import re
import collections
import amazonmws as mws
import xmallow as xm
from lxml import etree
from datetime import datetime, timedelta
from .common import ISO_8601, MWSActor, MWSResponseSchema, RawXMLSchema


########################################################################################################################


class GetServiceStatus(MWSActor):

    class Schema(MWSResponseSchema):
        status = xm.String('.//Status')

    def api_name(self):
        return 'Products'


########################################################################################################################


class ListMatchingProducts(MWSActor):

    class Schema(MWSResponseSchema):

        class ProductSchema(xm.Schema):
            ignore_missing = True

            class RankSchema(xm.Schema):
                category = xm.String('./ProductCategoryId')
                rank = xm.Int('./Rank')

            sku = xm.String('./Identifiers/MarketplaceASIN/ASIN')
            brand = xm.First(('.//Brand', './/Manufacturer', './/Label', './/Publisher', './/Studio'))
            model = xm.First(('.//Model', './/PartNumber'))
            price = xm.Float('.//ListPrice/Amount')
            NumberOfItems = xm.Int('.//NumberOfItems')
            PackageQuantity = xm.Int('.//PackageQuantity')
            image_url = xm.String('.//SmallImage/URL')
            title = xm.String('.//Title')
            ranks = xm.Nested('.//SalesRank', RankSchema(), many=True)
            features = xm.String('.//Feature', many=True)

            def post_load(self, data):
                if 'features' in data:
                    data.features = '\n'.join(data.pop('features'))

                for ranking in data.pop('ranks', []):
                    if not ranking['category'].isdigit():
                        data['category'] = ranking.category
                        data['rank'] = ranking.rank
                        break

                return data

        products = xm.List('//Product', ProductSchema(), default=list)

    def api_name(self):
        return 'Products'

    def build_params(self, query, market_id='US'):
        return {
            'Query': query,
            'MarketplaceId': market_id if len(market_id) > 2 else mws.MARKETID[market_id]
        }

    def process_response(self, args, kwargs, response):
        return response.products


########################################################################################################################


class GetMyFeesEstimate(MWSActor):

    class Schema(MWSResponseSchema):
        status = xm.String('.//Status')
        selling_fees = xm.Float('.//TotalFeesEstimate/Amount', default=None)

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

    def process_response(self, args, kwargs, response):
        doc = args[0] if args else kwargs['doc']

        if response.pop('status') == 'Success':
            doc['selling_fees'] = response.selling_fees

        return doc


########################################################################################################################


class GetCompetitivePricingForASIN(MWSActor):

    class Schema(MWSResponseSchema):
        success = xm.Attribute('//GetCompetitivePricingForASINResult', attr='status')
        listing_price = xm.Float('.//ListingPrice/Amount', default=0)
        shipping = xm.Float('.//Shipping/Amount', default=0)
        landed_price = xm.Float('.//LandedPrice/Amount', default=0)
        offers = xm.Int('.//OfferListingCount[@condition="New"]', default=0)

        def post_load(self, data):
            data.success = data.success == 'Success'
            return data

    def api_name(self):
        return 'Products'

    def build_params(self, doc, market_id='US'):
        return {
            'MarketplaceId': market_id if len(market_id) > 2 else mws.MARKETID[market_id],
            **mws.structured_list('ASINList', 'ASIN', [doc['sku']]),
        }

    def process_response(self, args, kwargs, response):
        doc = args[0] if args else kwargs['doc']

        if response.success:
            price = response.landed_price or (response.listing_price + response.shipping)

            if price:
                doc['price'] = price

            doc['offers'] = response.offers

        return doc


########################################################################################################################


