from itertools import groupby
from flask_restful import Resource, reqparse

from app import search
from models import User, Vendor, Customer, Listing


########################################################################################################################


class TextSearch(Resource):
    """Search the entire database using a query string."""

    model_aliases = {
        'user': User,
        'vendor': Vendor,
        'customer': Customer,
        'listing': Listing
    }

    default_types = [
        'user',
        'vendor',
        'customer',
        'listing'
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.parser = reqparse.RequestParser()
        self.parser.add_argument('query', type=str)
        self.parser.add_argument('types', action='append')

    def get(self):
        args = self.parser.parse_args()
        query = args.get('query') or ''
        types = args.get('types') or self.default_types
        response = {
            'total': 0
        }

        try:
            for type_name in types:
                model_type = self.model_aliases[type_name]
                results, total = model_type.search(query)

                response['total'] += total
                response[type_name] = {
                    'total': total,
                    'results': [m.abbr_json() for m in results]
                }
        except Exception as e:
            return {
                'status': 'error',
                'exception': repr(e),
                'message': str(e)
            }

        return response
