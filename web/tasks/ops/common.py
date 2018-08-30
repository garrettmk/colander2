import json
import redis
import dramatiq
import sqlalchemy
import requests
import uuid

import marshmallow as mm

from config import Config
from core import app, db, search


########################################################################################################################


ISO_8601 = '%Y-%m-%dT%H:%M:%S'


########################################################################################################################
# The following is copied-and-modifief from the Dramatiq source code


class generic_actor(type):
    """Meta for class-based actors.
    """

    def __new__(metacls, name, bases, attrs):
        clazz = super().__new__(metacls, name, bases, attrs)
        meta = getattr(clazz, "Meta", object())
        if not getattr(meta, "abstract", False):
            options = {}

            # Use meta's inherited attributes
            ignored = ('abstract',)

            for base in reversed(meta.__mro__):
                options.update({
                    name: getattr(base, name) for name in vars(base) if not name.startswith('_') and name not in ignored
                })

            # Include the module in the actor name
            actor_name = getattr(meta, 'actor_name', f'{clazz.__module__}.{clazz.__name__}')
            options.pop('actor_name', None)

            clazz_instance = clazz()
            actor_instance = dramatiq.actor(clazz_instance, actor_name=actor_name, **options)
            setattr(clazz, "__getattr__", generic_actor.__getattr__)
            setattr(clazz_instance, "__actor__", actor_instance)
            return clazz_instance

        setattr(meta, "abstract", False)
        return clazz

    def __getattr__(cls, name):
        return getattr(cls.__actor__, name)


class GenericActor(metaclass=generic_actor):
    """Base-class for class-based actors.

    Each subclass may define an inner class named ``Meta``.  You can
    use the meta class to provide broker options for the actor.

    Classes that have ``abstract = True`` in their meta class are
    considered abstract base classes and are not converted into
    actors.  You can't send these classes messages, you can only
    inherit from them.  Actors that subclass abstract base classes
    inherit their parents' meta classes.

    Example:

      >>> class BaseTask(GenericActor):
      ...   class Meta:
      ...     abstract = True
      ...     queue_name = "tasks"
      ...     max_retries = 20
      ...
      ...   def get_task_name(self):
      ...     raise NotImplementedError
      ...
      ...   def perform(self):
      ...     print(f"Hello from {self.get_task_name()}!")

      >>> class FooTask(BaseTask):
      ...   def get_task_name(self):
      ...     return "Foo"

      >>> class BarTask(BaseTask):
      ...   def get_task_name(self):
      ...     return "Bar"

      >>> FooTask.send()
      >>> BarTask.send()

    Attributes:
      logger(Logger): The actor's logger.
      broker(Broker): The broker this actor is bound to.
      actor_name(str): The actor's name.
      queue_name(str): The actor's queue.
      priority(int): The actor's priority.
      options(dict): Arbitrary options that are passed to the broker
        and middleware.
    """

    class Meta:
        abstract = True

    @property
    def __name__(self):
        """The default name of this actor.
        """
        return type(self).__name__

    def __call__(self, *args, **kwargs):
        return self.perform(*args, **kwargs)

    def perform(self):
        """This is the method that gets called when the actor receives
        a message.  All non-abstract subclasses must implement this
        method.
        """
        raise NotImplementedError("%s does not implement perform()" % self.__name__)


########################################################################################################################


