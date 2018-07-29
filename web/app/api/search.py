import math

from webargs import fields
from webargs.flaskparser import use_kwargs
from marshmallow import Schema

import core
import models
from .common import ColanderResource


searchable_models = [m.__name__ for m in core.Base.all_subclasses() if issubclass(m, models.mixins.SearchMixin)]
quick_models = [m.__name__ for m in core.Base.all_subclasses() if hasattr(m, 'QuickResult')]


########################################################################################################################


class TextSearch(ColanderResource):
    """Search the entire database using a query string."""

    class SearchSchema(Schema):
        """Schema for search requests."""
        query = fields.Str(missing='')
        types = fields.List(fields.Str(), missing=searchable_models)
        page = fields.Int(missing=1)
        perPage = fields.Int(missing=10)

        class Meta:
            strict = True

    @use_kwargs(SearchSchema)
    def get(self, query, types, page, perPage):
        response = {
            'total': 0
        }

        for type_name in types:
            model_type = getattr(models, type_name)
            results, total = model_type.search(query, page, perPage)

            response['total'] += total
            response[type_name] = {
                'total': total,
                'page': page,
                'pages': math.ceil(total / perPage),
                'results': [m.to_json() for m in results]
            }

        return response


########################################################################################################################


class QuickSearch(ColanderResource):
    """Quick search results using a query string."""

    class QuickSchema(Schema):
        query = fields.Str(required=True)
        types = fields.List(fields.Str(), missing=quick_models)
        limit = fields.Int(missing=10)

        class Meta:
            strict = True

    @use_kwargs(QuickSchema)
    def get(self, query, types, limit):
        response = {}

        for type_name in types:
            model_type = getattr(models, type_name)
            results, total = model_type.search(query, per_page=limit)
            if not total:
                continue

            response[type_name] = {
                'name': model_type.__name__,
                'results': [m.to_json(schema_attr='QuickResult') for m in results]
            }

        response.pop('Entity', None)

        return response
