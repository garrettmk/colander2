import re
import amazonmws as mws
from lxml import etree
from datetime import datetime, timedelta
from .common import ISO_8601, MWSActor, xpath_get


########################################################################################################################


class GetServiceStatus(MWSActor):

    def api_name(self):
        return 'Products'

    def build_params(self):
        return {}

    def parse_response(self, args, kwargs, response):
        return response.xpath_get('.//Status')


########################################################################################################################


class ListMatchingProducts(MWSActor):

    def api_name(self):
        return 'Products'

    def build_params(self, query, market_id='US'):
        return {
            'Query': query,
            'MarketplaceId': market_id if len(market_id) > 2 else mws.MARKETID[market_id]
        }

    def parse_response(self, args, kwargs, response):
        results = []
        for tag in response.tree.iterdescendants('Product'):
            product = dict()
            product['sku'] = xpath_get('./Identifiers/MarketplaceASIN/ASIN', tag)
            product['brand'] = xpath_get('.//Brand', tag) \
                               or xpath_get('.//Manufacturer', tag) \
                               or xpath_get('.//Label', tag) \
                               or xpath_get('.//Publisher', tag) \
                               or xpath_get('.//Studio', tag)
            product['model'] = xpath_get('.//Model', tag) \
                               or xpath_get('.//PartNumber', tag)
            product['price'] = xpath_get('.//ListPrice/Amount', tag, _type=float)
            product['NumberOfItems'] = xpath_get('.//NumberOfItems', tag, _type=int)
            product['PackageQuantity'] = xpath_get('.//PackageQuantity', tag, _type=int)
            product['image_url'] = xpath_get('.//SmallImage/URL', tag)
            product['title'] = xpath_get('.//Title', tag)

            for rank_tag in tag.iterdescendants('SalesRank'):
                if not rank_tag.xpath('./ProductCategoryId')[0].text.isdigit():
                    product['category'] = xpath_get('./ProductCategoryId', rank_tag)
                    product['rank'] = xpath_get('./Rank', rank_tag, _type=int)
                    break

            product['description'] = '\n'.join([t.text for t in tag.iterdescendants('Feature')]) or None

            results.append({k: v for k, v in product.items() if v is not None})

        return results


########################################################################################################################


class GetMyFeesEstimate(MWSActor):

    def api_name(self):
        return 'Products'

    def build_params(self, doc, market_id='US'):
        try:
            price = str(doc['price'])
        except (KeyError, ValueError, TypeError):
            price = '0'

        # Allow two-letter marketplace abbreviations
        return mws.structured_list(
            'FeesEstimateRequestList', 'FeesEstimateRequest',
            [
                {
                    'MarketplaceId': market_id if len(market_id) > 2 else mws.MARKETID[market_id],
                    'IdType': 'ASIN',
                    'IdValue': doc['sku'],
                    'IsAmazonFulfilled': 'true',
                    'Identifier': 'request1',
                    'PriceToEstimateFees.ListingPrice.CurrencyCode': 'USD',
                    'PriceToEstimateFees.ListingPrice.Amount': price
                }
            ]
        )

    def parse_response(self, args, kwargs, response):
        doc = args[0] if args else kwargs['doc']
        try:
            price = str(doc['price'])
        except (KeyError, ValueError, TypeError):
            return doc

        tag = response.tree.xpath('//FeesEstimateResult')[0]
        if xpath_get('.//Status', tag) == 'Success':
            doc['selling_fees'] = xpath_get('.//TotalFeesEstimate/Amount', tag, _type=float)

        return doc


########################################################################################################################


