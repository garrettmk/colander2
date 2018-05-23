import dramatiq
import sqlalchemy
import requests

from flask import has_app_context
from app import db, create_app, search

app = create_app()

ISO_8601 = '%Y-%m-%dT%H:%M:%S'


########################################################################################################################


def should_retry(retries_so_far, exception):
    """Custom retry behavior for MWS calls."""
    return retries_so_far < 10 and isinstance(exception, (
        sqlalchemy.exc.InternalError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout
    ))


standard_options = {
    'store_results': True,
    'min_backoff': 5000,
    'max_backoff': 300000,
    'retry_when': should_retry,
    'queue_name': 'core',
}


def ops_actor(fn=None, **options):
    """A version of dramatiq.actor that configures default options and sets up the app context."""

    def decorator(fn):

        def ops_fn(*args, **kwargs):
            if has_app_context():
                return fn(*args, **kwargs)
            else:
                with app.app_context():
                    return fn(*args, **kwargs)

        opts = dict(standard_options)
        opts['actor_name'] = fn.__name__
        opts.update(options)
        return dramatiq.actor(ops_fn, **opts)

    return decorator if fn is None else decorator(fn)

