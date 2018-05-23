from urllib.parse import urlparse

from models.entities import Vendor
from models.listings import Listing, QuantityMap, Inventory
from models.orders import Order, OrderItem
from models.finances import OrderEvent, OrderItemEvent, FinancialAccount
from models.relationships import Opportunity, OpportunitySource

from .common import db, ops_actor, search


########################################################################################################################


@ops_actor
def test(message=None):
    print(f'This was a test: {message}')


@ops_actor
def import_listing_default(doc):
    """Imports a JSON map into the database as a listing."""
    # Check for required fields
    assert 'vendor_id' in doc or 'detail_url' in doc, 'vendor_id or detail_url required.'
    assert 'sku' in doc, 'sku required'

    # Do some basic cleaning
    for field, value in doc.items():
        if isinstance(value, str):
            doc[field] = value.strip()

    # Try to locate the product in the database
    sku = doc.pop('sku')
    vendor_id = doc.pop('vendor_id', None)
    if vendor_id:
        vendor = Vendor.query.filter_by(id=vendor_id).one()
    else:
        netloc = urlparse(doc['detail_url'])[1]
        vendor = Vendor.query.filter(Vendor.url.ilike(f'%{netloc}%')).one()
        vendor_id = vendor.id

    listing = Listing.query.filter_by(vendor_id=vendor_id, sku=sku).one_or_none()\
              or Listing(vendor_id=vendor_id, sku=sku)

    # Update and commit
    listing.update(doc)
    db.session.add(listing)
    db.session.commit()

    return listing.id


@ops_actor
def import_matching_listings(listing_ids):
    """Import matching listings from the vendors."""
    vendors = Vendor.query.all()
    listings = Listing.query.filter(Listing.id.in_(listing_ids)).all()

    for listing in listings:
        for vendor in vendors:
            if vendor.extension and hasattr(vendor.extension, 'import_matches'):
                vendor.extension.import_matches.send(listing.id)

    return listing_ids



# @ops_actor
# def find_opportunities(listing_ids):
#     """Find opportunities for a given listing."""
#     if listing_ids:
#         listings = Listing.query.filter(Listing.id.in_(listing_ids)).all()
#     else:
#         listings = Listing.query.all()
#
#     for listing in listings:
#         listing_type = type(listing)
#
#         # Search the database for matches
#         search_type = Listing
#         hits, total = search.find_matching_listings(listing, model_types=[search_type], per_page=100)
#         ids = [h['id'] for h in hits if h['n_score'] >= 0.35]
#         matched_listings = Listing.query.filter(Listing.id.in_(ids)).all()
#
#         # Create opportunities for each match
#         opps = []
#         for match in matched_listings:
#             if isinstance(listing, MarketListing):
#                 opp = Opportunity(listing=listing)
#                 src = OpportunitySource(listing=match)
#             elif isinstance(match, MarketListing):
#                 opp = Opportunity(listing=match)
#                 src = OpportunitySource(listing=listing)
#             else:
#                 continue
#
#             opp.sources.append(src)
#             opps.append(opp)
#
#         if opps:
#             db.session.add_all(opps)
#             db.session.commit()
#
#     return listing_ids
