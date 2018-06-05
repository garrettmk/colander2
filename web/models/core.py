import collections
import decimal
import datetime

from app import db
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import JSONB
from flask_sqlalchemy import SignallingSession
from werkzeug.security import generate_password_hash, check_password_hash
from app import search

decimal.getcontext().prec = 23


########################################################################################################################


URL = db.Text
CURRENCY = db.Numeric(19, 4)


def quantize_decimal(d, places=4):
    """Formats a Decimal object."""
    depth = '.' + '0' * (places - 1) + '1'
    return d.quantize(decimal.Decimal(depth))


########################################################################################################################


class UpdateMixin:
    """Provides models with an update() method, similar to dictionaries."""
    extra = db.Column(MutableDict.as_mutable(JSONB), default={}, nullable=False)

    def update(self, *args, **kwargs):
        """Update a model object's attributes, either by specifying their values as keyword arguments or as a
        dictionary. Keywords that do not correspond to column names will have their values stored in the 'extra'
        column."""
        data = {}

        if len(args) == 1:
            if isinstance(args[0], collections.Mapping):
                data.update(args[0])
            else:
                raise TypeError('Argument must be an instance of collections.Mapping')
        elif len(args) > 1:
            raise ValueError('update() can only accept a single key-value mapping as a positional parameter.')

        data.update(kwargs)
        extra = {}

        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                extra[key] = value

        if self.extra:
            self.extra.update(extra)
        else:
            self.extra = extra

    def encode_attribute(self, attr):
        """Return a JSON-compatible representation of a given object."""
        value = getattr(self, attr)

        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.timestamp()
        elif isinstance(value, decimal.Decimal):
            return float(value)

        return value

    def as_json(self, *args):
        """Returns a representation of the model as a Python dictionary."""
        if not args:
            args = list(c.name for c in type(self).__mapper__.columns)
            args += getattr(self, '__extended__', [])

        doc = {attr: self.encode_attribute(attr) for attr in args}
        return doc

    def abbr_json(self):
        """Returns an abbreviated form of the model as a Python dictionary."""
        try:
            abbr_attrs = self.__abbreviated__
        except AttributeError:
            abbr_attrs = []

        return self.as_json(*abbr_attrs)


########################################################################################################################


class SearchMixin:
    """A mixin that enables search indexing and a search function to work alongside SQLAlchemy."""
    __search_fields__ = NotImplemented
    __search_index__ = 'default'

    @classmethod
    def before_commit(cls, session):
        """Hold on to any searchable instances so that we can index them after the commit."""
        session._add_to_index = [obj for obj in session.new if isinstance(obj, cls)] + \
                                [obj for obj in session.dirty if isinstance(obj, cls)]
        session._remove_from_index = [obj for obj in session.deleted if isinstance(obj, cls)]

    @classmethod
    def after_commit(cls, session):
        """Add or remove objects from the search index."""
        for obj in session._add_to_index:
            search.add_to_index(obj)
        session._add_to_index = None

        for obj in session._remove_from_index:
            search.remove_from_index(obj)
        session._remove_from_index = None

    @classmethod
    def register_hooks(cls):
        db.event.listen(SignallingSession, 'before_commit', cls.before_commit)
        db.event.listen(SignallingSession, 'after_commit', cls.after_commit)

    @classmethod
    def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in s.all_subclasses()]

    @classmethod
    def full_name(cls):
        return '.'.join((cls.__module__, cls.__name__))

    @classmethod
    def search(cls, expression, page=1, per_page=10):
        hits, total = search.search(
            expression,
            index=cls.__search_index__,
            model_types=[cls] + cls.all_subclasses(),
            page=page,
            per_page=per_page
        )
        ids = [h['id'] for h in hits]
        whens = [(id, i) for i, id in enumerate(ids)]

        if total > 0:
            return cls.query.filter(cls.id.in_(ids)).order_by(db.case(whens, value=cls.id)), total
        else:
            return cls.query.filter_by(id=0), 0

    @classmethod
    def reindex(cls):
        search.reindex(cls)


SearchMixin.register_hooks()


########################################################################################################################


class User(db.Model, UpdateMixin, SearchMixin):
    """Tracks user name, email and password."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    human_name = db.Column(db.Text)
    password_hash = db.Column(db.Text, nullable=False)

    def __init__(self, *args, password=None, **kwargs):
        """Initialize the User."""
        super().__init__(*args, **kwargs)

        if password:
            self.set_password(password)

    def __repr__(self):
        return f'<{type(self).__name__} {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


########################################################################################################################


class PolymorphicBase:
    """Base class for extended models."""
    type = db.Column(db.String(64), nullable=False)

    @declared_attr
    def __mapper_args__(cls):
        return {
            'polymorphic_identity': cls.__name__,
            'polymorphic_on': cls.type
        }

    def __repr__(self):
        return f'<{type(self).__name__} {self.id}>'