class ListInventorySupply(MWSActor):

    class Schema(MWSResponseSchema):

        class SupplySchema(xm.Schema):
            ignore_missing = True

            sku = xm.String('.//ASIN')
            fnsku = xm.String('.//FNSKU')
            msku = xm.String('.//SellerSKU')
            fulfillable = xm.Int('.//InStockSupplyQuantity')
            condition = xm.String('.//Condition')

        items = xm.Field('.//member', SupplySchema(), many=True, default=list)
        next_token = xm.String('.//NextToken', default=None)

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

    def process_response(self, args, kwargs, response):
        results = []
        while response:
            results.extend(response['items'])

            response = self.make_api_call(
                'ListInventorySupplyByNextToken',
                throttle_action='ListInventorySupply',
                NextToken=response.next_token
            ) if response.next_token else None

        return results


########################################################################################################################


class ListInboundShipments(MWSActor):

    class Schema(MWSResponseSchema):

        class ShipmentSchema(xm.Schema):
            ignore_missing = True

            class ContentsFeeSchema(xm.Schema):
                units = xm.Int('.//TotalUnits')
                per_unit = xm.Float('.//FeePerUnit/Amount')
                total = xm.Float('.//TotalFee/Amount')

            order_number = xm.String('.//ShipmentId', required=True)
            name = xm.String('.//ShipmentName')
            fulfillment_cented_id = xm.String('.//DestinationFulfillmentCenterId')
            label_prep_type = xm.String('.//LabelPrepType')
            status = xm.String('.//ShipmentStatus')
            cases_required = xm.Boolean('.//AreCasesRequired')
            need_by_date = xm.String('.//ConfirmedNeedByDate')
            box_contents_source = xm.String('.//BoxContentsSource')
            box_contents_fee = xm.Field('.//EstimatedBoxContentsFee', ContentsFeeSchema())

        items = xm.Field('.//member', ShipmentSchema(), many=True, default=list)
        next_token = xm.String('.//NextToken', default=None)

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

    def process_response(self, args, kwargs, response):
        results = []
        while response:
            results.extend(response['items'])

            next_token = response.next_token
            response = self.make_api_call(
                'ListInboundShipmentsByNextToken',
                throttle_action='ListInboundShipments',
                NextToken=next_token
            ) if next_token else None

        return results


########################################################################################################################


class ListInboundShipmentItems(MWSActor):

    class Schema(MWSResponseSchema):

        class ShipmentSchema(xm.Schema):

            class PrepDetailsSchema(xm.Schema):
                instruction = xm.String('.//PrepInstruction')
                owner = xm.String('.//PrepOwner')

            order_number = xm.String('.//ShipmentId', required=True)
            msku = xm.String('.//SellerSKU')
            fnsku = xm.String('.//FulfillmentNetworkSKU')
            quantity = xm.Int('.//QuantityShipped')
            received = xm.Int('.//QuantityReceived')
            case_quantity = xm.Int('.//QuantityInCase')
            prep_details = xm.Field('.//PrepDetails', PrepDetailsSchema(), many=True)

        items = xm.Field('.//member', ShipmentSchema(), many=True, default=list)
        next_token = xm.String('.//NextToken', default=None)

    def api_name(self):
        return 'FulfillmentInboundShipment'

    def build_params(self, *args, **kwargs):
        doc = args[0] if args else kwargs['doc']
        return {'ShipmentId': doc['order_number']}

    def process_response(self, args, kwargs, response):
        results = []
        while response:
            results.extend(response['items'])

            next_token = response.next_token
            response = self.make_api_call(
                'ListInboundShipmentItemsByNextToken',
                throttle_action='ListInboundShipmentItems',
                NextToken=next_token
            ) if next_token else None

        return results


########################################################################################################################


class GetTransportContent(MWSActor):

    class Schema(MWSResponseSchema):

        class PackageSchema(xm.Schema):
            ignore_missing = True

            class Dimensions(xm.Schema):
                units = xm.String('.//Unit')
                height = xm.Float('.//Height')
                length = xm.Float('.//Length')
                width = xm.Float('.//Width')

            weight = xm.Float('.//Weight/Value')
            tracking_number = xm.String('.//TrackingId')
            carrier = xm.String('.//CarrierName')
            status = xm.String('.//PackageStatus')
            dimensions = xm.Field('.//Dimensions', Dimensions())

        shipping = xm.Float('.//PartneredEstimate/Amount/Value')
        transport_status = xm.String('.//TransportStatus', required=True)
        packages = xm.Field('//member', PackageSchema(), many=True, default=list)

    def api_name(self):
        return 'FulfillmentInboundShipment'

    def build_params(self, *args, **kwargs):
        doc = args[0] if args else kwargs.pop('doc')
        return {'ShipmentId': doc['order_number']}

    def process_response(self, args, kwargs, response):
        print(response)
        order_doc = {
            'shipping': response.shipping,
            'transport_status': response.transport_status
        }
        results = response.packages

        return order_doc, results


