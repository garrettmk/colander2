import importlib
import functools

from webargs import fields, validate
from webargs.flaskparser import use_kwargs

from flask import request
from flask_restful import Resource
from tasks.broker import setup_dramatiq
setup_dramatiq()


########################################################################################################################


def format_response(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
        except Exception as e:
            return {
                'status': 'error',
                'exception': type(e).__name__,
                'message': str(e)
            }

        return {
            'status': 'ok',
            **response
        }
    return wrapper


class Tasks(Resource):
    """Task-related API."""
    method_decorators = [format_response]

    start_args = {
        'task': fields.Str(required=True),
        'args': fields.List(fields.Raw(), missing=lambda: []),
        'kwargs': fields.Dict(missing=lambda: {}),
        'options': fields.Dict(missing=lambda: {})
    }

    @use_kwargs(start_args)
    def post(self, task, args, kwargs, options):
        """Start a task using the POST data."""

        path = task.split('.')
        module = '.'.join(path[:-1])
        actor = path[-1]

        module = importlib.import_module(module)
        actor = getattr(module, actor)

        message = actor.send_with_options(args=args, kwargs=kwargs, **options)

        return {
            'message_id': message.message_id
        }

