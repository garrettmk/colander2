import importlib
import marshmallow as mm

from dramatiq import GenericActor
from sqlalchemy.orm import reconstructor
from marshmallow_jsonschema import JSONSchema

from app import db
from core import JSONB
from .mixins import SearchMixin


########################################################################################################################


class Extension(db.Model, SearchMixin):
    """A module of code."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)
    module = db.Column(db.Text, nullable=False, unique=True)
    exports = db.Column(JSONB, default=dict, nullable=False)

    tasks = db.relationship('Task', back_populates='extension')

    class QuickResult(mm.Schema):
        id = mm.fields.Int()
        type = mm.fields.Str()
        title = mm.fields.Str(attribute='name')
        description = mm.fields.Function(lambda obj: f'ext.{obj.module}')

    def __repr__(self):
        name = self.name or self.module or self.id
        return f'<{type(self).__name__} {name}>'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._m = None
        self.load_module()

    @reconstructor
    def __init_on_load___(self):
        self._m = None

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
        actors = [s for s in symbols if isinstance(s, GenericActor) and getattr(s, 'public', False)]

        self._m = mod
        self.name = self.name or self.module
        self.exports = {
            a.actor_name: {
                'doc': getattr(a, '__doc__', a.__class__.__doc__),
                'schema': JSONSchema().dump(a.Schema()).data['definitions']['Schema']
            }
        for a in actors}

    def send(self, action, *args, **kwargs):
        """Call an actor asynchronously and returns the message ID."""
        if action not in self.exports:
            raise ValueError(f'Unknown export: {action}')

        message = getattr(self.m, action).send(*args, **kwargs)
        return {'message_id': message.message_id}

    def call(self, action, *args, **kwargs):
        """Call an actor synchronously and return it's return value."""
        if action not in self.exports:
            raise ValueError(f'Unknown export: {action}')

        return getattr(self.m, action)(*args, **kwargs)


########################################################################################################################


class Task(db.Model, SearchMixin):
    """Stores info on recurring tasks."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)
    ext_id = db.Column(db.Integer, db.ForeignKey('extension.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(64), nullable=False)
    params = db.Column(JSONB, default=dict)
    schedule = db.Column(JSONB, default=dict)

    extension = db.relationship('Extension', back_populates='tasks')

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