########################################################################################################################


class ListOrders(MWSActor):

    class Schema(MWSResponseSchema):

        class OrderSchema(xm.Schema):
            ignore_missing = True

            order_number = xm.String('.//AmazonOrderId', required=True)
            seller_order_id = xm.String('.//SellerOrderId')
            date = xm.String('.//PurchaseDate')
            status = xm.String('.//OrderStatus')
            prime = xm.Boolean('.//IsPrime')
            fulfillment_channel = xm.String('.//FulfillmentChannel')
            business = xm.Boolean('.//IsBusinessOrder')
            replacement = xm.Boolean('.//IsReplacementOrder')

            class CustomerSchema(xm.Schema):
                ignore_missing = True

                class AddressSchema(xm.Schema):
                    ignore_missing = True

                    city = xm.String('.//City')
                    postal_code = xm.String('.//PostalCode')
                    state = xm.String('.//StateOrRegion')
                    country = xm.String('.//CountryCode')
                    lines = xm.String('.//*[starts-with(name(), "AddressLine")]', many=True)

                name = xm.String('.//BuyerName')
                email = xm.String('.//BuyerEmail')
                address = xm.Field('.//ShippingAddress', AddressSchema())

        orders = xm.Field('.//Order', OrderSchema(), many=True, default=list)
        next_token = xm.String('.//NextToken', default=None)

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

    def process_response(self, args, kwargs, response):
        results = []
        while response:

            # TODO: Update users of this actor to accept the new response format
            results.extend(response.orders)

            token = response.next_token
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


########################################################################################################################


class ListOrderItems(MWSActor):

    class Schema(MWSResponseSchema):

        class OrderItemSchema(xm.Schema):
            ignore_missing = True

            sku = xm.String('.//ASIN', required=True)
            msku = xm.String('.//SellerSKU')
            order_item_id = xm.String('.//OrderItemId')
            title = xm.String('.//Title')
            qty_ordered = xm.Int('.//QuantityOrdered')
            qty_shipped = xm.Int('.//QuantityShipped')
            price = xm.Float('.//ItemPrice/Amount')
            currency_code = xm.String('.//ItemPrice/CurrencyCode')
            shipping_price = xm.Float('.//ShippingPrice/Amount')

        items = xm.Field('.//OrderItem', OrderItemSchema(), many=True, default=list)
        next_token = xm.String('.//NextToken', default=None)

    def api_name(self):
        return 'Orders'

    def build_params(self, order_number):
        return {'AmazonOrderId': order_number}

    def process_response(self, args, kwargs, response):
        results = []
        while response:
            results.extend(response['items'])

            token = response.next_token
            response = self.make_api_call(
                'ListOrderItemsByNextToken',
                throttle_action='ListOrderItems',
                NextToken=token
            ) if token else None

        return results


########################################################################################################################


