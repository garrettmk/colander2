import re
import time
import redis
import requests
import dramatiq
import amazonmws
from dramatiq.rate_limits import RateLimiter
from lxml import etree

from app import create_app, db, Config
app = create_app()

from models.entities import Vendor
from tasks.broker import rate_limiter_backend
from ext.core import ExtActor

ISO_8601 = '%Y-%m-%dT%H:%M:%S'


########################################################################################################################


class HiResWindowRateLimiter(RateLimiter):
    """Basically a copy of WindowRateLimiter with some modifications allowing sub-second windows."""

    def __init__(self, backend, key, *, limit=1, window=1.0):
        assert limit >= 1, "limit must be positive"
        assert window > 0, "window must be positive"

        super().__init__(backend, key)
        self.limit = limit

        min_res, max_res = 1, 0.001
        res = min_res
        while res >= max_res:
            if window / res == int(window / res):
                self.res = res
                break
            res /= 10
        else:
            self.res = None

        self.window = int(window / res)
        self.window_millis = int(window * 1000)

    def _acquire(self):
        timestamp = int(time.time() / self.res)
        keys = ["%s@%s" % (self.key, timestamp - i) for i in range(self.window)]

        # TODO: This is susceptible to drift because the keys are
        # never re-computed when CAS fails.
        return self.backend.incr_and_sum(
            keys[0], keys, 1,
            maximum=self.limit,
            ttl=self.window_millis,
        )

    def _release(self):
        pass


########################################################################################################################


def should_retry(retries_so_far, exception):
    """Custom retry behavior for MWS calls."""
    return retries_so_far < 10 and isinstance(exception, type(None))


standard_options = {
    'store_results': True,
    'min_backoff': 5000,
    'max_backoff': 300000,
    'retry_when': should_retry,
    'queue_name': 'ext',
}


def mws_actor(fn=None, *, quota_max=1, restore_rate=1, **options):
    """A version of dramatiq.actor that automatically configures rate limiting."""

    def decorator(fn):
        actor_name = fn.__name__
        mutex = HiResWindowRateLimiter(rate_limiter_backend, actor_name, limit=quota_max, window=restore_rate * quota_max)

        def limited_fn(*args, **kwargs):
            while True:
                with mutex.acquire(raise_on_failure=False) as acquired:
                    if acquired:
                        return fn(*args, **kwargs)
                    else:
                        time.sleep(restore_rate)

        opts = dict(standard_options)
        opts['actor_name'] = actor_name
        opts.update(options)
        return dramatiq.actor(limited_fn, **opts)

    return decorator if fn is None else decorator(fn)


########################################################################################################################


def format_parsed_response(action, params, results=None, errors=None, succeeded=None):
    if succeeded is None:
        succeeded = True if errors is None or not len(errors) else False

    return {
        'action': action,
        'params': params,
        'results': results if results is not None else {},
        'errors': errors if errors is not None else {},
        'succeeded': succeeded
    }


########################################################################################################################


class AmazonMWSError(Exception):
    """Base class for MWS errors."""
    def __init__(self, type=None, code=None, message=None):
        self.type = type
        self.code = code
        self.message = message


class RequestThrottled(AmazonMWSError):
    pass


class InternalError(AmazonMWSError):
    pass


class QuotaExceeded(AmazonMWSError):
    pass


########################################################################################################################


