import pytest
from app import db as _db
from .fixtures import app, db, session

from models.core import User, UpdateMixin
from sqlalchemy.exc import IntegrityError


########################################################################################################################


class UpdateMixinTester(UpdateMixin, _db.Model):
    id = _db.Column(_db.Integer, primary_key=True)
    field1 = _db.Column(_db.String(32))
    field2 = _db.Column(_db.Integer)
    field3 = _db.Column(_db.Boolean)


########################################################################################################################


def test_update_mixin_defaults(session):
    """Check the default values for UpdateMixin's columns."""
    # When the object is created
    obj1 = UpdateMixinTester()
    assert obj1.extra == {}

    # When the object is committed
    obj2 = UpdateMixinTester()
    session.add(obj2)
    session.commit()
    assert obj2.extra == {}


def test_update_mixin(session):
    """Test the UpdateMixin class."""

    obj1, obj2 = UpdateMixinTester(), UpdateMixinTester()

    # These values should get assigned to columns
    columns = {
        'field1': 'some text',
        'field2': 1234,
        'field3': True,
    }

    # These values should get dumped in `extra`
    extra = {
        'extra1': 'some text',
        'extra2': 1234
    }

    # __init__() only accept one arg, a mapping
    with pytest.raises(TypeError):
        obj1.update('only accepts collections.Mapping')

    # Or, nothing but keyword args
    with pytest.raises(ValueError):
        obj1.update('only', 'accepts', 'one', 'arg')

    combined = dict(**columns, **extra)

    # Data as an arg
    obj1.update(combined)

    # Data as kwargs
    obj2.update(**combined)

    # Make sure everything was assigned correctly
    for name, value in columns.items():
        assert getattr(obj1, name) == value
        assert getattr(obj2, name) == value

    for name, value in extra.items():
        assert obj1.extra[name] == value
        assert obj2.extra[name] == value


########################################################################################################################


def test_user_set_password(session):
    user = User()
    user.set_password('password')

    assert user.password_hash is not None
    assert user.password_hash != 'password'

    user2 = User(password='password')
    assert user2.password_hash is not None
    assert user2.password_hash != 'password'


def test_user_password_non_null(session):
    user = User(name='garrett')
    session.add(user)

    with pytest.raises(IntegrityError):
        session.commit()


def test_user_name_non_null(session):
    user = User(password='foo')
    session.add(user)

    with pytest.raises(IntegrityError):
        session.commit()


def test_user_name_unique(session):
    user1, user2 = User(name='first', password='foo'), User(name='first', password='bar')
    session.add_all((user1, user2))

    with pytest.raises(IntegrityError):
        session.commit()
