import pytest

from sqlalchemy.exc import IntegrityError

from .fixtures import *
from models.listings import Listing, quantize_decimal
from models.relationships import Relationship, RelationshipSource, Opportunity, OpportunitySource,\
    InventoryConversion, gcd, lcm


########################################################################################################################


@pytest.fixture(scope='function')
def relationships(session, listings):
    relationships = (
        Relationship(listing=listings[0]),
        Relationship(listing=listings[1]),
        Relationship(listing=listings[2])
    )

    session.add_all(relationships)
    session.commit()
    return relationships


@pytest.fixture(scope='function')
def relationship_sources(session, listings, relationships):
    relationship_sources = (
        RelationshipSource(relationship=relationships[0], listing=listings[1]),
        RelationshipSource(relationship=relationships[1], listing=listings[2]),
        RelationshipSource(relationship=relationships[2], listing=listings[0])
    )

    session.add_all(relationship_sources)
    session.commit()
    return relationship_sources


@pytest.fixture(scope='function')
def opportunities(session, listings, market_listings):
    opportunities = (
        Opportunity(listing_id=market_listings[0].id),
        Opportunity(listing_id=market_listings[1].id),
        Opportunity(listing_id=market_listings[2].id)
    )

    opportunities[0].sources.extend([
        OpportunitySource(relationship_id=opportunities[0].id, listing_id=listings[0].id)
    ])

    opportunities[1].sources.extend([
        OpportunitySource(relationship_id=opportunities[1].id, listing_id=listings[0].id),
        OpportunitySource(relationship_id=opportunities[1].id, listing_id=listings[1].id)
    ])

    # Third opp has no sources

    session.add_all(opportunities)
    session.commit()
    return opportunities


@pytest.fixture(scope='function')
def conversions(session, market_listings):
    conversions = (
        InventoryConversion(listing_id=market_listings[0].id, cost=1.0),
        InventoryConversion(listing_id=market_listings[1].id, cost=2.0),
        InventoryConversion(listing_id=market_listings[2].id, cost=3.0)
    )

    for ml, f in zip(market_listings, (10, 50, 100)):
         ml.fulfillable = f

    conversions[0].sources.extend([
        RelationshipSource(listing_id=market_listings[1].id, units=1)
    ])

    conversions[1].sources.extend([
        RelationshipSource(listing_id=market_listings[0].id, units=2),
        RelationshipSource(listing_id=market_listings[2].id, units=3)
    ])

    conversions[2].sources.extend([
        RelationshipSource(listing_id=market_listings[0].id, units=2),
        RelationshipSource(listing_id=market_listings[1].id, units=None)
    ])

    session.add_all(conversions)
    session.commit()
    return conversions


########################################################################################################################


@pytest.mark.parametrize('a,b', [
    (1, 2),
    (3, 4),
    (5, 6),
    (7, 8),
    (9, 10)
])
def test_gcd(a, b):
    g = gcd(a, b)

    for i in range(g + 1, min(a, b)):
        assert a % i or b % i


@pytest.mark.parametrize('factors', [
    (2, 3),
    (4, 6),
    (10, 25),
    (7, 8),
    (1, 2, 3),
    (4, 5, 6),
    (7, 8, 9, 10)
])
def test_lcm(factors):
    m = lcm(*factors)

    for f in factors:
        assert not m % f

    for i in range(1, m):
        assert sum(i % f for f in factors)


########################################################################################################################


def test_relationship_listing_non_null(session):
    rel = Relationship()
    session.add(rel)

    with pytest.raises(IntegrityError):
        session.commit()


def test_relationship_source_relationship_non_null(session, listings):
    l1 = listings[0]
    rs1 = RelationshipSource(listing=l1)
    session.add(rs1)

    with pytest.raises(IntegrityError):
        session.commit()


def test_relationship_source_listing_non_null(session, relationships):
    r1 = relationships[0]
    rs1 = RelationshipSource(relationship=r1)
    session.add(rs1)

    with pytest.raises(IntegrityError):
        session.commit()


def test_relationship_source_unique(session, listings, relationships):
    l1 = listings[0]
    r1 = relationships[0]

    s1, s2 = RelationshipSource(listing=l1, relationship=r1), RelationshipSource(listing=l1, relationship=r1)
    session.add_all((s1, s2))

    with pytest.raises(IntegrityError):
        session.commit()


def test_relationship_source_defaults(session, relationship_sources):
    sources = session.query(RelationshipSource).all()
    for s in sources:
        assert s.units == 1


########################################################################################################################


def test_opportunity_cost_attribute(session, opportunities, details, market_details):
    valid_cost_exists = False
    invalid_cost_exists = False

    for opp in opportunities:
        try:
            cost = sum(
                s.listing.estimated_unit_cost * s.units * opp.listing.quantity
                for s in opp.sources
            ) if opp.sources else None

            valid_cost_exists = valid_cost_exists or cost is not None
        except TypeError:
            cost = None

        invalid_cost_exists = invalid_cost_exists or cost is None

        assert opp.cost == cost

    assert valid_cost_exists
    assert invalid_cost_exists