class TaskContext:
    """Holds context information for a task or group of tasks."""
    expires = 30 * 60
    redis = redis.from_url(Config.REDIS_URL)

    # Magic methods

    def __init__(self, *messages, id=None, **kwargs):
        self.id = id or self._build_id()
        self.title = kwargs.get('title', '')
        self.data = kwargs.get('data', {})
        self.messages = []
        self.sent = kwargs.get('sent', [])
        self.children = kwargs.get('children', [])
        self.errors = kwargs.get('errors', [])
        self.counts = kwargs.get('counts', {})

        if id is None:
            self._update()
        else:
            self._refresh()

        for msg in messages:
            self.bind(msg)

    def __getitem__(self, item):
        """Access an item in the context data."""
        self._refresh('data')
        return self.data[item]

    def __setitem__(self, key, value):
        self._refresh('data')
        self.data[key] = value
        self._update('data')

    def __contains__(self, item):
        self._refresh('data')
        return item in self.data

    # Private methods

    def _build_id(self):
        """Creates an ID for a context."""
        return str(uuid.uuid4()) + '_ctx'

    @staticmethod
    def _load(id):
        """Loads the entire data structure from redis."""
        redis = TaskContext.redis

        pipe = redis.pipeline()
        pipe.get(id + '_data')
        pipe.hgetall(id + '_scalars')
        pipe.smembers(id + '_messages')
        pipe.smembers(id + '_sent')
        pipe.smembers(id + '_children')
        pipe.hgetall(id + '_errors')
        pipe.hgetall(id + '_counts')
        data, scalars, messages, sent, children, errors, counts = pipe.execute()

        data = {
            'title': scalars.get(b'title', b'').decode(),
            'data': json.loads(data) if data else {},
            'messages': [dramatiq.Message(**json.loads(msg)) for msg in messages],
            'sent': [msg_id.decode() for msg_id in sent],
            'children': [child_id.decode() for child_id in children],
            'errors': {msg_id.decode(): err.decode() for msg_id, err in errors.items()},
            'counts': {act.decode(): int(cnt) for act, cnt in counts.items()}
        }

        return data

    def _refresh(self, *members):
        """Updates all or some of this context's member with data from Redis."""
        members = members or ['title', 'data', 'messages', 'sent', 'children', 'errors', 'counts']
        state = TaskContext._load(self.id)
        for member in members:
            setattr(self, member, state[member])

    def _update(self, *members):
        """Update Redis with some or all members of this context."""
        members = members or ['title', 'data', 'messages', 'sent', 'children', 'errors', 'counts']
        id = self.id
        pipe = self.redis.pipeline()

        for member in members:

            if member == 'title':
                pipe.hset(id + '_scalars', 'title', self.title)

            elif member == 'data':
                pipe.set(id + '_data', json.dumps(self.data))

            elif member == 'messages' and self.messages:
                pipe.sadd(id + '_messages', *[json.dumps(dict(msg.asdict())) for msg in self.messages])

            elif member == 'sent' and self.sent:
                pipe.sadd(id + '_sent', *self.sent)

            elif member == 'children' and self.children:
                pipe.sadd(id + '_children', *self.children)

            elif member == 'errors' and self.errors:
                pipe.hmset(id + '_errors', self.errors)

            elif member == 'counts' and self.counts:
                pipe.hmset(id + '_counts', self.counts)

        pipe.execute()

    # Properties

    @property
    def complete(self):
        sent, total = self.progress()
        try:
            return sent / total == 1
        except ZeroDivisionError:
            return False

    # Public methods

    def progress(self):
        self._refresh('sent', 'messages', 'children')

        sent = len(self.sent)
        total = len(self.messages)

        for child_id in self.children:
            child = TaskContext(id=child_id)
            child_sent, child_total = child.progress()
            sent += child_sent
            total += child_total

        return sent, total

    def copy(self):
        return self.data.copy()

    def as_dict(self):
        """Return a dictionary representation of the context object."""
        return {
            'id': self.id,
            'title': self.title,
            'data': self.data,
            'messages': [dict(msg.asdict()) for msg in self.messages],
            'sent': self.sent,
            'children': self.children,
            'errors': self.errors,
            'counts': self.counts
        }

    @classmethod
    def load(cls, id):
        """Load a context from Redis."""
        ctx = TaskContext(id=id)
        ctx._refresh()
        return ctx

    def child(self, *messages, data=None, title=None):
        """Create a child context and bind it to this context."""
        child = TaskContext(*messages, title=title, data=data)
        self.children.append(child.id)
        self._update('children')
        return child

    def message_complete(self, idx):
        """Update the status message for the action at :idx:."""
        message_id = self.messages[idx].message_id
        self.sent.append(message_id)
        self._update('sent')

    def log_error(self, msg_idx, err):
        """Log an error."""
        self._refresh('errors')

        message_id = self.messages[msg_idx].message_id
        self.errors[message_id] = err

        self._update('errors')

    def all_errors(self):
        self._refresh('errors', 'children')

        errors = {msg_id: err for msg_id, err in self.errors.items()}
        for child_id in self.children:
            child = TaskContext(id=child_id)
            errors.update(**child.all_errors())

        return errors

    def bind(self, *messages):
        """Adds the message to this context's actions and returns a copy of the Dramatiq message,
        with context parameters added."""
        if not messages:
            return

        self._refresh('messages')

        for message in messages:
            # Check that this message isn't already bound
            bound_ids = [msg.message_id for msg in self.messages]
            if message.message_id in bound_ids:
                return

            idx = len(self.messages)
            kwargs = message.kwargs.copy()
            opts = message.options.copy()

            kwargs.update({'_ctx': self.id, '_ctx_idx': idx})

            self.messages.append(message.copy(kwargs=kwargs, options=opts))

        self._update('messages')
        return self

    def send(self, *messages):
        """Send the first unsent message bound to this context. If :messages: are provided, they are bound to the
        context before a message is sent."""
        if messages:
            self.bind(messages)

        self._refresh('messages', 'sent')
        message = next((msg for msg in self.messages if msg.message_id not in self.sent), None)
        if message is None:
            return

        self.sent.append(message.message_id)
        self.counts[message.actor_name] = self.counts.get(message.actor_name, 0) + 1
        self._update('sent', 'counts')

        broker = dramatiq.get_broker()
        broker.enqueue(message)

    def send_all(self):
        """Sends all messages simultaneously."""
        raise NotImplementedError

    def counts(self):
        counts = self.counts.copy()
        for child_id in self.children:
            child_counts = TaskContext(id=child_id).counts()

            for actor in child_counts:
                counts[actor] = counts.get(actor, 0) + 1

        return counts