class ListFinancialEventGroups(MWSActor):

    class Schema(MWSResponseSchema):

        class EventGroupSchema(xm.Schema):
            ignore_missing = True

            group_id = xm.String('.//FinancialEventGroupId', required=True)
            group_status = xm.String('.//FinancialEventGroupStatus')
            fund_transfer_status = xm.String('.//FundTransferStatus')
            original_total = xm.Float('.//OriginalTotal/Amount')
            converted_total = xm.Float('.//ConvertedTotal/Amount')
            fund_transfer_date = xm.String('.//FundTransferDate')
            trace_id = xm.String('.//TraceId')
            account_tail = xm.String('.//AccountTail')
            beginning_balance = xm.Float('.//BeginningBalance/Amount')
            start_date = xm.String('.//FinancialEventGroupStartDate')
            end_date = xm.String('.//FinancialEventGroupEndDate')

        groups = xm.Field('.//FinancialEventGroup', EventGroupSchema(), many=True, default=list)
        next_token = xm.String('.//NextToken', default=None)

    def api_name(self):
        return 'Finances'

    def build_params(self, *, started_after=None, started_before=None):
        if started_after is None and started_before is None:
            started_after = (datetime.utcnow() - timedelta(days=90)).strftime(ISO_8601)

        return {k: v for k, v in {
            'FinancialEventGroupStartedAfter': started_after,
            'FinancialEventgroupStartedBefore': started_before
        }.items() if v is not None}

    def process_response(self, args, kwargs, response):
        results = []
        while response:
            results.extend(response.groups)

            token = response.next_token
            response = self.make_api_call(
                'ListFinancialEventGroupsByNextToken',
                throttle_action='ListFinancialEventGroups',
                NextToken=token
            ) if token else None

        return results


########################################################################################################################


class ComponentList(xm.Schema):
    """Schema for ChargeComponentList, FeeComponentList, and DirectPaymentList."""

    class Component(xm.Schema):
        type = xm.First(('.//ChargeType', './/FeeType', './/DirectPaymentType'))
        amount = xm.First(('.//CurrencyAmount', './/Amount'), cast=float)

    _items = xm.First(('.//ChargeComponent', './/FeeComponent', './/DirectPayment', './/OrderChargeAdjustment', './/TaxWithheldComponent'),
                     cast=Component(),
                     many=True,
                     default=list)

    def post_load(self, data):
        return {
            item.type: item.amount
            for item in data['_items']
        }


class Promotion(xm.Schema):
    ignore_missing = True

    type = xm.String('.//PromotionType')
    id = xm.String('.//PromotionId')
    amount = xm.Float('.//PromotionAmount/CurrencyAmount', default=0)


