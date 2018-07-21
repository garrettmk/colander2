import json
import urllib.parse

import sqlalchemy as sa
from webargs import fields
from webargs.flaskparser import use_kwargs, use_args
from marshmallow import Schema, post_load, ValidationError
import sqlalchemy_jsonbase as sajs

from app import db
from core import filter_with_json
from .common import model_types, ColanderResource


########################################################################################################################


class EncodedDict(fields.Field):
    """A dictionary that has been URL encoded. Supports nested schemas for decoded content."""

    def _deserialize(self, value, attr, data):
        if isinstance(value, str):
            decoded = urllib.parse.unquote(value)
            value = json.loads(decoded)

        nested = self.metadata.get('nested', None)
        if nested:
            value = nested.load(value).data

        return value


########################################################################################################################


class ViewSchema(sajs.ViewSchema):
    """Schema for the _view parameter."""
    _page = fields.Int(missing=1)
    _per_page = fields.Int(missing=10)


########################################################################################################################


class ObjectSchema(ColanderResource):
    """Returns the schema for a object type."""

    class ObjectSchemaSchema(Schema):
        view = fields.Nested(ViewSchema, missing=dict)
        class Meta:
            strict = True

    @use_kwargs(ObjectSchemaSchema)
    def post(selfself, type_alias, view):
        obj_type = model_types[type_alias]
        return obj_type.json_schema(**view)


########################################################################################################################


class ObjectFilter(ColanderResource):
    """Filters and returns objects using JSON queries."""
    
    class FilterSchema(Schema):
        query = fields.Dict(missing=dict)
        view = fields.Nested(ViewSchema, missing=dict)
        
        class Meta:
            strict = True
            
    @use_kwargs(FilterSchema)
    def post(self, type_alias, query, view):
        obj_type = model_types[type_alias]
        query = filter_with_json(obj_type.query, query)
        page = query.paginate(page=view['context']['_page'], per_page=view['context']['_per_page'])
        print(view)
        items = [m.to_json(**view) for m in page.items]
        return {
            'total': page.total,
            'page': page.page,
            'pages': page.pages,
            'per_page': page.per_page,
            'items': items,
            'schema': obj_type.json_schema(**view)
        }


########################################################################################################################


class ObjectUpdater(ColanderResource):
    """Updates all objects that match the query."""
    
    class UpdateSchema(Schema):
        query = fields.Dict(required=True)
        data = fields.Dict(required=True)
        
        class Meta:
            strict = True
            
    @use_kwargs(UpdateSchema)
    def post(self, type_alias, query, data):
        obj_type = model_types[type_alias]
        loaded = obj_type.Schema().load(data, partial=True)

        if loaded.errors:
            return {'errors': loaded.errors}

        query = filter_with_json(obj_type.query, query)

        for obj in query.all():
            obj.update(loaded.data)

        db.session.commit()
        return {'status': 'ok'}


########################################################################################################################


class ObjectCreator(ColanderResource):
    """Creates an object and returns it's ID."""
    
    class CreatorSchema(Schema):
        data = fields.Dict(required=True)
        
        class Meta:
            strict = True
            
    @use_kwargs(CreatorSchema)
    def post(self, type_alias, data):
        obj_type = model_types[type_alias]
        errors = obj_type.Schema().validate(data, partial=False)
        
        if errors:
            return {'errors': errors}
        
        obj = obj_type.from_json(data)
        db.session.add(obj)

        try:
            db.session.commit()
        except sa.exc.IntegrityError as exc:
            db.session.rollback()

            try:
                error_key = [key for key in data if f'\"entity_{key}_key\"' in str(exc)][0]
            except IndexError:
                raise exc

            return {'errors': {error_key: str(exc)}}
        
        return {'id': obj.id}


########################################################################################################################


class ObjectDeleter(ColanderResource):
    """Deletes all objects that match the query."""

    class DeleterSchema(Schema):
        query = fields.Dict(required=True)

        class Meta:
            strict = True

    @use_kwargs(DeleterSchema)
    def post(self, type_alias, query):
        obj_type = model_types[type_alias]
        query = filter_with_json(obj_type.query, query)
        query.delete()
        db.session.commit()

        return {'status': 'ok'}