class GetCompetitivePricingForASIN(MWSActor):

    def api_name(self):
        return 'Products'

    def build_params(self, doc, market_id='US'):
        return {
            'MarketplaceId': market_id if len(market_id) > 2 else mws.MARKETID[market_id],
            **mws.structured_list('ASINList', 'ASIN', [doc['sku']]),
        }

    def parse_response(self, args, kwargs, response):
        doc = args[0] if args else kwargs['doc']
        tag = response.tree.xpath('//GetCompetitivePricingForASINResult')[0]
        if tag.attrib.get('status') == 'Success':
            for price_tag in tag.iterdescendants('CompetitivePrice'):
                if price_tag.attrib.get('condition') != 'New':
                    continue

                listing_price = xpath_get('.//ListingPrice/Amount', price_tag, _type=float)
                shipping = xpath_get('.//Shipping/Amount', price_tag, _type=float)
                landed_price = xpath_get('.//LandedPrice/Amount', price_tag, _type=float)

                doc['price'] = landed_price or (listing_price + shipping)
                break

            for count_tag in tag.iterdescendants('OfferListingCount'):
                if count_tag.attrib.get('condition') == 'New':
                    doc['offers'] = int(count_tag.text)
                    break
            else:
                doc['offers'] = 0

        return doc


########################################################################################################################


class ListInventorySupply(MWSActor):

    def api_name(self):
        return 'FulfillmentInventory'

    def build_params(self, *, seller_skus=None, start=None, market_id='US'):
        if seller_skus is None and start is None:
            start = datetime.utcnow() - timedelta(days=90)
            start = start.strftime(ISO_8601)

        if seller_skus and start:
            raise ValueError('Can only accept seller_skus or start, not both.')
        elif seller_skus:
            params = mws.structured_list('SellerSkus', 'member', seller_skus)
        elif start:
            params = {'QueryStartDateTime': start}
        else:
            raise ValueError('seller_skus or start is required.')

        params.update(MarketplaceId=market_id if len(market_id) > 2 else mws.MARKETID[market_id])

        return params

    def parse_response(self, args, kwargs, response):
        results = []
        while response:
            for tag in response.tree.iterdescendants('member'):
                listing = dict()
                listing['sku'] = xpath_get('.//ASIN', tag)
                listing['fnsku'] = xpath_get('.//FNSKU', tag)
                listing['msku'] = xpath_get('.//SellerSKU', tag)
                listing['fulfillable'] = xpath_get('.//InStockSupplyQuantity', tag, _type=int)
                listing['condition'] = xpath_get('.//Condition', tag)
                results.append({k: v for k, v in listing.items() if v is not None})

            next_token = response.xpath_get('.//NextToken')
            response = self.make_api_call(
                'ListInventorySupplyByNextToken',
                throttle_action='ListInventorySupply',
                NextToken=next_token
            ) if next_token else None

        return results


########################################################################################################################


class ListInboundShipments(MWSActor):

    def api_name(self):
        return 'FulfillmentInboundShipment'

    def build_params(self, *, status=None, shipment_id=None, updated_after=None, updated_before=None):
        if updated_after is None and updated_before is None:
            updated_after = (datetime.utcnow() - timedelta(days=90)).strftime(ISO_8601)
            updated_before = datetime.utcnow().strftime(ISO_8601)

        status = [status] if isinstance(status, str) else status
        if status is None:
            status = ('WORKING', 'SHIPPED', 'IN_TRANSIT', 'DELIVERED', 'CHECKED_IN', 'RECEIVING', 'CLOSED', 'CANCELLED')
        status_list = mws.structured_list('ShipmentStatusList', 'member', status) if status else {}

        shipment_id = [shipment_id] if isinstance(shipment_id, str) else shipment_id
        shipment_id_list = mws.structured_list('ShipmentIdList', 'member', shipment_id) if shipment_id else {}

        return {k: v for k, v in {
            'LastUpdatedAfter': updated_after,
            'LastUpdatedBefore': updated_before,
            **status_list,
            **shipment_id_list
        }.items() if v is not None}

    def parse_response(self, args, kwargs, response):
        results = []
        while response:
            for tag in response.tree.iterdescendants('member'):
                order = dict()
                order['order_number'] = xpath_get('.//ShipmentId', tag)
                order['name'] = xpath_get('.//ShipmentName', tag)
                #order['from_address'] = response.xpath_get('.//ShipFromAddress', tag)
                order['fulfillment_center_id'] = xpath_get('.//DestinationFulfillmentCenterId', tag)
                order['label_prep_type'] = xpath_get('.//LabelPrepType', tag)
                order['status'] = xpath_get('.//ShipmentStatus', tag)
                order['cases_required'] = xpath_get('.//AreCasesRequired', tag, _type=bool)
                order['need_by_date'] = xpath_get('.//ConfirmedNeedByDate', tag)
                order['box_contents_source'] = xpath_get('.//BoxContentsSource', tag)
                order['box_contents_fee'] = {
                    'units': xpath_get('.//EstimatedBoxContentsFee/TotalUnits', tag, _type=int),
                    'per_unit': xpath_get('.//EstimatedBoxContentsFee/FeePerUnit/Amount', tag, _type=float),
                    'total': xpath_get('.//EstimatedBoxContentsFee/TotalFee/Amount', tag, _type=float)
                }
                results.append({k: v for k, v in order.items() if v is not None})

            next_token = response.xpath_get('.//NextToken')
            response = self.make_api_call(
                'ListInboundShipmentsByNextToken',
                throttle_action='ListInboundShipments',
                NextToken=next_token
            ) if next_token else None

        return results


