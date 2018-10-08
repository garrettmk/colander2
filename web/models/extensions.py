import importlib

import sqlalchemy as sa
import flask_sqlalchemy as flsa
import marshmallow as mm
import marshmallow.fields as mmf
import marshmallow_jsonschema as mmjs
import sqlalchemy_jsonbase as jb

from core import db, JSONB
from tasks.broker import setup_dramatiq
setup_dramatiq()
from tasks.ops.common import TaskContext, ColanderActor
from .mixins import SearchMixin


########################################################################################################################


class Extension(db.Model, SearchMixin):
    """A module of code."""
    id = jb.Column(db.Integer, primary_key=True, label='Extension ID')
    name = jb.Column(db.Text, nullable=False, unique=True, label='Name')
    module = jb.Column(db.Text, nullable=False, unique=True, label='Module (ext.)')
    exports = jb.Column(JSONB, default=dict, nullable=False, label='Exports')

    tasks = jb.relationship('Task', back_populates='extension', uselist=True, label='Extensions')
    instances = jb.relationship('TaskInstance', back_populates='extension', uselist=True, label='Instances')

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
        actors = [s for s in symbols if isinstance(s, ColanderActor) and getattr(s, 'public', False)]

        self._m = mod
        self.name = self.name or self.module
        self.exports = {
            a.__class__.__name__: {
                'doc': getattr(a, '__doc__', a.__class__.__doc__),
                'schema': mmjs.JSONSchema().dump(a.Schema()).data['definitions']['Schema']
            } for a in actors}

    def send(self, action, name=None, context=None, **params):
        """Call an actor asynchronously and returns the message ID."""

        # Auto-generate a name if none provided
        if name is None:
            name = f'{action}: {context or params}'

        # Get the actor and use it to build a context
        message = self.message(action, **params)

        ctx = TaskContext(message, data=context)
        ctx.send()

        instance = TaskInstance(context_id=ctx.id, name=name, extension=self)
        db.session.add(instance)
        db.session.commit()

        return instance

    def message(self, action, **kwargs):
        """Return a message from the given action, which can be sent later."""
        if action not in self.exports:
            raise ValueError(f'Unknown export: {action}')

        message = getattr(self.m, action).message(**kwargs)
        return message

    def call(self, action, *args, **kwargs):
        raise NotImplementedError


########################################################################################################################


class Task(db.Model, SearchMixin):
    """Stores info on recurring tasks."""
    id = jb.Column(db.Integer, primary_key=True)
    name = jb.Column(db.Text, nullable=False, unique=True)
    ext_id = jb.Column(db.Integer, db.ForeignKey('extension.id', ondelete='CASCADE'))
    action = jb.Column(db.String(64), nullable=False)
    context = jb.Column(JSONB, default=dict)
    schedule = jb.Column(JSONB, default=dict)

    extension = jb.relationship('Extension', back_populates='tasks')

    def __init__(self, *args, **kwargs):
        self.params = {}
        self.options = {}
        self.schedule = {}
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f'<{type(self).__name__} {self.name or self.id}>'

    def send(self, **kwargs):
        return TaskInstance.create_from(self, **kwargs)


########################################################################################################################


def ListOf(type):
    def _listof(**kwargs):
        return mmf.List(type, **kwargs)

    return _listof


class TaskInstance(db.Model, SearchMixin):
    """Keeps track of a task context."""
    id = jb.Column(db.Integer, primary_key=True)
    name = jb.Column(db.Text)
    context_id = jb.Column(db.Text, unique=True)

    extension_id = jb.Column(db.Integer, db.ForeignKey('extension.id'), nullable=False)
    extension = jb.relationship('Extension', back_populates='instances')

    def __init__(self, *, action=None, data=None, status=None, **kwargs):
        if action is not None:
            # Get the extension
            if 'extension' in kwargs:
                extension = kwargs.get['extension']
            elif 'extension_id' in kwargs:
                extension = Extension.query.filter_by(id=kwargs['extension_id']).one()
            elif '.' in action:
                module = action.split('.')[-2]
                extension = Extension.query.filter_by(module=module).one()
            else:
                raise ValueError(f'extension, extension_id, or qualified action is requirecd.')

            # Get a message for the action
            action = action.split('.')[-1]
            message = extension.message(action)

            # Create a task context
            ctx = TaskContext(message, data=data, status=status)
            kwargs['context_id'] = ctx.id

            if 'name' not in kwargs:
                kwargs['name'] = f'{action}: {ctx.id}'

        super().__init__(**kwargs)
        self._context = TaskContext(id=self.context_id)

    @classmethod
    def from_json(cls, data):
        return cls(**data)

    @sa.orm.reconstructor
    def reconstructor(self):
        self._context = TaskContext(id=self.context_id)

    @classmethod
    def before_commit(cls, session):
        """Hold on to any deleted trackers so we can expire their contexts."""
        session._deleted_trackers = [obj for obj in session.deleted if isinstance(obj, cls)]

    @classmethod
    def after_commit(cls, session):
        """Expire any deleted contexts."""
        for tracker in session._deleted_trackers:
            tracker.expire()

    @classmethod
    def register_hooks(cls):
        """Register lifecycle hooks with the database session."""
        db.event.listen(flsa.SignallingSession, 'before_commit', cls.before_commit)
        db.event.listen(flsa.SignallingSession, 'after_commit', cls.after_commit)

    @property
    def ctx(self):
        return self._context

    @jb.property(label='Context', format='object', field=mmf.Dict)
    def data(self):
        return self._context.data if self._context else {}

    @jb.property(label='Unsent messages', format='array', field=ListOf(mmf.String))
    def messages(self):
        messages = self._context.messages
        return [dict(msg.asdict()) for msg in messages]

    @jb.property(label='Sent messages', format='array', field=ListOf(mmf.String))
    def sent(self):
        return self._context.sent

    @jb.property(label='Completed messages', format='array', field=ListOf(mmf.String))
    def completed(self):
        return self._context.completed

    @jb.property(label='Child contexts', format='array', field=ListOf(mmf.String))
    def children(self):
        return self._context.children

    @jb.property(label='Errors', format='object', field=mmf.Dict)
    def errors(self):
        return self._context.errors

    @jb.property(label='Message counts', format='object', field=mmf.Dict)
    def counts(self):
        return self._context.counts

    @jb.property(label='Progress', format='array', field=ListOf(mmf.Int))
    def progress(self):
        return self._context.progress()

    @jb.property(label='Status', format='string', field=mmf.String)
    def status(self):
        return self._context.status

    @status.setter
    def status(self, value):
        self._context.status = value

    def expire(self, seconds=None):
        return self._context.expire(seconds)

    # TODO: Override to_json() to reduce the number of redis ops
    # def to_json(self, *args, _schema='__schema__', **kwargs):
    #     schema_cls = getattr(self, _schema)
    #
    #     if len(args) == 1 and isinstance(args[0], dict):
    #         params = args[0]
    #     elif args:
    #         raise ValueError(f'Only valid arg is a dict, got {args}')
    #     else:
    #         params = jb.ViewSchema(context={'_exclude_rels': schema_cls}).load(kwargs).data
    #
    #     schema = schema_cls(**params)
    #
    #
    #     data = self._context.as_dict()
    #     data.update(
    #         id=self.id,
    #         name=self.name,
    #
    #     )


TaskInstance.register_hooks()