########################################################################################################################


class ContextExpiredError(Exception):
    pass


########################################################################################################################


class ColanderActor(GenericActor):
    """A base class for core and extension actors, primarily those exposed to the API."""
    public = False

    class Meta:
        abstract = True
        min_backoff = 5000,
        max_backoff = 300000,

        @staticmethod
        def retry_when(retries, exc):
            return retries < 3 and isinstance(exc, (
                sqlalchemy.exc.InternalError,
                sqlalchemy.exc.OperationalError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout
            ))

    class Schema(mm.Schema):
        """Schema for this actor's parameters."""

    def _create_context(self, message, data):
        """Create a context for this actor, if one wasn't supplied."""
        context = TaskContext(message, title=type(self).__name__, data=data)
        self.context = context
        self.context_idx = 0

    def _load_context(self, id, idx=None):
        """Load a context using its ID."""
        context = TaskContext(id=id)

        self.context = context
        self.context_idx = idx

    def __call__(self, *, _ctx=None, _ctx_idx=None, **params):
        """Process a call to action."""

        # Pull up the context, if any
        if _ctx is None or isinstance(_ctx, dict):
            msg = dramatiq.Message(
                queue_name='',
                actor_name=self.actor_name,
                args=[],
                kwargs=params,
                options={}
            )
            self._create_context(msg, _ctx)
        else:
            self._load_context(_ctx, _ctx_idx)

        # Update the keyword arguments using values from the context
        fields = list(self.Schema._declared_fields)  # Use _declared_fields because it preserves declaration order
        kwargs = {field: self.context[field] for field in fields if field in self.context}

        # Override with actual keyword args if they we provided
        kwargs.update(params)

        # Validate against the schema
        loaded = self.Schema().load(kwargs)

        if loaded.errors:
            exc = mm.ValidationError(message=loaded.errors)
            self.context.log_error(self.context_idx, str(exc))
            raise exc

        # Perform the action
        with app.app_context():
            try:
                result = self.perform(**loaded.data)
            except Exception as e:
                self.context.log_error(self.context_idx, str(e))
                raise e
            else:
                self.context.send()
                return result

    @classmethod
    def validate(cls, **params):
        """Validate params against the actor's schema."""
        return cls.Schema().validate(params)


########################################################################################################################


class OpsActor(ColanderActor):

    class Meta(ColanderActor.Meta):
        abstract = True
        queue_name = 'core'
