import functools

from flask_restful import Resource

from app import db


########################################################################################################################


model_types = {
    t.__name__.lower(): t for t in db.Model.all_subclasses()
}


def format_response(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return {
                **func(*args, **kwargs)
            }
        except Exception as e:
            raise e
            return {
                'error': {
                    'exception': type(e).__name__,
                    'message': str(e)
                }
            }
    return wrapper


class ColanderResource(Resource):
    """Base class for all API resources."""
    method_decorators = [format_response]
