import itertools
import pytest
from unittest.mock import Mock

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app import db as _db
from .fixtures import app, db, session, vendors, listings, market_listings, details, more_details, market_details,\
    more_market_details, inventory_details, more_inventory_details, markets
from models.core import quantize_decimal
from models.entities import Vendor
from models.listings import QuantityMap, Listing, ListingDetails, detail_property, MarketListing, MarketListingDetails,\
    InventoryDetails


########################################################################################################################


def test_listing_details_listing_id_non_null(session):
    details = ListingDetails()
    session.add(details)

    with pytest.raises(IntegrityError):
        session.commit()


def test_listing_details_timestamp(details, more_details):
    age_check = datetime.utcnow() - timedelta(seconds=5)

    for d, md in zip(details, more_details):
        assert d.timestamp is not None and md.timestamp is not None
        assert d.timestamp > age_check and md.timestamp > age_check
        assert md.timestamp > d.timestamp


def test_listing_details_delete_cascade(session, details):
    assert session.query(ListingDetails).count() > 0
    session.query(Listing).delete()
    session.commit()
    assert session.query(ListingDetails).count() == 0


def test_listing_details_listing_relationship(session, listings, details, more_details):
    for listing in listings:
        listing_details = session.query(ListingDetails)\
            .filter_by(listing_id=listing.id)\
            .order_by(ListingDetails.timestamp.asc())\
            .all()

        assert listing.details == listing_details

        for deets in listing_details:
            assert deets.listing is listing


########################################################################################################################


def test_listing_vendor_id_non_null(session):
    l1 = Listing(sku='12345')
    session.add(l1)

    with pytest.raises(IntegrityError):
        session.commit()


def test_listing_sku_non_null(session, vendors):
    v1 = vendors[0]
    l1 = Listing(vendor_id=v1.id)
    session.add(l1)

    with pytest.raises(IntegrityError):
        session.commit()


def test_listing_vendor_sku_unique(session, vendors):
    v1 = vendors[0]
    l1, l2 = Listing(vendor_id=v1.id, sku='1234'), Listing(vendor_id=v1.id, sku='1234')
    session.add_all((l1, l2))

    with pytest.raises(IntegrityError):
        session.commit()


def test_listing_vendor_delete_cascade(session, vendors, listings):
    v1 = vendors[0]
    count = session.query(Listing).count()
    v1_count = session.query(Listing).filter_by(vendor_id=v1.id).count()

    session.delete(v1)
    session.commit()

    assert session.query(Listing).count() == (count - v1_count)


def test_vendor_relationship(session, vendors, listings):
    v1 = vendors[0]
    l1 = session.query(Listing).filter_by(vendor_id=v1.id).first()

    assert l1.vendor is v1


def test_detail_properties_attributes(session, listings):
    l1 = listings[0]
    assert not l1.details

    l1.price = 1.11
    assert l1.details

    l1.rank = 10
    assert len(l1.details) == 1

    session.add(l1)
    session.commit()
    assert l1.details[0].id

    l1.price = 1.22
    assert len(l1.details) == 2
    assert l1.details[-1].price == 1.22
    assert l1.rank is None


def test_detail_properties_attributes_2(session, listings, more_details):
    for listing, deets in zip(listings, more_details):
        assert listing.price == deets.price
        assert listing.rank == deets.rank
        assert listing.rating == deets.rating


def test_detail_properties_expression(session, listings, details, more_details):
    for deets in details:
        assert session.query(Listing).filter_by(price=deets.price).first() is None
        assert session.query(Listing).filter(Listing.rank == deets.rank).first() is None

    for deets in more_details:
        assert session.query(Listing).filter_by(price=deets.price).one() is deets.listing
        assert session.query(Listing).filter(Listing.rank == deets.rank).one() is deets.listing

    listings = sorted(listings, key=lambda l: l.price, reverse=True)
    assert session.query(Listing).order_by(Listing.price.desc()).all() == listings

    listings = sorted(filter(lambda l: l.price > 5, listings), key=lambda l: l.price, reverse=True)
    assert session.query(Listing).filter(Listing.price > 5).order_by(Listing.price.desc()).all() == listings


def test_market_detail_properties_expression(session, market_listings, market_details, more_market_details):
    for deets in market_details:
        assert session.query(MarketListing).filter_by(price=deets.price).first() is None
        assert session.query(MarketListing).filter(MarketListing.selling_fees == deets.selling_fees).first() is None

    for deets in more_market_details:
        assert session.query(MarketListing).filter_by(price=deets.price).one() is deets.listing
        assert session.query(MarketListing).filter(MarketListing.selling_fees == deets.selling_fees).one() is deets.listing

    listings = sorted(market_listings, key=lambda l: l.price, reverse=True)
    assert session.query(MarketListing).order_by(MarketListing.price.desc()).all() == listings

    listings = sorted(filter(lambda l: l.selling_fees > 6, market_listings), key=lambda l: l.selling_fees, reverse=True)
    assert session.query(MarketListing).filter(MarketListing.selling_fees > 6).order_by(MarketListing.selling_fees.desc()).all() == listings


def test_inventory_property_attributes(session, market_listings, inventory_details, more_inventory_details):
    for listing, deets in zip(market_listings, more_inventory_details):
        assert listing.active == deets.active
        assert listing.fulfillable == deets.fulfillable


