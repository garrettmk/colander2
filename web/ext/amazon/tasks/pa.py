import marshmallow as mm
import marshmallow.fields as mmf

import xmallow as xm

from .common import MWSActor, MWSResponseSchema


########################################################################################################################


class ItemLookup(MWSActor):
    """Performs an ItemLookup operation. Accepts a dictionary with a 'sku' key, and updates and returns that dictionary
    with the results of the lookup."""
    api_name = 'ProductAdvertising'

    class Schema(mm.Schema):
        """Parameter schema for ItemLookup."""
        class ListingSchema(mm.Schema):
            sku = mmf.String(required=True, title='Listing SKU')

            @mm.decorators.post_load(pass_original=True)
            def include_all(self, data, original):
                for key, value in original.items():
                    if key not in data:
                        data[key] = value
                return data

        listing = mmf.Nested(ListingSchema, required=True, title='Listing document')

    class ResponseSchema(MWSResponseSchema):
        """Schema for ItemLookup responses."""

        class ProductSchema(xm.Schema):
            ignore_missing = True

            sku = xm.String('.//ASIN', required=True)
            detail_url = xm.Field('ASIN', cast=lambda tag: f'http://www.amazon.com/dp/{tag.text}')
            rank = xm.Int('SalesRank')
            category = xm.String('.//ProductGroup')
            image_url = xm.String('.//LargeImage/URL')
            brand = xm.First(('.//Brand', './/Manufacturer', './/Label', './/Publisher', './/Studio'))
            model = xm.First(('.//Model', './/MPN', './/PartNumber'))
            NumberOfItems = xm.Int('.//NumberOfItems')
            PackageQuantity = xm.Int('.//PackageQuantity')
            title = xm.String('.//Title')
            upc = xm.String('.//UPC')
            merchant = xm.String('.//Merchant/Name')
            prime = xm.Boolean('.//IsEligibleForPrime')
            features = xm.String('.//Feature', many=True)
            description = xm.String('.//EditorialReview/Content')
            price = xm.Field('.//OfferListing/Price/Amount', cast=lambda tag: int(tag.text) / 100)

            def post_load(self, data):
                if 'features' in data:
                    data.features = '\n'.join(data.features)

                return data

        products = xm.Field('//Item', ProductSchema(), many=True, default=list)

    def build_params(self, listing=None):
        return {
        'ResponseGroup': 'Images,ItemAttributes,OfferFull,SalesRank,EditorialReview',
        'ItemId': listing['sku'],
    }

    def process_response(self, args, kwargs, response):
        doc = kwargs['listing']

        if response.products:
            doc.update(response.products[0])

        if response.errors:
            doc['errors'] = doc.get('errors', []).extend(response.errors)

        self.context['listing'] = doc
        return doc
