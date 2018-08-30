import marshmallow as mm
import marshmallow.fields as mmf

from models import Listing
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
        listing_ids = mmf.List(mmf.Int(), required=True, title='Listing IDs')

    def perform(self, listing_ids=None):
        listings = Listing.query.filter(Listing.id.in_(listing_ids)).all()
        urls = [listing.detail_url or f'http://www.katom.com/{listing.sku}.html' for listing in listings]

        self.context.send(
            Crawl.message(urls=urls)
        )



########################################################################################################################

