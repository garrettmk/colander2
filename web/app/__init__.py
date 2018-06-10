import re
import operator

import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy, Model, DefaultMeta
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from marshmallow import fields, Schema, post_load

from config import Config
from app.core import bp as core_bp
from search.search import ColanderSearch

# The following function converts from CapitalCase to python_case
first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def to_snake_case(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


########################################################################################################################


column_to_field = {
    sa.Boolean: fields.Boolean,
    sa.Integer: fields.Integer,
    sa.Float: fields.Float,
    sa.String: fields.String,
    sa.Text: fields.String,
    sa.Date: fields.Date,
    sa.DateTime: fields.DateTime,
    sa.Time: fields.Time,
    sa.Numeric: fields.Decimal,
    sa.JSON: fields.Dict,
    JSONB: fields.Dict
}

schema_kwargs = ['_only', '_exclude', '_prefix', '_many', '_load_only', '_dump_only', '_partial']


def filter_with_json(query, js, obj_type=None):
    obj_type = obj_type or query._primary_entity.type
    mapper = obj_type.__mapper__
    ops = {
        '_eq': operator.eq,
        '_ne': operator.ne,
        '_in': operator.contains,
        '_nin': lambda a, b: not operator.contains(a, b)
    }

    for attr, filters in js.items():
        if attr in mapper.columns:
            exprs = [ops[op](getattr(obj_type, attr), value) for op, value in filters.items()]
            query = query.filter(*exprs)
        elif attr in mapper.relationships:
            rel_type = mapper.relationships[attr].mapper.class_
            query = query.join(rel_type)
            query = filter_with_json(query, filters, rel_type)

    return query


class RelationshipField(fields.Field):

    # The number of items to serialize for query-type relationships
    query_limit = 10

    def _serialize(self, value, attr, obj):
        if self.context.get('_follow', False) or attr in self.context:
            attr_context = self.context.get(attr, {})
            context = {k: v for k, v in attr_context.items() if k not in schema_kwargs}
            schema_opts = {k[1:]: v for k, v in attr_context.items() if k in schema_kwargs}
            only = schema_opts.pop('only', None)
            schema_set = context.get('_schema_set', None)

            def dump(obj):
                schema_set_fields = type(obj).__schema_set__[schema_set] if schema_set else None
                schema_only = [f for f in only if f in obj.Schema._declared_fields] if only else None
                schema = obj.Schema(context=context, only=schema_set_fields or schema_only, **schema_opts)
                return schema.dump(obj).data

            if isinstance(value, sa.orm.Query):
                filters = self.context.get(attr, {}).get('_filter', {})
                q = filter_with_json(value, filters)
                return [dump(i) for i in q.limit(self.query_limit).all()]

            elif isinstance(value, sa.orm.collections.InstrumentedList):
                return [dump(i) for i in value]

            elif value is None:
                return None

            return dump(value)

        return None


class BaseMeta(DefaultMeta):
    """Metaclass for all models."""
    def __init__(cls, name, bases, dict_):
        super().__init__(name, bases, dict_)
        if hasattr(cls, '__table__'):
            search_fields = []
            col_fields = {}
            rel_fields = []

            for name, attr in dict_.items():
                if isinstance(attr, sa.Column):
                    col_type = type(attr.type)
                    col_fields.update({name: col_type})
                    if col_type in (sa.String, sa.Text):
                        search_fields.append(name)
                elif isinstance(attr, sa.orm.RelationshipProperty):
                    rel_fields.append(name)

            schema_fields = {
                **{n: column_to_field[t]() for n, t in col_fields.items()},
                **{n: RelationshipField() for n in rel_fields}
            }

            cls.__search__ = search_fields
            cls.Schema = type('Schema', (Schema,), schema_fields)


########################################################################################################################


class Base(Model):
    """Custom base class for all models."""
    extra = sa.Column(MutableDict.as_mutable(JSONB), default=dict, nullable=False)

    @declared_attr
    def __tablename__(cls):
        return to_snake_case(cls.__name__)

    @classmethod
    def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in s.all_subclasses()]

    @classmethod
    def full_name(cls):
        return '.'.join((cls.__module__, cls.__name__))

    def to_json(self, **kwargs):
        bases = type(self).__mro__
        context = {k: v for k, v in kwargs.items() if k not in schema_kwargs}
        schema_opts = {k[1:]: v for k, v in kwargs.items() if k in schema_kwargs}
        only = schema_opts.pop('only', None)

        data = {}
        for base in reversed(bases):
            schema = getattr(base, 'Schema', None)
            if schema:
                schema_set = context.get('_schema_set', None)
                schema_set_fields = base.__schema_set__[schema_set] if schema_set else None
                schema_only = [f for f in only if f in schema._declared_fields] if only else None

                schema_data = schema(
                    context=context,
                    only=schema_set_fields or schema_only,
                    **schema_opts
                ).dump(self).data

                data.update(schema_data)

        return data

    def from_json(self, data):
        bases = type(self).__mro__
        loaded = {}

        for base in reversed(bases):
            if hasattr(base, 'Schema'):
                loaded.update(base.Schema().load(data).data)
        extra = {k: v for k, v in data.items() if k not in loaded}

        for key, value in data.items():
            setattr(self, key, value)

        if self.extra:
            self.extra.update(extra)
        else:
            self.extra = extra


Base = declarative_base(cls=Base, metaclass=BaseMeta)


########################################################################################################################


db = SQLAlchemy(model_class=Base)
search = ColanderSearch()


def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static/dist')
    app.config.from_object(config_class)

    app.register_blueprint(core_bp)

    db.init_app(app)
    search.init_app(app)

    from app.api import api
    api.init_app(app)

    return app


########################################################################################################################


