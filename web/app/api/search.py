import math

from flask_restful import Resource
from webargs import fields
from webargs.flaskparser import use_kwargs

from .common import model_types, format_response


########################################################################################################################


class TextSearch(Resource):
    """Search the entire database using a query string."""

    default_types = [
        'user',
        'vendor',
        'customer',
        'listing'
    ]

    get_schema = {
        'query': fields.Str(missing=''),
        'types': fields.List(fields.Str(), missing=default_types),
        'page': fields.Int(missing=1),
        'perPage': fields.Int(missing=10)
    }

    @use_kwargs(get_schema)
    def get(self, query, types, page, perPage):
        response = {
            'total': 0
        }

        for type_name in types:
            model_type = model_types[type_name]
            results, total = model_type.search(query, page, perPage)

            response['total'] += total
            response[type_name] = {
                'total': total,
                'page': page,
                'pages': math.ceil(total / perPage),
                'results': [m.abbr_json() for m in results]
            }

        return response
