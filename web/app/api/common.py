import functools
import flask_restful as fr


########################################################################################################################


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


########################################################################################################################


class ColanderResource(fr.Resource):
    """Base class for all API resources."""
    method_decorators = [format_response]
