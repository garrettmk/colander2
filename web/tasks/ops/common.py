import json
import redis
import dramatiq
import sqlalchemy
import requests
import uuid
import time
import enum

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
            default_name = '.'.join(clazz.__module__.split('.')[:2]) + '.' + clazz.__name__
            actor_name = getattr(meta, 'actor_name', default_name)
            options.pop('actor_name', None)

            def fn(*args, **kwargs):
                """Create a new instance of the class for each call. This lets us attach a TaskContext to each
                individual instance."""
                new = clazz()
                return new(*args, **kwargs)

            clazz_instance = clazz()
            actor_instance = dramatiq.actor(fn, actor_name=actor_name, **options)
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
        # Create a new instance for each call
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
    redis = redis.from_url(Config.REDIS_URL)
    default_expire = 60

    class Status(enum.Enum):
        """Status codes for TaskContext."""
        running = 1
        paused = 2
        cancelled = 3
        complete = 4
        unknown = 5
        default = running

    # Magic methods

    def __init__(self, *messages, id=None, data=None, status=None):
        self._id = id or self._build_id()
        self.bind(*messages)

        if data is not None:
            self.data = data

        if status is not None:
            self.status = status

    def __getitem__(self, item):
        """Access an item in the context data."""
        return self.data[item]

    def __setitem__(self, key, value):
        data = self.data
        data[key] = value
        self.data = data

    def __contains__(self, item):
        return item in self.data

    # Private methods

    def _key_for(self, member):
        """Build a key based on a data member's name."""
        return f'{self._id}_{member}'

    def _decode_dicts(self, *dicts):
        """Decodes a mapping returned from Redis. If multiple dicts are provided, a tuple is returned."""
        r = tuple(
            {k.decode(): v.decode() for k, v in _dict.items()}
            for _dict in dicts
        )

        if len(dicts) == 1:
            return r[0]
        else:
            return r

    def _decode_lists(self, *lists):
        """Decodes a list of items returned from Redis. If multiple lists are provided, a tuple is returned."""
        r = tuple(
            [item.decode() for item in _list]
            for _list in lists
        )

        if len(lists) == 1:
            return r[0]
        else:
            return r

    def _build_id(self):
        """Creates an ID for a context."""
        return str(uuid.uuid4()) + '_ctx'

    # Redis properties

    @property
    def id(self):
        """Returns the ID of the context. This property is read-only."""
        return self._id

    @property
    def data(self):
        """The context's data dictionary."""
        key = self._key_for('data')
        data = self.redis.get(key)

        if data:
            return json.loads(data)
        else:
            return dict()

    @data.setter
    def data(self, new):
        key = self._key_for('data')

        if new:
            data = json.dumps(new)
            self.redis.set(key, data)
        else:
            self.redis.delete(key)

    @property
    def messages(self):
        """The messages that this context will execute."""
        key = self._key_for('messages')
        data = self.redis.zrange(key, 0, -1)
        return [dramatiq.Message(**json.loads(msg)) for msg in data]

    def bind(self, *messages):
        """Adds the message to this context's actions and returns a copy of the Dramatiq message,
        with context parameters added."""
        if not messages:
            return

        key = self._key_for('messages')
        add_messages = []

        for msg in messages:
            kwargs = msg.kwargs.copy()
            kwargs.update(_ctx=self._id, _msg_id=msg.message_id)
            new_msg = msg.copy(kwargs=kwargs)
            new_msg = json.dumps(dict(new_msg.asdict()))
            add_messages.append(time.time())
            add_messages.append(new_msg)

        self.redis.execute_command('ZADD', key, 'NX', *add_messages)
        self.persist()
        return self

    @property
    def sent(self):
        """Messages already sent to the broker."""
        key = self._key_for('sent')
        data = self.redis.zrange(key, 0, -1)
        return self._decode_lists(data)

    def send(self, *messages):
        """Send the first unsent message bound to this context. If :messages: are provided, they are bound to the
        context before a message is sent. Returns True if a message is sent, otherwise False."""

        # Bind the messages
        self.bind(*messages)

        if self.status != self.Status.running:
            return

        # Get the current state of messages and sent
        sent_key = self._key_for('sent')
        messages, sent, errors = self.messages, self.sent, self.errors

        for msg in messages:

            if msg.message_id not in sent\
                and msg.message_id not in errors\
                    and self.redis.execute_command('ZADD', sent_key, 'NX', time.time(), msg.message_id):

                broker = dramatiq.get_broker()
                broker.enqueue(msg)
                self.count_message(msg)
                return

        completed, total = self.progress()
        if completed == total:
            self.status = self.Status.complete

    @property
    def completed(self):
        """Messages that completed successfully."""
        key = self._key_for('completed')
        data = self.redis.zrange(key, 0, -1)
        return self._decode_lists(data)

    def complete(self, *message_ids):
        """Add messages to the completed list."""
        key = self._key_for('completed')
        pipe = self.redis.pipeline()

        for msg_id in message_ids:
            pipe.execute_command('ZADD', key, 'NX', time.time(), msg_id)

        pipe.execute()

    @property
    def children(self):
        """Child contexts."""
        key = self._key_for('children')
        data = self.redis.zrange(key, 0, -1)
        return self._decode_lists(data)

    def child(self, *messages, data=None):
        """Create a child context and bind it to this context."""
        status = self.status
        child_status = status if status in (self.Status.running, self.Status.paused, self.Status.cancelled) else None
        child = TaskContext(*messages, data=data, status=child_status)

        key = self._key_for('children')
        self.redis.zadd(key, child.id, time.time())
        self.persist()
        return child

    @property
    def errors(self):
        """A mapping of message IDs to error codes."""
        key = self._key_for('errors')
        data = self.redis.hgetall(key)
        errors = self._decode_dicts(data)

        for child_id in self.children:
            child = TaskContext(id=child_id)
            errors.update(**child.errors)

        return errors

    def log_error(self, msg_id, err):
        """Logs an error."""
        key = self._key_for('errors')
        self.redis.hset(key, msg_id, err)

    @property
    def counts(self):
        """How many times a given actor has been executed by this context, or one of its children."""
        key = self._key_for('counts')
        data = self.redis.hgetall(key)
        counts = {k.decode(): int(v) for k, v in data.items()}
        for child_id in self.children:
            child_counts = TaskContext(id=child_id).counts

            for actor, count in child_counts.items():
                counts[actor] = counts.get(actor, 0) + count

        return counts

    def count_message(self, msg):
        key = self._key_for('counts')
        self.redis.hincrby(key, msg.actor_name, 1)
        self.redis.hincrby('actor_counts', msg.actor_name, 1)

    def progress(self):
        completed = len(self.completed)
        total = len(self.messages)

        for child_id in self.children:
            child = TaskContext(id=child_id)
            child_completed, child_total = child.progress()
            completed += child_completed
            total += child_total

        return completed, total

    @property
    def status(self):
        """Current execution status."""
        key = self._key_for('status')
        data = self.redis.get(key)
        return self.Status(int(data)) if data is not None else self.Status.default

    @status.setter
    def status(self, status):
        """Recursively set the status of this context and its children."""
        if isinstance(status, int):
            status = self.Status(status)
        elif isinstance(status, str):
            status = self.Status[status]

        key = self._key_for('status')
        self.redis.set(key, status.value)

        if status in (self.Status.running, self.Status.paused, self.Status.cancelled):
            for child_id in self.children:
                child = TaskContext(id=child_id)
                child.status = status

        if status == self.Status.running:
            self.send()

    def copy(self):
        return self.data.copy()

    def as_dict(self):
        """Return a dictionary representation of the context object."""

        pipe = self.redis.pipeline()
        pipe.get(self._key_for('data'))
        pipe.zrange(self._key_for('messages'), 0, -1)
        pipe.zrange(self._key_for('sent'), 0, -1)
        pipe.zrange(self._key_for('completed'), 0, -1)
        pipe.zrange(self._key_for('children'), 0, -1)
        pipe.hgetall(self._key_for('errors'))
        pipe.hgetall(self._key_for('counts'))
        pipe.get(self._key_for('status'))
        data, messages, sent, completed, children, errors, counts, status = pipe.execute()

        data = json.loads(data) if data else {}
        messages = [json.loads(msg) for msg in messages]
        sent = self._decode_lists(sent)
        completed = self._decode_lists(completed)
        children = self._decode_lists(children)
        errors = self._decode_dicts(errors)
        counts = {k.decode(): int(v) for k, v in counts.items()}
        status = self.Status(int(status)) if status is not None else self.Status.default

        total_completed, total_messages = len(completed), len(messages)

        for child_id in children:
            child = TaskContext(id=child_id)

            errors.update(child.errors)

            child_completed, child_total = child.progress()
            total_completed += child_completed
            total_messages += child_total

            child_counts = child.counts
            for actor, count in child_counts.items():
                counts[actor] = counts.get(actor, 0) + count

        return {
            'id': self.id,
            'data': data,
            'messages': messages,
            'sent': sent,
            'completed': completed,
            'children': children,
            'errors': errors,
            'counts': counts,
            'progress': (total_completed, total_messages),
            'status': status.name
        }

    def expire(self, seconds=None):
        """Set all keys on this context (and its children) to expire. If :seconds: is None, keys are
        deleted immediately."""

        for child_id in self.children:
            child = TaskContext(id=child_id)
            child.expire(seconds)

        seconds = self.default_expire if seconds is None else seconds
        members = ('data', 'messages', 'sent', 'completed', 'children', 'errors', 'counts', 'status')
        keys = [self._key_for(member) for member in members]
        pipe = self.redis.pipeline()
        for key in keys:
            pipe.expire(key, seconds)
        pipe.execute()

    def persist(self):
        """Clear the expiration on all keys."""

        for child_id in self.children:
            child = TaskContext(id=child_id)
            child.persist()

        members = ('data', 'messages', 'sent', 'completed', 'children', 'errors', 'counts', 'status')
        keys = [self._key_for(member) for member in members]
        pipe = self.redis.pipeline()

        for key in keys:
            pipe.persist(key)

        pipe.execute()


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

    def __call__(self, *, _ctx=None, _msg_id=None, **params):
        """Process a call to action."""
        # Load or create the context
        if _ctx is None or isinstance(_ctx, dict):
            message = self.message(**params)
            context = TaskContext(message, data=_ctx)
            self.context = context
            self.message_id = message.message_id
        else:
            context = TaskContext(id=_ctx)
            self.context = context
            self.message_id = _msg_id

        # Update the keyword arguments using values from the context
        fields = list(self.Schema._declared_fields)  # Use _declared_fields because it preserves declaration order
        ctx_data = context.data
        kwargs = {field: ctx_data[field] for field in fields if field in ctx_data}

        # Override with actual keyword args if they we provided
        kwargs.update(params)

        # Validate against the schema
        loaded = self.Schema().load(kwargs)

        if loaded.errors:
            exc = mm.ValidationError(message=loaded.errors)
            context.log_error(_msg_id, str(exc))
            raise exc

        # Perform the action
        with app.app_context():
            try:
                result = self.perform(**loaded.data)
            except Exception as e:
                context.log_error(_msg_id, str(e))
                raise e
            else:
                context.complete(_msg_id)
                context.send()
                return result

    @classmethod
    def validate(cls, **params):
        """Validate params against the actor's schema."""
        return cls.Schema().validate(params)

    def perform(self, **kwargs):
        raise NotImplementedError


########################################################################################################################


class OpsActor(ColanderActor):

    class Meta(ColanderActor.Meta):
        abstract = True
        queue_name = 'core'