class ListFinancialEvents(MWSActor):

    class Schema(MWSResponseSchema):

        class ShipmentEvent(xm.Schema):
            ignore_missing = True

            class ShipmentItem(xm.Schema):
                ignore_missing = True

                msku = xm.String('.//SellerSKU')
                order_item_id = xm.String('.//OrderItemId')
                order_adj_id = xm.String('.//OrderAdjustmentItemId')
                qty_shipped = xm.Int('.//QuantityShipped')

                charges = xm.Nested('.//ItemChargeList', ComponentList())
                taxes = xm.Nested('.//TaxesWithheldList', ComponentList())
                charge_adjustments = xm.Nested('.//ItemChargeAdjustmentList', ComponentList())
                fees = xm.Nested('.//ItemFeeList', ComponentList())
                fee_adjustments = xm.Nested('.//ItemFeeAdjustmentList', ComponentList())
                promotions = xm.Nested('.//PromotionList/Promotion', Promotion())
                promo_adjustments = xm.Nested('.//PromotionAdjustmentList/Promotion', Promotion())

            amazon_order_id = xm.String('.//AmazonOrderId')
            seller_order_id = xm.String('.//SellerOrderId')
            marketplace = xm.String('.//MarketplaceName')
            posted_date = xm.String('.//PostedDate')

            charges = xm.Nested('.//OrderChargeList', ComponentList())
            charge_adjustments = xm.Nested('.//OrderChargeAdjustmentList', ComponentList())
            shipment_fees = xm.Nested('.//ShipmentFeeList', ComponentList())
            shipment_adjustments = xm.Nested('.//ShipmentFeeAdjustmentList', ComponentList())
            fees = xm.Nested('.//OrderFeeList', ComponentList())
            fee_adjustments = xm.Nested('.//OrderFeeAdjustmentList', ComponentList())
            direct_payments = xm.Nested('.//DirectPaymentList', ComponentList())
            items = xm.List('.//ShipmentItemList/ShipmentItem', ShipmentItem())
            item_adjustments = xm.List('.//ShipmentItemAdjustments/ShipmentItem', ShipmentItem())

        class RetroChargeEvent(xm.Schema):
            ignore_missing = True
            type = xm.String('.//RetrochargeEventType')
            amazon_order_id = xm.String('.//AmazonOrderId')
            posted_date = xm.String('.//PostedDate')
            base_tax = xm.Float('.//BaseTax/Amount')
            shipping_tax = xm.Float('.//ShippingTax/Amount')
            marketplace = xm.String('.//MarketplaceName')

        class ServiceFeeEvent(xm.Schema):
            ignore_missing = True
            amazon_order_id = xm.String('.//AmazonOrderId')
            reason = xm.String('.//FeeReason')
            fees = xm.Nested('.//FeeList', ComponentList())
            msku = xm.String('.//SellerSKU')
            fnsku = xm.String('.//FnSKU')
            description = xm.String('.//FeeDescription')
            sku = xm.String('.//ASIN')

        class AdjustmentEvent(xm.Schema):
            ignore_missing = True

            class AdjustmentItem(xm.Schema):
                ignore_missing = True

                quantity = xm.Int('.//Quantity')
                per_unit_amount = xm.Float('.//PerUnitAmount/Amount')
                total_amount = xm.Float('.//TotalAmount/Amount')
                msku = xm.String('.//SellerSKU')
                fnsku = xm.String('.//FnSKU')
                sku = xm.String('.//ASIN')
                description = xm.String('.//ProductDescription')

            type = xm.String('.//AdjustmentType')
            amount = xm.Float('.//AdjustmentAmount/Amount')
            posted_date = xm.String('.//PostedDate')
            items = xm.List('.//AdjustmentItemList/AdjustmentItem', AdjustmentItem())

        shipment_events = xm.List('.//ShipmentEventList/ShipmentEvent', ShipmentEvent())
        refund_events = xm.List('.//RefundEventList/ShipmentEvent', ShipmentEvent())
        guarantee_events = xm.List('.//GuaranteeClaimEventList/ShipmentEvent', ShipmentEvent())
        chargeback_events = xm.List('.//ChargebackEventList/ShipmentEvent', ShipmentEvent())
        retrocharge_events = xm.List('.//RetrochargeEventList/RetrochargeEvent', RetroChargeEvent())
        service_fee_events = xm.List('.//ServiceFeeEventList/ServiceFeeEvent', ServiceFeeEvent())
        adjustment_events = xm.List('.//AdjustmentEventList/AdjustmentEvent', AdjustmentEvent())
        next_token = xm.String('.//NextToken', default=None)

    def api_name(self):
        return 'Finances'

    def build_params(self, *args, order_number=None, group_id=None, posted_after=None, posted_before=None):
        return {k: v for k, v in {
            'AmazonOrderId': order_number,
            'FinancialEventGroupId': group_id,
            'PostedAfter': posted_after,
            'PostedBefore': posted_before
        }.items() if v is not None}

    def process_response(self, args, kwargs, response):
        results = {
            'shipment_events': [],
            'refund_events': [],
            'guarantee_events': [],
            'chargeback_events': [],
            'retrocharge_events': [],
            'service_fee_events': [],
            'adjustment_events': [],
        }
        while response:
            results['shipment_events'].extend(response.get('shipment_events', []))
            results['refund_events'].extend(response.get('refund_events', []))
            results['guarantee_events'].extend(response.get('guarantee_events', []))
            results['chargeback_events'].extend(response.get('chargeback_events', []))
            results['retrocharge_events'].extend(response.get('retrocharge_events', []))
            results['service_fee_events'].extend(response.get('service_fee_events', []))
            results['adjustment_events'].extend(response.get('adjustment_events', []))

            token = response.next_token
            response = self.make_api_call(
                'ListFinancialEventGroupsByNextToken',
                throttle_action='ListFinancialEventGroups',
                NextToken=token
            ) if token else None

        return results
