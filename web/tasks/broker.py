import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.results.backends import RedisBackend as RedisResultsBackend
from dramatiq.rate_limits.backends import RedisBackend as RedisRateLimiterBackend
from dramatiq.results import Results

from urllib.parse import urlsplit
from config import Config


########################################################################################################################


broker = None
results_backend = None
rate_limiter_backend = None


########################################################################################################################


def setup_dramatiq(config_class=Config):
    global broker, results_backend, rate_limiter_backend
    o = urlsplit(config_class.REDIS_URL)

    results_backend = RedisResultsBackend(
        host=o.hostname,
        port=o.port,
        db=o.path.split('/')[-1] or None,
        password=o.password
    )

    rate_limiter_backend = RedisRateLimiterBackend(
        host=o.hostname,
        port=o.port,
        db=o.path.split('/')[-1] or None,
        password=o.password
    )

    broker = RedisBroker(url=config_class.REDIS_URL)
    broker.add_middleware(Results(backend=results_backend))

    dramatiq.set_broker(broker)


