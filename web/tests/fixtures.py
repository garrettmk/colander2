import pytest

from app import create_app, Config
from app import db as _db
from models.entities import Vendor, Market, Customer
from models.listings import Listing, ListingDetails, MarketListing, MarketListingDetails, InventoryDetails


########################################################################################################################


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:passwd@database:5432/testing'


########################################################################################################################


@pytest.fixture(scope='session')
def app(request):
    """Session-wide test Flask app."""
    app = create_app(TestingConfig)

    # Establish an app context before running tests
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app


@pytest.fixture(scope='session')
def db(app, request):
    """Session-wide test database."""

    def teardown():
        _db.drop_all()

    _db.app = app
    _db.create_all()

    request.addfinalizer(teardown)
    return _db


@pytest.fixture(scope='function')
def session(db, request):
    """Creates a new database session for the test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    options = {
        'bind': connection,
        'binds': {}
    }

    session = db.create_scoped_session(options=options)
    db.session = session

    def teardown():
        transaction.rollback()
        connection.close()
        session.remove()

    request.addfinalizer(teardown)
    return session


########################################################################################################################


@pytest.fixture(scope='function')
def vendors(session):
    vendors = (
        Vendor(name='Vendor One', avg_tax=.1, avg_shipping=.1),
        Vendor(name='Vendor Two', avg_tax=.2, avg_shipping=.2),
        Vendor(name='Vendor Three')
    )

    session.add_all(vendors)
    session.commit()
    return vendors


@pytest.fixture(scope='function')
def listings(session, vendors):
    listings = (
        Listing(vendor_id=vendors[0].id, sku='L1234', quantity=1),
        Listing(vendor_id=vendors[1].id, sku='L2345', quantity=2),
        Listing(vendor_id=vendors[2].id, sku='L3456', quantity=3)
    )

    session.add_all(listings)
    session.commit()
    return listings


@pytest.fixture(scope='function')
def details(session, listings):
    details = (
        ListingDetails(listing_id=listings[0].id, price=1.11, rank=10, rating=0.1),
        ListingDetails(listing_id=listings[1].id, price=2.22, rank=20, rating=0.2),
        ListingDetails(listing_id=listings[2].id, price=3.33, rank=30, rating=0.3)
    )

    session.add_all(details)
    session.commit()
    return details


@pytest.fixture(scope='function')
def more_details(session, listings):
    more_details = (
        ListingDetails(listing_id=listings[0].id, price=4.44, rank=40, rating=.4),
        ListingDetails(listing_id=listings[1].id, price=5.55, rank=50, rating=.5),
        ListingDetails(listing_id=listings[2].id, price=6.66, rank=60, rating=.6)
    )

    session.add_all(more_details)
    session.commit()
    return more_details


@pytest.fixture(scope='function')
def markets(session):
    markets = (
        Market(name='Market One', avg_tax=.1, avg_shipping=.1, avg_selling_fees=.1),
        Market(name='Market Two', avg_tax=.2, avg_shipping=.2, avg_selling_fees=.2),
        Market(name='Market Three')
    )

    session.add_all(markets)
    session.commit()
    return markets


@pytest.fixture(scope='function')
def market_listings(session, markets):
    market_listings = (
        MarketListing(vendor_id=markets[0].id, sku='M1234', quantity=1),
        MarketListing(vendor_id=markets[0].id, sku='M2345', quantity=2),
        MarketListing(vendor_id=markets[0].id, sku='M3456', quantity=3)
    )

    session.add_all(market_listings)
    session.commit()
    return market_listings


@pytest.fixture(scope='function')
def market_details(session, market_listings):
    market_details = (
        MarketListingDetails(listing_id=market_listings[0].id, price=11.11, selling_fees=5),
        MarketListingDetails(listing_id=market_listings[1].id, price=22.22, selling_fees=10),
        MarketListingDetails(listing_id=market_listings[2].id, price=33.33, selling_fees=15)
    )

    session.add_all(market_details)
    session.commit()
    return market_details


@pytest.fixture(scope='function')
def more_market_details(session, market_listings):
    more_market_details = (
        MarketListingDetails(listing_id=market_listings[0].id, price=12.12, selling_fees=6),
        MarketListingDetails(listing_id=market_listings[1].id, price=34.34, selling_fees=11),
        MarketListingDetails(listing_id=market_listings[2].id, price=45.45, selling_fees=16)
    )

    session.add_all(more_market_details)
    session.commit()
    return more_market_details


@pytest.fixture(scope='function')
def inventory_details(session, market_listings):
    inventory_details = (
        InventoryDetails(listing_id=market_listings[0].id, fulfillable=1, reserved=1),
        InventoryDetails(listing_id=market_listings[1].id, fulfillable=2, reserved=2),
        InventoryDetails(listing_id=market_listings[2].id, fulfillable=3, reserved=3)
    )

    session.add_all(inventory_details)
    session.commit()
    return inventory_details


@pytest.fixture(scope='function')
def more_inventory_details(session, market_listings):
    more_inventory_details = (
        InventoryDetails(listing_id=market_listings[0].id, fulfillable=4, reserved=4),
        InventoryDetails(listing_id=market_listings[1].id, fulfillable=5, reserved=5),
        InventoryDetails(listing_id=market_listings[2].id, fulfillable=6, reserved=6)
    )

    session.add_all(more_inventory_details)
    session.commit()
    return more_inventory_details