########################################################################################################################


class ListInboundShipmentItems(MWSActor):

    def api_name(self):
        return 'FulfillmentInboundShipment'

    def build_params(self, *args, **kwargs):
        doc = args[0] if args else kwargs['doc']
        return {'ShipmentId': doc['order_number']}

    def parse_response(self, args, kwargs, response):
        results = []
        while response:
            for tag in response.tree.iterdescendants('member'):
                item = dict()
                item['order_number'] = xpath_get('.//ShipmentId', tag)
                item['msku'] = xpath_get('.//SellerSKU', tag)
                item['fnsku'] = xpath_get('.//FulfillmentNetworkSKU', tag)
                item['quantity'] = xpath_get('.//QuantityShipped', tag, _type=int)
                item['received'] = xpath_get('.//QuantityReceived', tag, _type=int)
                item['case_quantity'] = xpath_get('.//QuantityInCase', tag, _type=int)
                item['prep_details'] = [
                    {
                        'instruction': xpath_get('.//PrepInstruction', pdt_tag),
                        'owner': xpath_get('.//PrepOwner', pdt_tag)
                    }
                    for pdt_tag in tag.iterdescendants('PredDetails')
                ]
                results.append({k: v for k, v in item.items() if v is not None})

            next_token = response.xpath_get('.//NextToken')
            response = self.make_api_call(
                'ListInboundShipmentItemsByNextToken',
                throttle_action='ListInboundShipmentItems',
                NextToken=next_token
            ) if next_token else None

        return results


########################################################################################################################


class GetTransportContent(MWSActor):

    def api_name(self):
        return 'FulfillmentInboundShipment'

    def build_params(self, *args, **kwargs):
        doc = args[0] if args else kwargs.pop('doc')
        return {'ShipmentId': doc['order_number']}

    def parse_response(self, args, kwargs, response):
        order_doc = {
            'shipping': response.xpath_get('.//PartneredEstimate/Amount/Value', _type=float),
            'transport_status': response.xpath_get('.//TransportStatus')
        }
        results = []
        for tag in response.tree.iterdescendants('member'):
            shipment = {
                'weight': xpath_get('.//Weight/Value', tag, _type=float),
                'tracking_number': xpath_get('.//TrackingId', tag),
                'carrier': xpath_get('.//CarrierName', tag),
                'dimensions': {
                    'units': xpath_get('.//Dimensions/Unit', tag),
                    'height': xpath_get('.//Dimensions/Height', tag, _type=float),
                    'width': xpath_get('.//Dimensions/Width', tag, _type=float),
                    'length': xpath_get('.//Dimensions/Length', tag, _type=float)
                },
                'status': xpath_get('.//PackageStatus', tag)
            }

            results.append({k: v for k, v in shipment.items() if v is not None})

        return order_doc, results


########################################################################################################################


