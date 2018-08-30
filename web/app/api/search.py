import math

import webargs.flaskparser
import marshmallow as mm
import sqlalchemy_jsonbase as sajs

import core
import models
from .common import ColanderResource


searchable_models = [m.__name__ for m in core.Base.all_subclasses() if issubclass(m, models.mixins.SearchMixin)]
quick_models = [m.__name__ for m in core.Base.all_subclasses() if hasattr(m, 'Preview')]


########################################################################################################################


class TextSearch(ColanderResource):
    """Search the entire database using a query string."""

    class SearchSchema(mm.Schema):
        """Schema for search requests."""
        query = mm.fields.Str(missing='')
        types = mm.fields.List(mm.fields.Str(), missing=searchable_models)
        page = mm.fields.Int(missing=1)
        perPage = mm.fields.Int(missing=10)

        class Meta:
            strict = True

    @webargs.flaskparser.use_kwargs(SearchSchema)
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

    class QuickSchema(mm.Schema):
        query = mm.fields.Str(required=True)
        types = mm.fields.List(mm.fields.Str(), missing=quick_models)
        limit = mm.fields.Int(missing=10)

        class Meta:
            strict = True

    @webargs.flaskparser.use_kwargs(QuickSchema)
    def get(self, query, types, limit):
        response = {}

        for type_name in types:
            model_type = getattr(models, type_name)
            results, total = model_type.search(query, per_page=limit)
            if not total:
                continue

            response[type_name] = {
                'name': model_type.__name__,
                'results': [m.to_json(_schema='Preview') for m in results]
            }

        response.pop('Entity', None)

        return response


########################################################################################################################


class ViewSchema(sajs.ViewSchema):
    """Schema for the _view parameter."""
    _page = mm.fields.Int(missing=1)
    _per_page = mm.fields.Int(missing=10)


class SimilarListingsSearch(ColanderResource):
    """Find similar listings."""

    class SimilarSchema(mm.Schema):
        id = mm.fields.Str(required=True)
        minScore = mm.fields.Float(missing=None)
        page = mm.fields.Int(missing=1)
        perPage = mm.fields.Int(missing=10)
        view = mm.fields.Nested(ViewSchema, missing=dict)

        class Meta:
            string = True

    @webargs.flaskparser.use_kwargs(SimilarSchema)
    def get(self, id, minScore, page, perPage, view):
        listing = models.Listing.query.filter_by(id=id).one()
        results, total, scores = listing.find_similar(min_score=minScore, page=page, per_page=perPage)
        paginator = results.paginate(page=page, per_page=perPage)
        items = [m.to_json(view) for m in paginator.items]
        for item in items:
            item['_score'] = scores[item['id']]

        return {
            'total': paginator.total,
            'page': paginator.page,
            'pages': paginator.pages,
            'per_page': paginator.per_page,
            'items': items,
            'schema': models.Listing.json_schema(view),
        }