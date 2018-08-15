from marshmallow import Schema, fields

from core.models import ObjectIdField
from models.listings import Listing
from ext.core import launch_spider, ext_actor, ExtActor
from tasks.ops.listings import import_listing_default


########################################################################################################################


class Crawl(ExtActor):
    """Launch the vendor's spdr and crawl the given URLs."""
    public = True

    class Schema(Schema):
        urls = fields.List(fields.URL(), required=True, title='URLs')

    def perform(self, *args, **kwargs):
        return launch_spider('katom', **kwargs)


class FormTest(ExtActor):
    """Test automatic form generation with different field types."""
    public = True

    class Schema(Schema):
        int_field = fields.Int()
        float_field = fields.Float(required=True, title='Float Field')
        str_field = fields.Str()
        list_field = fields.List(fields.Str(), title='List of strings')
        int_list = fields.List(fields.Int(), title='List of integers')
        listing_field = ObjectIdField(class_='listing')

    def perform(self, *args, **kwargs):
        print(args, kwargs)


@ext_actor
def import_spider_item(doc):
    """Process a document from the spider."""
    if 'sku' in doc:
        return import_listing_default.send(doc)
    else:
        return doc


@ext_actor
def update_listings(listing_ids):
    """Update the given listing."""
    listings = Listing.query.filter(Listing.id.in_(listing_ids)).all()
    urls = [listing.detail_url or f'http://www.katom.com/{listing.sku}.html' for listing in listings]
    Crawl(urls)