class ListOrders(MWSActor):

    def api_name(self):
        return 'Orders'

    def build_params(self, *, created_after=None, created_before=None, updated_after=None, updated_before=None,
                     order_status=None, market_id=('US',), **kwargs):
        if created_after is None and created_before is None and updated_after is None and updated_before is None:
            created_after = (datetime.utcnow() - timedelta(days=90)).strftime(ISO_8601)

        order_status = mws.structured_list('OrderStatus', 'Status', order_status) if order_status else {}
        market_id = mws.structured_list('MarketplaceId', 'Id',
                                        [mid if len(mid) > 2 else mws.MARKETID[mid] for mid in market_id])

        params = {k: v for k, v in {
            'CreatedAfter': created_after,
            'CreatedBefore': created_before,
            'LastUpdatedAfter': updated_after,
            'LastUpdatedBefore': updated_before,
            **market_id,
            **order_status,
            **kwargs
        }.items() if v is not None}

        return params

    def parse_response(self, args, kwargs, response):
        results = []
        while response:
            for tag in response.tree.iterdescendants('Order'):
                order = {k: v for k, v in {
                    'order_number': xpath_get('.//AmazonOrderId', tag),
                    'seller_order_id': xpath_get('.//SellerOrderId', tag),
                    'date': xpath_get('.//PurchaseDate', tag),
                    'status': xpath_get('.//OrderStatus', tag),
                    'prime': xpath_get('.//IsPrime', tag, _type=bool),
                    'fulfillment_channel': xpath_get('.//FulfillmentChannel', tag),
                    'business': xpath_get('.//IsBusinessOrder', tag, _type=bool),
                    'replacement': xpath_get('.//IsReplacementOrder', tag, _type=bool),
                }.items() if v is not None}

                customer = {k: v for k, v in {
                    'email': xpath_get('.//BuyerEmail', tag),
                    'name': xpath_get('.//BuyerName', tag),
                    'address': {
                        'city': xpath_get('.//ShippingAddress/City', tag),
                        'postal_code': xpath_get('.//ShippingAddress/PostalCode', tag),
                        'state': xpath_get('.//ShippingAddress/StateOrRegion', tag),
                        'country': xpath_get('.//CountryCode', tag),
                        'lines': [line for line in [
                            xpath_get(f'.//ShippingAddress/AddressLine{i}', tag) for i in (1, 2, 3)
                        ] if line is not None],
                    }
                }.items() if v is not None}

                results.append((customer, order))

            token = response.xpath_get('.//NextToken')
            response = self.make_api_call(
                'ListOrdersByNextToken',
                throttle_action='ListOrders',
                NextToken=token
            ) if token else None

        return results


########################################################################################################################


class GetOrder(MWSActor):

    def api_name(self):
        return 'Orders'

    def build_params(self, amz_order_ids):
        return {
            **mws.structured_list('AmazonOrderId', 'Id', amz_order_ids)
        }

    def parse_response(self, args, kwargs, response):
        from pprint import pprint
        pprint(response.xml)


########################################################################################################################


class ListOrderItems(MWSActor):

    def api_name(self):
        return 'Orders'

    def build_params(self, order_number):
        return {'AmazonOrderId': order_number}

    def parse_response(self, args, kwargs, response):
        results = []
        while response:
            for tag in response.tree.iterdescendants('OrderItem'):
                item = {k: v for k, v in {
                    'sku': xpath_get('.//ASIN', tag),
                    'msku': xpath_get('.//SellerSKU', tag),
                    'order_item_id': xpath_get('.//OrderItemId', tag),
                    'title': xpath_get('.//Title', tag),
                    'qty_ordered': xpath_get('.//QuantityOrdered', tag, _type=int),
                    'qty_shipped': xpath_get('.//QuantityShipped', tag, _type=int),
                    'price': xpath_get('.//ItemPrice/Amount', tag, _type=float),
                    'currency_code': xpath_get('.//ItemPrice/CurrencyCode', tag),
                    'shipping_price': xpath_get('.//ShippingPrice/Amount', tag, _type=float),
                }.items() if v is not None}
                results.append(item)

            token = response.xpath_get('.//NextToken')
            response = self.make_api_call(
                'ListOrderItemsByNextToken',
                throttle_action='ListOrderItems',
                NextToken=token
            ) if token else None

        return results


