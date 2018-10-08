import re
import decimal
import datetime
import collections
import itertools

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import JSONB
from flask_sqlalchemy import Model, DefaultMeta

import marshmallow as mm
import marshmallow.fields as mmf

from flask.json import JSONEncoder
import sqlalchemy_jsonbase as jb


decimal.getcontext().prec = 23


class ColanderJSONEncoder(JSONEncoder):

    def default(self, value):
        if isinstance(value, decimal.Decimal):
            return str(value)

        return super().default(value)


########################################################################################################################


URL = sa.Text
CURRENCY = sa.Numeric(19, 4)
JSONB = MutableDict.as_mutable(JSONB)


def quantize_decimal(d, places=4):
    """Formats a Decimal object."""
    depth = '.' + '0' * (places - 1) + '1'
    return d.quantize(decimal.Decimal(depth))


# The following function converts from CapitalCase to python_case
first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def to_snake_case(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def filter_with_json(query, js, obj_type=None):
    """Apply filters and joins to a query, according to the contents of a JSON document."""
    obj_type = obj_type or query._primary_entity.type
    mapper = obj_type.__mapper__
    ops = {
        '_eq': lambda a, b: a == b,
        '_ne': lambda a, b: a != b,
        '_in': lambda a, b: a.in_(b),
        '_nin': lambda a, b: ~a.in_(b),
    }

    def expr(attr, op, value):
        return ops[op](getattr(obj_type, attr), value)

    for attr, filters in js.items():
        if attr in mapper.columns:
            if isinstance(filters, dict):
                exprs = [expr(attr, op, value) for op, value in filters.items()]
            elif isinstance(filters, list):
                exprs = [expr(attr, '_in', filters)]
            else:
                exprs = [expr(attr, '_eq', filters)]

            query = query.filter(*exprs)

        elif attr in mapper.relationships:
            rel_type = mapper.relationships[attr].mapper.class_
            query = query.join(rel_type)
            query = filter_with_json(query, filters, rel_type)

    orderings = []
    for attr, direction in js.get('_sort', {}).items():
        if direction in ('asc', 'ascending', 'up', True):
            direction = 'asc'
        elif direction in ('desc', 'descending', 'down', False):
            direction = 'desc'

        col = getattr(obj_type, attr)
        param = getattr(col, direction)()
        orderings.append(param)

    if orderings:
        query = query.order_by(*orderings)

    return query


def all_subclasses(cls):
    return [cls] + list(itertools.chain(*(all_subclasses(s) for s in cls.__subclasses__())))


########################################################################################################################


class DateTimeField(mmf.DateTime):
    def _deserialize(self, value, attr, data):
        if isinstance(value, datetime.datetime):
            return value
        return super()._deserialize(value, attr, data)


class ObjectIdField(mmf.Int):
    """Basically an integer field with some extra info."""

    def _jsonschema_type_mapping(self):
        return {k: v for k, v in {
            'type': 'objectId',
            'class': self.metadata['class_'],
            'title': self.attribute or self.name,
            'name': self.metadata.get('name', None)
        }.items() if v is not None}


jb.FIELD_MAP[sa.DateTime] = DateTimeField


########################################################################################################################


class BaseMeta(jb.JsonMetaMixin, DefaultMeta):
    """Metaclass for all models. Automatically generates a Schema and a __search_fields__ attribute for the class."""

    def __init__(cls, name, bases, dict_):
        super().__init__(name, bases, dict_)

        search_fields = []
        for name, attr in dict_.items():
            if isinstance(attr, sa.Column):
                if type(attr.type) in (sa.String, sa.Text):
                    search_fields.append(name)

        if '__search_fields__' in dict_:
            cls.__search_fields__ = dict_['__search_fields__']
        else:
            cls.__search_fields__ = getattr(cls, '__search_fields__', []) + search_fields


########################################################################################################################


class Base(jb.JsonMixin, Model):
    """Custom base class for all models."""
    extra = jb.Column(JSONB, default=dict, nullable=False, label='Extra data')
    type = jb.Column(sa.String(64), nullable=False, label='Object type')

    class __schema__(mm.Schema):
        extra = mmf.Dict()
        type = mmf.String()

    def __init__(self, *args, **kwargs):
        self.extra = {}
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f'<{type(self).__name__} {self.id}>'

    @declared_attr
    def __mapper_args__(cls):
        return {
            'polymorphic_identity': cls.__name__,
            'polymorphic_on': cls.type
        }

    @declared_attr
    def __tablename__(cls):
        return to_snake_case(cls.__name__)

    @classmethod
    def all_subclasses(cls):
        return all_subclasses(cls)

    @classmethod
    def full_name(cls):
        return '.'.join((cls.__module__, cls.__name__))

    def update(self, *args, **kwargs):
        """Convenience method for using from_json() with keyword args or a dictionary."""
        extra = super().update(*args, **kwargs)

        if self.extra is None:
            self.extra = extra
        else:
            self.extra.update(extra)


Base = declarative_base(cls=Base, metaclass=BaseMeta)
