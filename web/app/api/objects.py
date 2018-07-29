import json
import urllib.parse

import sqlalchemy as sa
from webargs import fields
from webargs.flaskparser import use_kwargs, use_args
from marshmallow import Schema, post_load, ValidationError
import sqlalchemy_jsonbase as sajs

import app
import core
import models
from .common import ColanderResource


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
    def post(selfself, type_, view):
        obj_type = getattr(models, type_)
        return obj_type.json_schema(view)


########################################################################################################################


class ObjectFilter(ColanderResource):
    """Filters and returns objects using JSON queries."""
    
    class FilterSchema(Schema):
        query = fields.Dict(missing=dict)
        view = fields.Nested(ViewSchema, missing=dict)
        schema = fields.String(missing='__schema__')
        
        class Meta:
            strict = True
            
    @use_kwargs(FilterSchema)
    def post(self, type_, query, view, schema):
        obj_type = getattr(models, type_)
        query = core.filter_with_json(obj_type.query, query)

        page = query.paginate(page=view['context']['_page'], per_page=view['context']['_per_page'])
        items = [m.to_json(view, _schema=schema) for m in page.items]
        return {
            'total': page.total,
            'page': page.page,
            'pages': page.pages,
            'per_page': page.per_page,
            'items': items,
            'schema': obj_type.json_schema(view)
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
    def post(self, type_, query, data):
        obj_type = getattr(models, type_)
        loaded = obj_type.Schema().load(data, partial=True)

        if loaded.errors:
            return {'errors': loaded.errors}

        query = core.filter_with_json(obj_type.query, query)

        for obj in query.all():
            obj.update(loaded.data)

        app.db.session.commit()
        return {'status': 'ok'}


########################################################################################################################


class ObjectCreator(ColanderResource):
    """Creates an object and returns it's ID."""
    
    class CreatorSchema(Schema):
        data = fields.Dict(required=True)
        
        class Meta:
            strict = True
            
    @use_kwargs(CreatorSchema)
    def post(self, type_, data):
        obj_type = getattr(models, type_)
        schema = obj_type.__schema__()
        errors = schema.validate(data, partial=False)
        
        if errors:
            return {'errors': errors}
        
        obj = obj_type.from_json(data)
        app.db.session.add(obj)

        try:
            app.db.session.commit()
        except sa.exc.IntegrityError as exc:
            app.db.session.rollback()

            try:
                error_key = [key for key in schema.fields if f'\"{key}\"' in str(exc) or f'\"entity_{key}_key\"' in str(exc)][0]
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
    def post(self, type_, query):
        obj_type = getattr(models, type_)
        query = core.filter_with_json(obj_type.query, query)
        query.delete()
        app.db.session.commit()

        return {'status': 'ok'}
