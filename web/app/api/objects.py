from flask import request
from flask_restful import Resource
from webargs import fields
from webargs.flaskparser import use_kwargs
from marshmallow import Schema, post_load

from app import db
from .common import model_types, format_response


########################################################################################################################


class Objects(Resource):
    """Handles creation, deletion, and filtering of objects."""

    class FilterSchema(Schema):
        """Marshmallow schema for filter requests."""
        pageNum = fields.Int(missing=1)
        perPage = fields.Int(missing=10)
        getAttrs = fields.List(fields.Str(), missing=['abbreviated'])
        query = fields.Dict(missing=None)

        class Meta:
            strict = True

        @post_load
        def _preserve(self, data):
            data['filters'] = {key: request.args[key] for key in request.args if key not in data}
            return data

    def build_query_from_json(self, obj_type, js):
        """Build a SQLAlchemy query from a JSON blob."""
        eq = [getattr(obj_type, name) == value for name, value in js.get('eq', {}).items()]
        neq = [getattr(obj_type, name) != value for name, value in js.get('neq', {}).items()]
        _in = [getattr(obj_type, name).in_(values) for name, values in js.get('in', {}).items()]
        nin = [db.not_(getattr(obj_type, name).in_(values)) for name, values in js.get('nin', {}).items()]

        return obj_type.query.filter(
            *eq,
            *neq,
            *_in,
            *nin
        )

    @use_kwargs(FilterSchema)
    def get(self, type_alias, pageNum=None, perPage=None, getAttrs=None, filters={}, query=None):
        """Filter objects of the given type using query string parameters."""
        obj_type = model_types[type_alias]
        query = self.build_query_from_json(obj_type, query) if query else obj_type.query.filter_by(**filters)
        page = query.paginate(page=pageNum, per_page=perPage)

        if getAttrs == ['all']:
            items = [m.as_json() for m in page.items]
        elif getAttrs == ['abbreviated']:
            items = [m.abbr_json() for m in page.items]
        else:
            items = [m.as_json(*getAttrs) for m in page.items]

        return {
            'total': page.total,
            'page': page.page,
            'pages': page.pages,
            'per_page': page.per_page,
            'items': items
        }

    def post(self, type_alias):
        """Create an object using POST data."""
        data = dict(request.json)
        obj_type = model_types[type_alias]

        obj = obj_type()
        obj.update(data)
        db.session.add(obj)
        db.session.commit()

        return {
            'status': 'ok',
            'id': obj.id
        }

    def delete(self, type_alias):
        """Delete objects specified in the DELETE data."""
        ids = request.json['ids']
        obj_type = model_types[type_alias]

        try:
            obj_type.query.filter(obj_type.id.in_(ids)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {
                'status': 'error',
                'exception': type(e).__name__,
                'message': str(e)
            }

        return {
            'status': 'ok'
        }


########################################################################################################################


class Attributes(Resource):
    """Provides low-level get and set functionality for database models."""

    def get(self, type_alias, obj_id):
        attrs = [a for a in request.args] or ['abbreviated']

        obj_type = model_types[type_alias]

        obj = obj_type.query.filter_by(id=obj_id).one()

        if attrs == ['abbreviated']:
            response = obj.abbr_json()
        elif attrs == ['all']:
            response = obj.as_json()
        else:
            response = obj.as_json(*attrs)

        return response

    def post(self, obj_type, obj_id):
        """Modify attributes on an object."""
        update = dict(request.json)
        obj_type = model_types[obj_type]
        obj = obj_type.query.filter_by(id=obj_id).one()

        obj.update(update)
        db.session.commit()

        return {
            'status': 'ok'
        }
