import re
import time
import redis
import requests
import amazonmws
import attrdict
import xmallow as xm
from lxml import etree

from core import app, db, search
from ext.common import ExtActor
from models import Vendor
from config import Config


########################################################################################################################


ISO_8601 = '%Y-%m-%dT%H:%M:%S'

xm.Schema.dict_type = attrdict.AttrDict


########################################################################################################################


def remove_namespaces(xml):
    """Remove all traces of namespaces from the given XML string."""
    re_ns_decl = re.compile(r' xmlns(:\w*)?="[^"]*"', re.IGNORECASE)
    re_ns_open = re.compile(r'<\w+:')
    re_ns_close = re.compile(r'/\w+:')
    #
    response = re_ns_decl.sub('', xml)  # Remove namespace declarations
    response = re_ns_open.sub('<', response)  # Remove namespaces in opening tags
    response = re_ns_close.sub('/', response)  # Remove namespaces in closing tags
    return response


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


class MWSResponseSchema(xm.Schema):
    """Base schema for MWS responses."""
    ignore_missing = True

    class Error(xm.Schema):
        """Schema for MWS errors."""
        type = xm.Field('.//Type')
        code = xm.Field('.//Code')
        message = xm.Field('.//Message')

    request_id = xm.String('//RequestId')
    errors = xm.Field('//Error', Error(), default=list, many=True)


class RawXMLSchema(MWSResponseSchema):
    """Utility schema that just grabs the raw XML response."""
    xml = xm.Field('.', cast=lambda tag: etree.tostring(tag).decode(), default='Not found?')


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
            return retries_so_far < 10 and isinstance(exception, (
                RequestThrottled,
                InternalError,
                QuotaExceeded
            ))

    api_name = NotImplemented
    ResponseSchema = RawXMLSchema
    apis = {}
    redis = redis.from_url(Config.REDIS_URL)
    pending_expires = 200  # TTL for pending keys in redis. They are deliberately cleared unless something bad happens

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Redis script evaluator objects
        self._usage_loader = None
        self._usage_saver = None

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
                    ).first() or (None, None)

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
        return dict()

    def perform(self, *args, **kwargs):
        params = self.build_params(*args, **kwargs)
        response = self.make_api_call(type(self).__name__, **params)
        return self.process_response(args, kwargs, response)

    def make_api_call(self, action, throttle_action=None, **params):
        """Make an API call and return an AmzXmlResponse object."""
        throttle_action = throttle_action or action
        api_name = self.api_name
        vendor_id = self.context['vendor_id']

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
        xml = getattr(api, action)(**params).text

        # Save usage
        self.save_usage(vendor_id, throttle_action, limits)

        # Parse the response
        xml = remove_namespaces(xml)
        response = self.ResponseSchema().load(xml)

        # Raise an exception if needed
        if response.errors:
            codes = [e.code for e in response.errors]
            exc_type = None
            if 'RequestThrottled' in codes:
                exc_type = RequestThrottled
                sleep = stretch + limits['restore_rate']
                expires = int(sleep * 10 * 1000)
                self.redis.set(
                    f'{throttle_action}_{vendor_id}_stretch',
                    sleep,
                    px=expires
                )
            elif 'QuotaExceeded' in codes:
                exc_type = QuotaExceeded
            elif 'InternalError' in codes:
                exc_type = InternalError

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

    def process_response(self, args, kwargs, response):
        """Return the parsed version of the response."""
        return response

