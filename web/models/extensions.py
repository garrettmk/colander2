import importlib

import sqlalchemy as sa
import marshmallow as mm
import marshmallow.fields as mmf
import marshmallow_jsonschema as mmjs
import sqlalchemy_jsonbase as jb
import dramatiq as dq

from app import db
from core import JSONB
from .mixins import SearchMixin


########################################################################################################################


class Extension(db.Model, SearchMixin):
    """A module of code."""
    id = jb.Column(db.Integer, primary_key=True, label='Extension ID')
    name = jb.Column(db.Text, nullable=False, unique=True, label='Name')
    module = jb.Column(db.Text, nullable=False, unique=True, label='Module (ext.)')
    exports = jb.Column(JSONB, default=dict, nullable=False, label='Exports')

    tasks = jb.relationship('Task', back_populates='extension', uselist=True, label='Extensions')

    class Preview(mm.Schema):
        id = mmf.Int()
        type = mmf.Str()
        title = mmf.Str(attribute='name')
        description = mmf.Function(lambda obj: f'ext.{obj.module}')

    def __repr__(self):
        name = self.name or self.module or self.id
        return f'<{type(self).__name__} {name}>'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._m = None
        self.load_module()

    @sa.orm.reconstructor
    def __init_on_load___(self):
        self._m = None
        self.load_module()

    @property
    def m(self):
        if self._m:
            return self._m

        self.load_module()
        return self._m

    @m.setter
    def m(self, name):
        if name is None:
            self._m = None
            self.module = None
            self.exports = {}
            return

        self.load_module(name)

    def load_module(self, name=None):
        """Inspects the currently loaded module and updates the name and functions attributes."""
        name = name or self.module
        if name is None:
            self.m = None
            return

        mod = importlib.import_module('ext.' + name)
        symbols = [getattr(mod, s) for s in dir(mod) if not s.startswith('_')]
        actors = [s for s in symbols if isinstance(s, dq.GenericActor) and getattr(s, 'public', False)]

        self._m = mod
        self.name = self.name or self.module
        self.exports = {
            a.actor_name: {
                'doc': getattr(a, '__doc__', a.__class__.__doc__),
                'schema': mmjs.JSONSchema().dump(a.Schema()).data['definitions']['Schema']
            } for a in actors}

    def send(self, action, **kwargs):
        """Call an actor asynchronously and returns the message ID."""
        if action not in self.exports:
            raise ValueError(f'Unknown export: {action}')

        message = getattr(self.m, action).send(**kwargs)
        return {'message_id': message.message_id}

    def call(self, action, *args, **kwargs):
        """Call an actor synchronously and return it's return value."""
        if action not in self.exports:
            raise ValueError(f'Unknown export: {action}')

        return getattr(self.m, action)(*args, **kwargs)


########################################################################################################################


class Task(db.Model, SearchMixin):
    """Stores info on recurring tasks."""
    id = jb.Column(db.Integer, primary_key=True)
    name = jb.Column(db.Text, nullable=False, unique=True)
    ext_id = jb.Column(db.Integer, db.ForeignKey('extension.id', ondelete='CASCADE'), nullable=False)
    action = jb.Column(db.String(64), nullable=False)
    params = jb.Column(JSONB, default=dict)
    schedule = jb.Column(JSONB, default=dict)

    extension = jb.relationship('Extension', back_populates='tasks')

    def __init__(self, *args, **kwargs):
        self.params = {}
        self.options = {}
        self.schedule = {}
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f'<{type(self).__name__} {self.name or self.id}>'

    def send(self):
        message = self.extension.send(
            self.action,
            *self.params.get('args', []),
            **self.params.get('kwargs', {})
        )

        return {'message_id': message.message_id}
