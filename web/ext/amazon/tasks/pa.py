import xmallow as xm

from .common import MWSActor, MWSResponseSchema


########################################################################################################################


class ItemLookup(MWSActor):
    """Performs an ItemLookup operation. Accepts a dictionary with a 'sku' key, and updates and returns that dictionary
    with the results of the lookup."""

    class Schema(MWSResponseSchema):
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

    def api_name(self):
        return 'ProductAdvertising'

    def build_params(self, doc):
        return {
        'ResponseGroup': 'Images,ItemAttributes,OfferFull,SalesRank,EditorialReview',
        'ItemId': doc['sku'],
    }

    def process_response(self, args, kwargs, response):
        from pprint import pprint
        pprint(response)
        doc = args[0] if args else kwargs.pop('doc')

        if response.products:
            doc.update(response.products[0])

        if response.errors:
            doc['errors'] = doc.get('errors', []).extend(response.errors)

        return doc
