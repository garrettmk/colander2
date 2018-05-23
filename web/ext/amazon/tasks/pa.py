from .common import MWSActor, xpath_get


########################################################################################################################


class ItemLookup(MWSActor):

    def api_name(self):
        return 'ProductAdvertising'

    def build_params(self, doc):
        return {
        'ResponseGroup': 'Images,ItemAttributes,OfferFull,SalesRank,EditorialReview',
        'ItemId': doc['sku'],
    }

    def parse_response(self, args, kwargs, response):
        doc = args[0] if args else kwargs.pop('doc')
        result = dict(doc)
        for item_tag in response.tree.iterdescendants('Item'):
            result['detail_url'] = f'http://www.amazon.com/dp/{result["sku"]}'
            result['rank'] = xpath_get('.//SalesRank', item_tag, _type=int)
            result['category'] = xpath_get('.//ProductGroup', item_tag)
            result['image_url'] = xpath_get('.//LargeImage/URL', item_tag)
            result['brand'] = xpath_get('.//Brand', item_tag) \
                              or xpath_get('.//Manufacturer', item_tag) \
                              or xpath_get('.//Label', item_tag) \
                              or xpath_get('.//Publisher', item_tag) \
                              or xpath_get('.//Studio', item_tag) \
                              or xpath_get('.//Model', item_tag)
            result['model'] = xpath_get('.//Model', item_tag) \
                              or xpath_get('.//MPN', item_tag) \
                              or xpath_get('.//PartNumber', item_tag)
            result['NumberOfItems'] = xpath_get('.//NumberOfItems', item_tag, _type=int)
            result['PackageQuantity'] = xpath_get('.//PackageQuantity', item_tag, _type=int)
            result['title'] = xpath_get('.//Title', item_tag)
            result['upc'] = xpath_get('.//UPC', item_tag)
            result['merchant'] = xpath_get('.//Merchant/Name', item_tag)
            result['prime'] = xpath_get('.//IsEligibleForPrime', item_tag, _type=bool)
            result['features'] = '\n'.join((t.text for t in item_tag.iterdescendants('Feature'))) or None
            result['description'] = xpath_get('.//EditorialReview/Content', item_tag)

            price = xpath_get('.//OfferListing/Price/Amount', item_tag, _type=float)
            result['price'] = price / 100 if price is not None else None

            result = {k: v for k, v in result.items() if v is not None}
            break

        return result