class MWSActor(ExtActor):
    """Provides common behaviors for all MWS API calls."""

    class Meta:
        abstract = True
        queue_name = 'ext'
        store_results = True
        min_backoff = 5000
        max_backoff = 300000

        @staticmethod
        def retry_when(retries_so_far, exception):
            return retries_so_far < 10 and isinstance(exception, (RequestThrottled, InternalError, QuotaExceeded))

    apis = {}
    redis = redis.from_url(Config.REDIS_URL)
    pending_expires = 200  # TTL for pending keys in redis. They are deliberately cleared unless something bad happens

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vendor_id = None

        # Redis script evaluator objects
        self._usage_loader = None
        self._usage_saver = None

    def api_name(self):
        """Return the name of the API used by the call."""
        raise NotImplementedError

    def get_api(self, vendor_id, api_name):
        """Returns an API object for a specific vendor."""
        if vendor_id not in MWSActor.apis:
            with app.app_context():
                q = db.session.query(Vendor.extra['mws_keys'], Vendor.extra['pa_keys'])
                if vendor_id:
                    mws_keys, pa_keys = q.filter(Vendor.id == vendor_id).one()
                else:
                    mws_keys, pa_keys = q.filter(
                        db.and_(
                            Vendor.extra.op('->')('mws_keys') != None,
                            Vendor.extra.op('->')('pa_keys') != None
                        )
                    ).first()

            if None in (mws_keys, pa_keys):
                raise ValueError('MWS and PA API keys not found.')

            MWSActor.apis[vendor_id] = {'_keys': (mws_keys, pa_keys)}

        if api_name not in MWSActor.apis[vendor_id]:
            mws_keys, pa_keys = MWSActor.apis[vendor_id]['_keys']
            api_type = getattr(amazonmws, api_name)
            api_keys = pa_keys if api_name == 'ProductAdvertising' else mws_keys
            MWSActor.apis[vendor_id][api_name] = api_type(**api_keys, make_request=requests.request)

        return MWSActor.apis[vendor_id][api_name]

    def build_params(self, *args, **kwargs):
        """Return a dictionary of parameters to send to the API call."""
        raise NotImplementedError

    def perform(self, *args, **kwargs):
        self.vendor_id = kwargs.pop('vendor_id', None)
        params = self.build_params(*args, **kwargs)
        response = self.make_api_call(type(self).__name__, **params)
        return self.parse_response(args, kwargs, response)

    def make_api_call(self, action, throttle_action=None, **params):
        """Make an API call and return an AmzXmlResponse object."""
        throttle_action = throttle_action or action
        api_name = self.api_name()
        vendor_id = self.vendor_id

        # Load the throttle limits for this API call
        default_limits = {'quota_max': 1, 'restore_rate': 1}
        limits = amazonmws.DEFAULT_LIMITS.get(throttle_action, default_limits)

        # Load the current usage for this action
        usage = self.load_usage(vendor_id, throttle_action, limits)

        # Sleep for the appropriate amount of time
        time.sleep(self.calculate_wait(usage, limits))

        # Load the elastic delay
        stretch = self.redis.get(f'{throttle_action}_{vendor_id}_stretch')
        stretch = float(stretch) if stretch else 0
        time.sleep(stretch)

        # Make the API call
        api = self.get_api(vendor_id, api_name)
        response = AmzXmlResponse(
            getattr(api, action)(**params).text
        )

        # Save usage
        self.save_usage(vendor_id, throttle_action, limits)

        # Raise an exception if needed
        code = response.error_code
        exc_type = None
        if code == 'RequestThrottled':
            exc_type = RequestThrottled
            sleep = stretch + limits['restore_rate']
            expires = int(sleep * 10 * 1000)
            self.redis.set(
                f'{throttle_action}_{vendor_id}_stretch',
                sleep,
                px=expires
            )
        elif code == 'QuotaExceeded':
            exc_type = QuotaExceeded
        elif code == 'InternalError':
            exc_type = InternalError
        elif code is not None:
            exc_type = AmazonMWSError

        if exc_type:
            raise exc_type(response.error_type, response.error_code, response.error_message)

        return response

    def load_usage(self, vendor_id, action, limits):
        """Load usage for this operation type, and increment the pending counter for this operation."""
        usage_key = f'{action}_{vendor_id}_usage'
        now = time.monotonic()
        restore_rate = limits['restore_rate']

        # The script below restores the quota level based on the elapsed time and the restore rate
        # Call like so: EVAL script 1 usage_key current_time restore_rate
        if self._usage_loader is None:
            script = f"""
            local usage = redis.call('HMGET', KEYS[1], 'quota_level', 'pending', 'last_request')
            local quota_level = true and tonumber(usage[1]) or 0
            local pending = true and tonumber(usage[2]) or 0
            local last_request = true and tonumber(usage[3]) or 0
            local restored = 0

            if last_request > 0 then
                restored = (tonumber(ARGV[1]) - last_request) / tonumber(ARGV[2])
                quota_level = math.max(quota_level - restored, 0)
                redis.call('HSET', KEYS[1], 'quota_level', quota_level)
            end

            redis.call('HINCRBY', KEYS[1], 'pending', 1)
            redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))

            return {{tostring(quota_level), pending, tostring(last_request), tostring(restored)}}
            """

            # KEYS = {usage_key}
            # ARGV = {now, restore_rate, pending_expires}

            self._usage_loader = self.redis.register_script(script)

        values = self._usage_loader(
            keys=(usage_key,),
            args=[str(arg) for arg in (now, restore_rate, self.pending_expires)]
        )

        return {
            'quota_level': float(values[0]),
            'pending': int(values[1]),
            'last_request': float(values[2])
        }

    def save_usage(self, vendor_id, action, limits):
        """Update the usage stats in the cache."""
        usage_key = f'{action}_{vendor_id}_usage'
        now = time.monotonic()
        restore_rate = limits['restore_rate']

        # The script below restores the quota level based on the elapsed time and the restore rate
        # Call like so: EVAL script 1 usage_key current_time restore_rate
        if self._usage_saver is None:
            script = f"""
                    local usage = redis.call('HMGET', KEYS[1], 'quota_level', 'last_request')
                    local quota_level = true and tonumber(usage[1]) or 0
                    local last_request = true and tonumber(usage[2]) or 0
                    local restored = 0

                    if last_request > 0 then
                        local restored = (tonumber(ARGV[1]) - last_request) / tonumber(ARGV[2])
                        quota_level = math.max(quota_level - restored, 0)
                        redis.call('HSET', KEYS[1], 'quota_level', quota_level + 1)
                    end

                    redis.call('HINCRBY', KEYS[1], 'pending', -1)
                    redis.call('HSET', KEYS[1], 'last_request', tonumber(ARGV[1]))

                    return {{tostring(restored), tostring(last_request)}}
                    """

            # KEYS = {usage_key}
            # ARGS = {now, restore_rate}

            self._usage_saver = self.redis.register_script(script)

        self._usage_saver(
            keys=(usage_key,),
            args=[str(arg) for arg in (now, restore_rate)]
        )

    def calculate_wait(self, usage, limits):
        """Calculate how long to sleep() before making the API call."""
        quota_max = limits['quota_max']
        restore_rate = limits['restore_rate']
        quota_level = usage['quota_level']
        pending = usage['pending']

        return max((quota_level + pending + 1 - quota_max), 0) * restore_rate

    def parse_response(self, args, kwargs, response):
        """Return the parsed version of the response."""
        return etree.tostring(response.tree, pretty_print=True).decode()


