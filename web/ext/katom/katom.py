from app import db
from models.entities import Vendor
from models.listings import Listing
from models.orders import Order, OrderItem, Shipment
from ext.core import ext_actor, ExtActor, launch_spider
from tasks.ops.listings import import_listing_default


########################################################################################################################


@ext_actor
def import_spider_item(doc):
    """Process a document from the spider."""
    if 'sku' in doc:
        return import_listing_default.send(doc)
    else:
        return doc


@ext_actor
def crawl(urls):
    """Launch a spider and crawl the given URLs."""
    return launch_spider('katom', urls)


@ext_actor
def update_listings(listing_ids):
    """Update the given listing."""
    listings = Listing.query.filter(Listing.id.in_(listing_ids)).all()
    urls = [listing.detail_url or f'http://www.katom.com/{listing.sku}.html' for listing in listings]
    crawl(urls)
