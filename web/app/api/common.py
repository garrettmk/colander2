import functools

from app import db


########################################################################################################################


model_types = {
    t.__name__.lower(): t for t in db.Model.all_subclasses()
}


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
