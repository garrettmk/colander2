import pytest
import itertools

from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from .fixtures import app, db, session, vendors, listings
from models.entities import Entity, Vendor
from models.listings import Listing
from models.orders import Order, OrderItem, VendorOrder, VendorOrderItem, Shipment


########################################################################################################################


@pytest.fixture(scope='function')
def orders(session, vendors):
    orders = (
        Order(source_id=vendors[0].id, dest_id=vendors[1].id),
        Order(source_id=vendors[1].id, dest_id=vendors[2].id),
        Order(source_id=vendors[2].id, dest_id=vendors[0].id)
    )

    session.add_all(orders)
    session.commit()
    return orders


@pytest.fixture(scope='function')
def order_items(session, orders, listings):
    order_items = (
        OrderItem(order_id=orders[0].id, listing_id=listings[0].id),
        OrderItem(order_id=orders[1].id, listing_id=listings[1].id),
        OrderItem(order_id=orders[2].id, listing_id=listings[2].id)
    )

    session.add_all(order_items)
    session.commit()
    return order_items


@pytest.fixture(scope='function')
def shipments(session, orders, order_items):
    shipments = (
        Shipment(order_id=orders[0].id),
        Shipment(order_id=orders[1].id),
        Shipment(order_id=orders[2].id)
    )

    session.add_all(shipments)
    session.commit()

    for item, shipment in zip(order_items, shipments):
        item.shipment_id = shipment.id

    session.commit()
    return shipments


########################################################################################################################


def test_order_source_non_null(session, vendors):
    """Ensure that we can't have an Order without a source."""
    v1 = vendors[0]
    o1 = Order(dest_id=v1.id)
    session.add(o1)

    with pytest.raises(IntegrityError):
        session.commit()


def test_order_source_delete_restrict(session, orders):
    """Ensure that we can't orphan an Order by deleting it's source."""
    o1 = orders[0]
    e1 = session.query(Entity).filter_by(id=o1.source_id).first()

    with pytest.raises(IntegrityError):
        session.delete(e1)
        session.commit()


def test_order_dest_non_null(session, vendors):
    """Ensure that we can't have an Order without a destination."""
    v1 = vendors[0]
    o1 = Order(source_id=v1.id)
    session.add(o1)

    with pytest.raises(IntegrityError):
        session.commit()


def test_order_dest_delete_restrict(session, orders):
    """Ensure that we can't orphan an Order by deleting its destination."""
    o1 = orders[0]
    e1 = session.query(Entity).filter_by(id=o1.dest_id).first()

    with pytest.raises(IntegrityError):
        session.delete(e1)
        session.commit()


def test_order_date_default(orders):
    """Check the default value for Order.date"""
    age_check = datetime.utcnow() - timedelta(seconds=5)
    for order in orders:
        assert order.date > age_check


def test_order_order_number_unique(session, orders):
    """Ensure that we can't have duplicate orders from the same source."""
    o1, o2 = orders[0], Order()
    o2.source_id = o1.source_id
    o1.order_number, o2.order_number = 'same', 'same'
    session.add(o2)

    with pytest.raises(IntegrityError):
        session.commit()


def test_order_items_relationship(session, orders, order_items):
    """Make sure the items relationship works."""
    for order, item in zip(orders, order_items):
        assert order.items[0] is item
        assert item.order is order


def test_order_shipments_relationship(session, orders, shipments):
    """Make sure the shipments relationship works."""
    for order, shipment in zip(orders, shipments):
        assert order.shipments[0] is shipment
        assert shipment.order is order


########################################################################################################################


def test_order_item_order_non_null(session, listings):
    """Ensure that we can't have an OrderItem with no Order."""
    l1 = listings[0]
    oi1 = OrderItem(listing_id=l1.id)
    session.add(oi1)

    with pytest.raises(IntegrityError):
        session.commit()


def test_order_item_order_delete_cascade(session, orders, order_items):
    """Ensure that OrderItems get deleted when the Order is deleted."""
    assert session.query(OrderItem).count() > 0
    session.query(Order).delete()
    assert session.query(OrderItem).count() == 0