########################################################################################################################


class ListFinancialEventGroups(MWSActor):

    def api_name(self):
        return 'Finances'

    def build_params(self, *, started_after=None, started_before=None):
        if started_after is None and started_before is None:
            started_after = (datetime.utcnow() - timedelta(days=90)).strftime(ISO_8601)

        return {k: v for k, v in {
            'FinancialEventGroupStartedAfter': started_after,
            'FinancialEventgroupStartedBefore': started_before
        }.items() if v is not None}

    def parse_response(self, args, kwargs, response):
        results = []
        while response:
            for tag in response.tree.iterdescendants('FinancialEventGroup'):
                item = {k: v for k, v in {
                    'group_id': xpath_get('.//FinancialEventGroupId', tag),
                    'group_status': xpath_get('.//ProcessingStatus', tag),
                    'fund_transfer_status': xpath_get('.//FundTransferStatus', tag),
                    'original_total': xpath_get('.//OriginalTotal/Amount', tag, _type=float),
                    'converted_total': xpath_get('.//ConvertedTotal/Amount', tag, _type=float),
                    'fund_transfer_date': xpath_get('.//FundTransferDate', tag),
                    'trace_id': xpath_get('.//TraceId', tag),
                    'account_tail': xpath_get('.//AccountTail', tag),
                    'beginning_balance': xpath_get('.//BeginningBalance/Amount', tag, _type=float),
                    'start_date': xpath_get('.//FinancialEventGroupStart', tag),
                    'end_date': xpath_get('.//FinancialEventGroupEnd', tag)
                }.items() if v is not None}
                results.append(item)

            token = response.xpath_get('.//NextToken')
            response = self.make_api_call(
                'ListFinancialEventGroupsByNextToken',
                throttle_action='ListFinancialEventGroups',
                NextToken=token
            ) if token else None

        return results


########################################################################################################################


