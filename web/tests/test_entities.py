import pytest
from sqlalchemy.exc import IntegrityError

from .fixtures import app, db, session
from models.entities import Entity, Customer, Vendor, Market


########################################################################################################################


def test_entity(session):
    ent = Entity()

    session.add(ent)
    session.commit()

    assert ent.id > 0


def test_entity_name_unique(session):
    ent1 = Entity(name='one')
    ent2 = Entity(name='one')

    session.add_all((ent1, ent2))

    with pytest.raises(IntegrityError):
        session.commit()


def test_vendor_url_unique(session):
    v1 = Vendor(name='first', url='www.first.com')
    v2 = Vendor(name='second', url='www.first.com')
    session.add_all((v1, v2))

    with pytest.raises(IntegrityError):
        session.commit()


def test_vendor_defaults(session):
    v1 = Vendor(name='first')
    session.add(v1)
    session.commit()

    assert v1.avg_tax is not None
    assert v1.avg_shipping is not None


def test_market_defaults(session):
    m1 = Market()
    session.add(m1)
    session.commit()

    assert m1.avg_selling_fees is not None


def test_entity_polymorphism(db, session):
    entities = (
        Customer(), Customer(),
        Vendor(), Vendor(),
        Market(), Market()
    )

    session.add_all(entities)
    session.commit()

    for type in (Entity, Customer, Vendor, Market):
        assert session.query(type).all() == list(filter(lambda e: isinstance(e, type), entities))