def test_order_item_listing_non_null(session, orders):
    """Ensure that we can't have an OrderItem with no listing."""
    o1 = orders[0]
    oi1 = OrderItem(order_id=o1.id)
    session.add(oi1)

    with pytest.raises(IntegrityError):
        session.commit()


def test_order_item_listing_delete_restrict(session, order_items, listings):
    """Ensure that we can't orphan an OrderItem by deleting its listing."""
    with pytest.raises(IntegrityError):
        session.query(Listing).delete()


def test_order_item_dest_delete_restrict(session, listings, order_items):
    """Ensure that we can't orphan an OrderItem by deleting its destination."""
    l1 = listings[1]  # The items source is listing[0]
    oi1 = order_items[0]
    oi1.dest_id = l1.id
    session.commit()

    with pytest.raises(IntegrityError):
        session.delete(l1)
        session.commit()


def test_order_item_quantity_non_null(session, order_items):
    """Make sure we can't have an OrderItem with an invalid quantity."""
    oi1 = order_items[0]
    oi1.quantity = None

    with pytest.raises(IntegrityError):
        session.commit()


def test_order_item_quantity_default(session, order_items):
    """Check the default value for OrderItem.quantity"""
    for item in order_items:
        assert item.quantity == 1


def test_order_item_order_relationship(session, orders, order_items):
    """Make sure the relationship to the parent Order works."""
    for order, item in zip(orders, order_items):
        assert order.items[0] is item
        assert item.order is order


def test_order_item_listing_relationship(session, order_items, listings):
    """Make sure the relationship to the source listing works."""
    for item, listing in zip(order_items, listings):
        assert listing.order_items[0] is item
        assert item.listing is listing


def test_order_item_destination_relationship(session, order_items, listings):
    """Make sure the relationship to the destination listing works."""
    for item, listing in zip(order_items, listings):
        item.dest_id = listing.id

    session.commit()

    for item, listing in zip(order_items, listings):
        assert item.destination is listing
        assert listing.fulfillments[0] is item


def test_order_item_shipment_relationship(session, order_items, shipments):
    """Make sure the relationship to the Shipment works."""
    for item, shipment in zip(order_items, shipments):
        assert item.shipment is shipment
        assert shipment.items[0] is item


########################################################################################################################


def test_shipment_order_non_null(session):
    """Ensure that we can't create an orphan shipment."""
    s1 = Shipment()
    session.add(s1)

    with pytest.raises(IntegrityError):
        session.commit()


def test_shipment_order_delete_cascade(session, orders, shipments):
    assert session.query(Shipment).count() > 0
    session.query(Order).delete()
    session.commit()
    assert session.query(Shipment).count() == 0


def test_shipment_created_on_default(session, shipments):
    """Check the default value for Shipment.created_on"""
    age_check = datetime.utcnow() - timedelta(seconds=5)
    for shipment in shipments:
        assert shipment.created_on > age_check


def test_shipment_updated_on_default(session, shipments):
    """Check the default value for Shipment.updated_on"""
    age_check = datetime.utcnow() - timedelta(seconds=5)
    for shipment in shipments:
        assert shipment.updated_on > age_check


def test_shipment_updated_on_update(session, shipments):
    """Make sure that Shipment.updated_on updates automatically."""
    olds = [s.updated_on for s in shipments]
    for shipment in shipments:
        shipment.status = 'updated'
    session.commit()

    for old, shipment in zip(olds, shipments):
        assert shipment.updated_on > old


def test_shipment_order_items_relationship(session, shipments, order_items):
    """Check the relationship to this shipment's OrderItems."""
    for item, shipment in zip(order_items, shipments):
        assert item.shipment is shipment
        assert shipment.items[0] is item


def test_shipment_order_relationship(session, orders, shipments):
    """Check the relationship to this shipment's Order."""
    for order, shipment in zip(orders, shipments):
        assert shipment.order is order
        assert order.shipments[0] is shipment


########################################################################################################################