def test_inventory_properties_expressions(session, market_listings, market_details, inventory_details, more_inventory_details):
    for deets in inventory_details:
        assert session.query(MarketListing).filter_by(fulfillable=deets.fulfillable).first() is None
        assert session.query(MarketListing).filter(MarketListing.reserved == deets.reserved).first() is None

    for deets in more_inventory_details:
        assert session.query(MarketListing).filter_by(fulfillable=deets.fulfillable).first() is deets.listing
        assert session.query(MarketListing).filter(MarketListing.fulfillable == deets.fulfillable).first() is deets.listing

    listings = sorted(market_listings, key=lambda l: l.fulfillable, reverse=True)
    assert session.query(MarketListing).order_by(MarketListing.fulfillable.desc()).all() == listings

    listings = sorted(filter(lambda l: l.fulfillable > 3, market_listings), key=lambda l: l.fulfillable, reverse=True)
    assert session.query(MarketListing).filter(MarketListing.fulfillable > 3).order_by(MarketListing.fulfillable.desc()).all() == listings


########################################################################################################################


def test_estimated_cost_attribute(session, vendors, listings, details):
    listings[0].price = None

    for vendor, listing in zip(vendors, listings):
        tax_rate, ship_rate = vendor.avg_tax, vendor.avg_shipping
        if listing.price is not None:
            est_cost = quantize_decimal(listing.price * Decimal(1 + tax_rate + ship_rate))
            assert listing.estimated_cost == est_cost
        else:
            assert listing.estimated_cost is None


def test_estimated_cost_expression(session, vendors, listings, details):
    listings[0].price = None
    session.commit()

    assert Listing.estimated_cost is not None

    for vendor, listing in zip(vendors, listings):
        id, est_cost = session.query(Listing.id, Listing.estimated_cost).filter_by(id=listing.id).first()

        if listing.price is None:
            assert est_cost is None
        else:
            tax = Decimal(vendor.avg_tax) * listing.price
            shipping = Decimal(vendor.avg_shipping) * listing.price
            total = quantize_decimal(listing.price + tax + shipping)
            assert est_cost == total


def test_estimated_unit_cost_attribute(session, vendors, listings, details):
    listings[0].price = None
    session.commit()

    valid_cost_exists = False
    invalid_cost_exists = False

    for vendor, listing in zip(vendors, listings):
        cost, quantity = listing.estimated_cost, listing.quantity

        if None in (cost, quantity):
            unit_cost = None
            invalid_cost_exists = True
        else:
            unit_cost = cost / quantity
            valid_cost_exists = True

        assert listing.estimated_unit_cost == unit_cost

    assert valid_cost_exists
    assert invalid_cost_exists


def test_estimated_unit_cost_expression(session, vendors, listings, details):
    listings[0].price = None
    session.commit()

    valid_cost_exists = False
    invalid_cost_exists = False

    for listing in listings:
        cost, quantity = listing.estimated_cost, listing.quantity

        if None in (cost, quantity):
            unit_cost = None
            invalid_cost_exists = True
        else:
            unit_cost = cost / quantity
            valid_cost_exists = True

        assert session.query(
            Listing.id,
            Listing.estimated_unit_cost
        ).filter(
            Listing.id == listing.id
        ).first()[1] == unit_cost

    assert valid_cost_exists
    assert invalid_cost_exists


@pytest.mark.parametrize('quantity_desc,quantity', [
    (None, None),
    (None, 12),
    ('dozen', None),
    ('dozen', 12)
])
def test_guess_quantity(session, quantity_desc, quantity):
    l1 = Listing(quantity=quantity, quantity_desc=quantity_desc, title='Some stuff (dozen)')

    if quantity_desc is None and quantity is None:
        qmap = QuantityMap(text='dozen', quantity=12)
        session.add(qmap)
        session.commit()

        l1.guess_quantity()

        assert l1.quantity_desc == 'dozen'
        assert l1.quantity == 12

    elif quantity_desc is None and quantity is not None:
        q = l1.quantity

        l1.guess_quantity()

        assert l1.quantity_desc is None
        assert l1.quantity == q

    elif quantity_desc is not None and quantity is None:
        qmap = QuantityMap(text='dozen', quantity=12)
        session.add(qmap)
        session.commit()

        l1.guess_quantity()

        assert l1.quantity == 12

    elif quantity_desc and quantity:
        l1.guess_quantity()

        qmap = QuantityMap.query.first()

        assert qmap is not None
        assert qmap.text == quantity_desc
        assert qmap.quantity == quantity


def test_auto_guess_quantity(session, vendors):
    """Make sure that quess_quantity() is called automatically when a listing is created or modified."""
    v1 = vendors[0]
    l1 = Listing(vendor=v1, sku='1234', title='Things')
    l1.guess_quantity = Mock()

    session.add(l1)
    session.commit()

    # Should be called for new listings
    assert l1.guess_quantity.called
    l1.guess_quantity.reset_mock()

    # Should not be called if unrelated properties are not modified
    l1.model = 'hey'
    session.commit()
    assert not l1.guess_quantity.called
    l1.guess_quantity.reset_mock()

    # Should be called if title or quantity_desc are changed
    l1.title = 'A dozen things'
    session.commit()
    assert l1.guess_quantity.called
    l1.guess_quantity.reset_mock()

    l1.quantity_desc = 'dozen'
    session.commit()
    assert l1.guess_quantity.called