def test_opportunity_cost_expression(session, opportunities, more_details):
    valid_cost_exists = False
    invalid_cost_exists = False

    for opp in opportunities:
        try:
            cost = sum(
                s.listing.estimated_unit_cost * s.units * opp.listing.quantity
                for s in opp.sources
            ) if opp.sources else None

            valid_cost_exists = valid_cost_exists or cost is not None
        except TypeError:
            cost = None

        invalid_cost_exists = invalid_cost_exists or cost is None

        assert session.query(Opportunity.id, Opportunity.cost).filter_by(id=opp.id).first()[1] == cost

    assert valid_cost_exists
    assert invalid_cost_exists


def test_opportunity_profit_attribute(session, opportunities, details,  market_details):
    valid_profit_exists = False
    invalid_profit_exists = False

    for opp in opportunities:
        price = opp.listing.price
        fees = opp.listing.selling_fees
        cost = opp.cost

        try:
            profit = price - fees - cost
            valid_profit_exists = True
        except TypeError:
            profit = None
            invalid_profit_exists = True

        assert opp.profit == profit

    assert valid_profit_exists
    assert invalid_profit_exists


def test_opportunity_profit_expression(session, opportunities, details, market_details):
    valid_profit_exists = False
    invalid_profit_exists = False

    for opp in opportunities:
        price = opp.listing.price
        fees = opp.listing.selling_fees
        cost = opp.cost

        try:
            profit = price - fees - cost
            valid_profit_exists = True
        except TypeError:
            profit = None
            invalid_profit_exists = True

        assert session.query(
            Opportunity.id,
            Opportunity.profit
        ).filter(
            Opportunity.id == opp.id
        ).first()[1] == profit

    assert valid_profit_exists
    assert invalid_profit_exists


def test_opportunity_roi_attribute(session, opportunities, details, market_details):
    valid_roi_exists = False
    invalid_roi_exists = False

    for opp in opportunities:
        profit = opp.profit
        cost = opp.cost
        try:
            roi = float(profit / cost)
            valid_roi_exists = True
        except TypeError:
            roi = None
            invalid_roi_exists = True

        if None in (opp.roi, roi):
            assert opp.roi == roi
        else:
            assert round(opp.roi, 6) == round(roi, 6)

    assert valid_roi_exists
    assert invalid_roi_exists


def test_opportunity_roi_expression(session, opportunities, details, market_details):
    valid_roi_exists = False
    invalid_roi_exists = False

    for opp in opportunities:
        profit = opp.profit
        cost = opp.cost
        try:
            roi = float(profit / cost)
            valid_roi_exists = True
        except TypeError:
            roi = None
            invalid_roi_exists = True

        sql_roi = session.query(
            Opportunity.id,
            Opportunity.roi
        ).filter(
            Opportunity.id == opp.id
        ).first()[1]

        if None in (roi, sql_roi):
            assert sql_roi == roi
        else:
            assert round(sql_roi, 6) == round(sql_roi, 6)

    assert valid_roi_exists
    assert invalid_roi_exists


########################################################################################################################


def test_inventory_conversion_units_per_dest(conversions):
    valid_units_exists = False

    for conversion in conversions:
        units_used = sum(s.units for s in conversion.sources)
        valid_units_exists = valid_units_exists or units_used > 0

        assert conversion.units_per_dest == units_used

    assert valid_units_exists


def test_inventory_conversion_min_source_units(conversions):
    for conversion in conversions:
        for units, source in zip(conversion.min_source_units, conversion.sources):
            assert units == lcm(source.listing.quantity or 1, source.units)


def test_inventory_conversion_total_units_per_batch(conversions):
    for conversion in conversions:
        assert conversion.total_units_per_batch == lcm(conversion.units_per_dest, *conversion.min_source_units)


def test_inventory_conversion_source_units_per_batch(conversions):
    for conversion in conversions:
        total_units_per_batch = conversion.total_units_per_batch
        units_per_dest = conversion.units_per_dest

        for source, units in zip(conversion.sources, conversion.source_units_per_batch):
            assert units == total_units_per_batch * source.units / units_per_dest


def test_inventory_conversion_batch_size(conversions):
    for conversion in conversions:
        units_per_dest = conversion.units_per_dest
        total_units_per_batch = conversion.total_units_per_batch

        assert conversion.batch_size == total_units_per_batch / units_per_dest


@pytest.mark.parametrize('batches', [1, 2, 3, 4])
def test_inventory_conversion_convert(batches, conversions):
    for conversion in conversions:
        # The current inventory levels
        src_inventory = tuple(s.listing.fulfillable for s in conversion.sources)
        dest_inventory = conversion.listing.fulfillable or 0

        # The amount of inventory required from each source to do the conversion
        required = tuple(units * batches for units in conversion.source_units_per_batch)

        # Whether or not sufficient inventory exists
        sufficient_inventory = tuple(s.listing.fulfillable or 0 >= req for s, req in zip(conversion.sources, required))

        if False in sufficient_inventory:
            with pytest.raises(Exception):
                conversion.convert(batches)
            continue

        conversion.convert(batches)
        exp_src_inventory = tuple(s - r for s, r in zip(src_inventory, required))
        exp_dest_inventory = dest_inventory + conversion.batch_size * batches

        for source, exp_inv in zip(conversion.sources, exp_src_inventory):
            assert source.listing.fulfillable == exp_inv

        assert conversion.listing.fulfillable == exp_dest_inventory