########################################################################################################################


def xpath_get(path, tag, _type=str, default=None):
    """Helper method for getting data values from lxml tags using XPath."""
    try:
        data = tag.xpath(path)[0].text
    except IndexError:
        return default

    if _type is bool:
        if data in ('1', 'true', 'yes'):
            return True
        elif data in ('0', 'false', 'no'):
            return False
        else:
            return bool(data)

    if data == '':
        return default

    return _type(data)


########################################################################################################################


class AmzXmlResponse:
    """A utility class for dealing with Amazon's XML responses."""

    def __init__(self, xml=None):
        self._xml = None
        self.tree = None

        self.xml = xml

    @property
    def xml(self):
        return self._xml

    @xml.setter
    def xml(self, xml):
        """Perform automatic etree parsing."""
        self._xml, self.tree = None, None

        if xml is not None:
            self._xml = self.remove_namespaces(xml)
            self.tree = etree.fromstring(self._xml)

    @staticmethod
    def remove_namespaces(xml):
        """Remove all traces of namespaces from the given XML string."""
        re_ns_decl = re.compile(r' xmlns(:\w*)?="[^"]*"', re.IGNORECASE)
        re_ns_open = re.compile(r'<\w+:')
        re_ns_close = re.compile(r'/\w+:')

        response = re_ns_decl.sub('', xml)  # Remove namespace declarations
        response = re_ns_open.sub('<', response)  # Remove namespaces in opening tags
        response = re_ns_close.sub('/', response)  # Remove namespaces in closing tags
        return response

    def xpath_get(self, *args, **kwargs):
        """Utility method for getting data values from XPath selectors."""
        return xpath_get(*args, tag=self.tree, **kwargs)

    @property
    def error_type(self):
        """Return the error type if there was an error, otherwise None."""
        return None if self.tree is None else self.xpath_get('/ErrorResponse/Error/Type')

    @property
    def error_code(self):
        """Holds the error code if the response was an error, otherwise None."""
        return None if self.tree is None else self.xpath_get('/ErrorResponse/Error/Code')

    @property
    def error_message(self):
        """Holds the error message if the response was an error, otherwise None."""
        return None if self.tree is None else self.xpath_get('/ErrorResponse/Error/Message')

    @property
    def request_id(self):
        """Returns the RequestID parameter."""
        if self.tree is None:
            return None

        return self.xpath_get('//RequestID')

    def error_as_json(self):
        """Formats an error response as a simple JSON object."""
        return {
            'error': {
                'code': self.error_code,
                'message': self.error_message,
                'request_id': self.request_id
            }
        }