class ListFinancialEvents(MWSActor):

    def api_name(self):
        return 'Finances'

    def build_params(self, *args, order_number=None, group_id=None, posted_after=None, posted_before=None):
        return {k: v for k, v in {
            'AmazonOrderId': order_number,
            'FinancialEventGroupId': group_id,
            'PostedAfter': posted_after,
            'PostedBefore': posted_before
        }.items() if v is not None}

    def parse_response(self, args, kwargs, response):
        # The following function converts from AmazonCase to python_case
        first_cap_re = re.compile('(.)([A-Z][a-z]+)')
        all_cap_re = re.compile('([a-z0-9])([A-Z])')

        # Convert CapitalCase to snake_case
        def convert(name):
            s1 = first_cap_re.sub(r'\1_\2', name)
            return all_cap_re.sub(r'\1_\2', s1).lower()

        # The following functions process basic list types, like FeeComponentList or TaxesWithheldList,
        # into JSON
        def process_charge_component_list(list_tag):
            return {
                xpath_get('.//ChargeType', tag): xpath_get('.//CurrencyAmount', tag, _type=float)
                for tag in list_tag
            }

        def process_fee_component_list(list_tag):
            return {
                xpath_get('.//FeeType', tag): xpath_get('.//CurrencyAmount', tag, _type=float)
                for tag in list_tag
            }

        def process_direct_payment_list(list_tag):
            return {
                xpath_get('.//DirectPaymentType', tag): xpath_get('.//Amount', tag, _type=float)
                for tag in list_tag
            }

        def process_tax_withheld_list(list_tag):
            return process_charge_component_list(list_tag.xpath('.//TaxesWithheld'))

        def process_promotion_list(list_tag):
            return [{
                'promo_type': xpath_get('.//PromotionType', tag),
                'promo_id': xpath_get('.//PromotionId', tag),
                'amount': xpath_get('.//PromotionAmount/CurrencyAmount', tag, _type=float, default=0)
            } for tag in list_tag]

        # Start processing events
        results = {}
        for list_tag in response.tree.xpath('.//FinancialEvents/*'):
            events = []
            for event_tag in list_tag.getchildren():
                event = {}
                for event_item_tag in event_tag.getchildren():
                    name = event_item_tag.tag
                    converted_name = convert(name)

                    # Process a list of ShipmentItems
                    if name in ('ShipmentItemList', 'ShipmentItemAdjustmentList', 'RefundEventList',
                                'GuaranteeClaimEventList', 'ChargebackEventList'):
                        items = []

                        for shp_item in event_item_tag.iterdescendants('ShipmentItem'):
                            charges_list = shp_item.xpath('.//ItemChargeList')
                            taxes_list = shp_item.xpath('.//ItemTaxWithheldList')
                            charge_adj_list = shp_item.xpath('.//ItemChargeAdjustmentList')
                            fee_list = shp_item.xpath('.//ItemFeeList')
                            fee_adj_list = shp_item.xpath('.//ItemFeeAdjustmentList')
                            promo_list = shp_item.xpath('.//PromotionList')
                            promo_adj_list = shp_item.xpath('.//PromotionAdjustmentList')

                            items.append({k: v for k, v in {
                                'msku': xpath_get('.//SellerSKU', shp_item),
                                'order_item_id': xpath_get('.//OrderItemId', shp_item),
                                'adjustment_id': xpath_get('.//OrderAdjustmentItemId', shp_item),
                                'quantity_shipped': xpath_get('.//QuantityShipped', shp_item, _type=int),
                                'charges': process_charge_component_list(charges_list[0]) if charges_list else [],
                                'taxes': process_tax_withheld_list(taxes_list[0]) if taxes_list else [],
                                'charge_adjustments': process_charge_component_list(charge_adj_list[0]) if charge_adj_list else [],
                                'fees': process_fee_component_list(fee_list[0]) if fee_list else [],
                                'fee_adjustments': process_fee_component_list(fee_adj_list[0]) if fee_adj_list else [],
                                'promotions': process_promotion_list(promo_list[0]) if promo_list else [],
                                'promotion_adjustments': process_promotion_list(promo_adj_list[0]) if promo_adj_list else [],
                            }.items() if v not in (None, [], {})})

                        event[converted_name] = items

                    # Process a FeeList
                    elif name == 'FeeList':
                        event[converted_name] = process_fee_component_list(event_item_tag)

                    # Process a list of AdjustmentItems
                    elif name == 'AdjustmentItemList':
                        items = []

                        for adj_item in event_item_tag.iterdescendants('AdjustmentItem'):
                            items.append({
                                'per_unit': xpath_get('.//PerUnitAmount/CurrencyAmount', adj_item, _type=float),
                                'quantity': xpath_get('.//Quantity', adj_item, _type=float),
                                'total': xpath_get('.//TotalAmount/CurrencyAmount', adj_item, _type=float),
                                'msku': xpath_get('.//SellerSKU', adj_item),
                                'product_description': xpath_get('.//ProductDescription', adj_item)
                            })

                        event[converted_name] = items

                    # Process a CurrencyAmount
                    elif name.endswith('Amount'):
                        event[converted_name] = xpath_get('.//CurrencyAmount', event_item_tag, _type=float)

                    # Some types we know to save as strings
                    elif any(term in name for term in ('Id', 'Name', 'Date', 'SKU', 'ASIN', 'Reason', 'Description',
                                                       'Type', 'Code')):
                        event[converted_name] = event_item_tag.text

                    # Try to cast the value to the appropriate type
                    else:
                        value = event_item_tag.text
                        try:
                            value = int(value)
                        except:
                            try:
                                value = float(value)
                            except:
                                if value.lower() in ('yes', 'true'):
                                    value = True
                                elif value.lower() in ('no', 'false'):
                                    value = False
                                else:
                                    # If all else fails, store the XML
                                    value = etree.tostring(event_item_tag).decode()

                        event[converted_name] = value

                events.append(event)

            results[convert(list_tag.tag)] = events

        return results
