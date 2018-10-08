import marshmallow as mm
import marshmallow.fields as mmf

from core import db, filter_with_json
from models import Listing, Vendor
from ext.common import launch_spider, ExtActor


########################################################################################################################


class Crawl(ExtActor):
    """Launch the vendor's spdr and crawl the given URLs."""
    public = True

    class Schema(mm.Schema):
        """Parameter schema for Crawl."""
        urls = mmf.List(mmf.URL(), required=True, title='URLs')
        options = mmf.Dict(missing=dict, title='Spider options')

    def perform(self, urls=None, options=None):
        return launch_spider('katom', urls=urls, context_id=self.context.id, spider_options=options)


########################################################################################################################


class UpdateListings(ExtActor):
    """Crawl the detail pages for the given listings."""
    public = True

    class Schema(mm.Schema):
        """Parameter schema for UpdateListings."""
        query = mmf.Dict(missing=dict, title='Listings query')

    def perform(self, query=None):
        katom = Vendor.query.filter(
            db.or_(
                Vendor.url.ilike('%katom.com%'),
                Vendor.name.ilike('katom%')
            )
        ).one()

        query.update(vendor_id=katom.id)
        listings = filter_with_json(Listing.query, query)
        urls = [listing.detail_url or f'http://www.katom.com/{listing.sku}.html' for listing in listings]

        self.context.send(
            Crawl.message(urls=urls)
        )



########################################################################################################################

