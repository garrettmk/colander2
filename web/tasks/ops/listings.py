from urllib.parse import urlparse

import marshmallow as mm
import marshmallow.fields as mmf

from core import filter_with_json
from models import Listing, Vendor

from .common import db, OpsActor, search


########################################################################################################################


class ImportListing(OpsActor):
    """Import a JSON document into the database as a listing."""
    public = True

    class Schema(mm.Schema):
        """Parameter schema for ImportListing."""
        class ListingSchema(mm.Schema):
            sku = mmf.String(required=True, title='Listing SKU')
            vendor_id = mmf.Int(title='Vendor ID')
            detail_url = mmf.Url(title='Detail page URL')

            @mm.decorators.post_load(pass_original=True)
            def include_all(self, data, original):
                for key, value in original.items():
                    if key not in data:
                        data[key] = value
                return data

            @mm.decorators.validates_schema()
            def validate(self, data):
                if 'vendor_id' not in data and 'detail_url' not in data:
                    raise mm.exceptions.ValidationError('Missing required field: vendor_id or detail_url')

        listing = mmf.Nested(ListingSchema, required=True, title='Listing document')

    def perform(self, listing=None):
        # Do some basic cleaning
        for field, value in listing.items():
            if isinstance(value, str):
                listing[field] = value.strip()

        # Try to locate the listing in the database
        sku = listing.pop('sku')
        vendor_id = listing.pop('vendor_id', None)

        if vendor_id is None:
            netloc = urlparse(listing['detail_url'])[1]
            vendor = Vendor.query.filter(Vendor.url.ilike(f'%{netloc}%')).one()
            vendor_id = vendor.id

        model = Listing.query.filter_by(vendor_id=vendor_id, sku=sku).one_or_none()\
                    or Listing(vendor_id=vendor_id, sku=sku)

        # Update and commit
        model.update(listing)
        db.session.add(model)
        db.session.commit()

        return model.id


########################################################################################################################


class ImportMatchingListings(OpsActor):
    """Import matching listings from all the vendors."""
    public = True

    class Schema(mm.Schema):
        query = mmf.Dict(missing=dict, title='Listings query')

    def perform(self, query=None):
        for vendor in Vendor.query.all():
            try:
                message = vendor.extension.message('ImportMatchingListings')
            except (ValueError, AttributeError):
                continue

            self.context.bind(message)


########################################################################################################################


class UpdateListings(OpsActor):
    """Update all listings in the given query, if their vendor extension provides an UpdateListings action."""
    public = True

    class Schema(mm.Schema):
        """Parameter schema from UpdateListings."""
        query = mmf.Dict(missing=dict, title='Listing query')

    def perform(self, query=None):
        """Delegate the update operation to the vendor extensions."""
        vendors = filter_with_json(Vendor.query, {'listings': query})

        for vendor in vendors:
            try:
                message = vendor.extension.message('UpdateListings')
            except (ValueError, AttributeError):
                continue

            self.context.bind(message)


########################################################################################################################


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
