import datetime as dt
import dramatiq.composition as dqc
import marshmallow as mm
import marshmallow.fields as mmf

from core import db, filter_with_json
from ext.common import ExtActor
from models import Vendor, Customer, Listing, ListingDetails, Inventory, Order, OrderItem, Shipment,\
    FinancialAccount, FinancialEvent, OrderEvent, OrderItemEvent

from .tasks import mws, pa
from .tasks.common import ISO_8601
import tasks.ops as coreops


########################################################################################################################


class ImportListing(ExtActor):
    """Import a listing specified in a JSON document. Only looks at the document's 'sku' field."""
    public = True

    class Schema(mm.Schema):
        """Parameter schema for ImportListing."""
        class ListingSchema(mm.Schema):
            sku = mmf.String(required=True, title='Listing SKU')

            @mm.decorators.post_load(pass_original=True)
            def include_all(self, data, original):
                for key, value in original.items():
                    if key not in data:
                        data[key] = value
                return data

        listing = mmf.Nested(ListingSchema, required=True, title='Listing document')

    def perform(self, listing=None):
        doc = listing
        amazon = Vendor.query.filter_by(name='Amazon').one()
        listing = Listing.query.filter_by(vendor_id=amazon.id, sku=doc['sku']).first()
        if listing is None:
            listing = Listing(vendor=amazon)

        amz_details = {k: v for k, v in {
            'offers': doc.pop('offers', None),
            'prime': doc.pop('prime', None)
        }.items() if v is not None}

        listing.update(doc)
        if amz_details:
            if not listing.details or listing.details[-1].id:
                listing.details.append(ListingDetails(listing_id=listing.id))
            listing.details[-1].update(amz_details)

        db.session.add(listing)
        db.session.commit()

        self.context['listing_id'] = listing.id
        return listing.id


########################################################################################################################


class UpdateListings(ExtActor):
    """Updates the Listing models with the given IDs."""
    public = True

    class Schema(mm.Schema):
        """Parameter schema for UpdateListings."""
        query = mmf.Dict(missing=dict, title='Listing query')

    def perform(self, query=None):
        amazon = Vendor.query.filter(
            db.or_(
                Vendor.url.ilike('%amazon.com%'),
                Vendor.name.ilike('amazon'),
                Vendor.name.ilike('amazon.com')
            )
        ).one()

        query.update(vendor_id=amazon.id)
        listings = filter_with_json(Listing.query, query)

        for listing in listings:
            self.context.child(
                mws.GetCompetitivePricingForASIN.message(),
                pa.ItemLookup.message(),
                mws.GetMyFeesEstimate.message(),
                ImportListing.message(),

                title=f'Update SKU #{listing.sku}',
                data={'listing': {'sku': listing.sku}}
            ).send()


########################################################################################################################


class ImportMatchingListings(ExtActor):
    """Search the vendor and import any listings that match the given product."""
    public = True

    class Schema(mm.Schema):
        """Parameter schema for ImportMatches."""
        query = mmf.Dict(missing=dict, title='Listings query')

    def perform(self, query=None):
        amazon = Vendor.query.filter(
            db.or_(
                Vendor.url.ilike('%amazon.com%'),
                Vendor.name.ilike('amazon'),
                Vendor.name.ilike('amazon.com')
            )
        ).one()

        # Modify the filter to exclude listings from Amazon
        listings = filter_with_json(Listing.query, query).filter(Listing.vendor_id != amazon.id)

        for listing in listings:
            if listing.brand and listing.model:
                query_str = f'{listing.brand} {listing.model}'
            elif listing.title:
                query_str = listing.title
            else:
                raise ValueError('Listing does not contain enough information to match.')

            self.context.child(
                mws.ListMatchingProducts.message(query=query_str),
                ProcessListings.message(),

                data={'vendor_id': listing.vendor_id}
            ).send()


class ProcessListings(ExtActor):
    """Process the results of a call to ListMatchingProducts."""

    class Schema(mm.Schema):
        """Parameter schema for ProcessListings."""
        listings = mmf.List(mmf.Dict(), required=True, title='Listing documents')

    def perform(self, listings=None):
        for doc in listings:
            self.context.child(
                mws.GetCompetitivePricingForASIN.message(),
                pa.ItemLookup.message(),
                mws.GetMyFeesEstimate.message(),
                ImportListing.message(),

                data={
                    'listing': doc,
                    'vendor_id': self.context['vendor_id']
                }
            ).send()


########################################################################################################################


class ImportInventory(ExtActor):
    """Import inventory data for the given vendor."""
    public = True

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')

    def perform(self, vendor_id=None):
        """Import any ASINs that have had inventory activity in the last 90 days."""
        dqc.pipeline([
            mws.ListInventorySupply.message(vendor_id=vendor_id),
            ProcessInventory.message(vendor_id=vendor_id)
        ]).run()


class ProcessInventory(ExtActor):
    """Process the results of a call to ListInventorySupply."""

    class Schema(mm.Schema):
        docs = mmf.List(mmf.Dict(), required=True, title='Documents')
        vendor_id = mmf.Int(required=True, title='Vendor ID')

    def perform(self, docs=None, vendor_id=None):
        vendor = Vendor.query.filter_by(id=vendor_id).one()

        for doc in docs:
            # Import the Amazon
            amz_doc = {'sku': doc['sku'], 'fnsku': doc['fnsku']}
            amz_id = ImportListing(amz_doc)

            # Import the vendor listing
            vnd_doc = {'vendor_id': vendor_id, 'sku': doc['msku']}
            try:
                vnd_id = vendor.ext.call('ImportListing', **vnd_doc)
            except (ValueError, AttributeError):
                vnd_id = coreops.listings.ImportListing(doc=vnd_doc)

            # Update or create the inventory relationship
            inventory = Inventory.query.filter_by(
                owner_id=vendor_id,
                listing_id=amz_id
            ).first() or Inventory(owner_id=vendor_id, listing_id=amz_id)

            inventory.update(
                fnsku=doc['fnsku'],
                fulfillable=doc['fulfillable'],
            )

            db.session.add(inventory)
            db.session.commit()

            # Get updated info for the Amazon listing
            dqc.pipeline([
                mws.GetCompetitivePricingForASIN.message(amz_doc, vendor_id=vendor_id),
                pa.ItemLookup.message(vendor_id=vendor_id),
                mws.GetMyFeesEstimate.message(vendor_id=vendor_id),
                ImportListing.message(),
                CopyToListing.message(vnd_id)
            ]).run()


class CopyToListing(ExtActor):
    """Copy some basic info from one listing to another."""

    class Schema(mm.Schema):
        source_id = mmf.Int(required=True, title='Source listing ID')
        dest_id = mmf.Int(required=True, title='Destination listing ID')

    def perform(self, dest_id, source_id):
        source = Listing.query.filter_by(id=source_id).one()
        dest = Listing.query.filter_by(id=dest_id).one()
        fields = ('title', 'brand', 'model', 'features', 'description')

        for field in fields:
            if getattr(dest, field) is None:
                setattr(dest, field, getattr(source, field))

        db.session.commit()


########################################################################################################################


class ImportInboundOrder(ExtActor):
    """Create or update the order specified by the document and the vendor ID."""
    public = True

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')
        doc = mmf.Dict(required=True, title='Order document')

    def perform(self, doc, vendor_id):
        amazon = Vendor.query.filter_by(name='Amazon').one()
        vendor = Vendor.query.filter_by(id=vendor_id).one()

        order = Order.query.filter_by(order_number=doc['order_number']).first() or Order()
        order.update(source_id=vendor.id, dest_id=amazon.id, **doc)

        db.session.add(order)
        db.session.commit()

        return order.id


class ImportInboundOrders(ExtActor):
    """Import inbound order data for the given vendor."""
    public = True

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')

    def perform(self, vendor_id):
        dqc.pipeline([
            mws.ListInboundShipments.message(vendor_id=vendor_id),
            ProcessInboundOrders.message(vendor_id=vendor_id)
        ]).run()


class ProcessInboundOrders(ExtActor):
    """Process inbound order documents."""

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')
        docs = mmf.List(mmf.Dict(), required=True, title='Inbound order documents')

    def perform(self, vendor_id=None, docs=None):
        for doc in docs:
            order_id = ImportInboundOrder(doc, vendor_id=vendor_id)
            dqc.pipeline([
                mws.ListInboundShipmentItems.message(doc, vendor_id=vendor_id),
                ProcessInboundOrderItems.message(vendor_id=vendor_id),
                mws.GetTransportContent.message(doc),
                ProcessInboundShipments.message(order_id=order_id)
            ]).run()


class ProcessInboundOrderItems(ExtActor):
    """Process the results of mws.ListInboundShipmentItems()."""

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')
        docs = mmf.List(mmf.Dict(), required=True, title='Order item documents')

    def perform(self, vendor_id=None, docs=None):
        amazon = Vendor.query.filter_by(name='Amazon').one()

        for doc in docs:
            order_number = doc.pop('order_number')
            vendor_sku = doc.pop('msku')
            fnsku = doc.pop('fnsku')

            # Get the order
            order = Order.query.filter_by(source_id=vendor_id, dest_id=amazon.id, order_number=order_number).first() \
                    or Order(source_id=vendor_id, dest_id=amazon.id, order_number=order_number)

            db.session.add(order)

            # Get the listings
            listing = Listing.query.filter_by(vendor_id=order.source_id, sku=vendor_sku).one()
            amz_listing = Listing.query.filter(Listing.vendor_id == amazon.id,
                                               Listing.extra['fnsku'].astext == fnsku).one()

            # Get the inventories
            src_inv = listing.inventory
            dest_inv = Inventory.query.filter_by(listing_id=amz_listing.id, owner_id=listing.vendor.id).first() \
                       or Inventory(listing=amz_listing, owner=listing.vendor)

            db.session.add(dest_inv)

            # Get the order item
            item = OrderItem.query.filter_by(order_id=order.id, source_id=src_inv.id, dest_id=dest_inv.id).first() \
                   or OrderItem(order=order, source=src_inv, destination=dest_inv)

            item.update(doc)

            # If this is a new order item, send_inventory()
            if item.id is None:
                item.send_inventory()

            db.session.add(item)
            db.session.commit()


class ProcessInboundShipments(ExtActor):
    """Process the results of mws.GetTransportContent()."""

    class Schema(mm.Schema):

        class DocsSchema(mm.Schema):
            order = mmf.Dict(required=True, title='Order documents')
            shipments = mmf.List(mmf.Dict(), required=True, title='Shipment documents')

        order_id = mmf.Int(required=True, title='Order ID')
        docs = mmf.Nested(DocsSchema, required=True, title='Order and shipment documents')

    def perform(self, order_id=None, docs=None):
        order_doc, shipment_docs = docs['order'], docs['shipments']
        order = Order.query.filter_by(id=order_id).one()
        order.update(order_doc)

        for doc in shipment_docs:
            shipment = Shipment.query.filter_by(tracking_number=doc['tracking_number']).first() \
                       or Shipment(order_id=order_id)

            shipment.update(doc)

            db.session.add(shipment)
            db.session.commit()

        if len(shipment_docs) == 1:
            for item in order.items:
                item.shipment_id = shipment.id

        db.session.commit()


########################################################################################################################


class ImportOrders(ExtActor):
    """Import customer order data for the given vendor."""
    public = True

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')

    def perform(self, vendor_id=None):
        dqc.pipeline([
            mws.ListOrders.message(vendor_id=vendor_id),
            ProcessOrders.message(vendor_id=vendor_id)
        ]).run()


class ProcessOrders(ExtActor):
    """Process the results of ListOrders()."""

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')
        orders = mmf.List(mmf.Dict(), required=True, title='Order documents')

    def perform(self, vendor_id, orders):
        amazon = Vendor.query.filter_by(name='Amazon').one()

        for cust_doc, order_doc in orders:
            if 'name' in cust_doc:
                customer = Customer.query.filter_by(name=cust_doc['name']).first() or Customer()
                customer.update(cust_doc)
                db.session.add(customer)
            else:
                customer = None

            order = Order.query.filter_by(source_id=amazon.id, order_number=order_doc['order_number']).first() \
                    or Order()

            order.update(order_doc)
            order.source = amazon
            order.destination = customer
            order.date = dt.datetime.strptime(order_doc['date'].replace('Z', ''), ISO_8601)

            db.session.add(order)
            db.session.commit()

            dqc.pipeline([
                mws.ListOrderItems.message(order.order_number),
                ProcessOrderItems.message(vendor_id, order.id),
            ]).run()


class ProcessOrderItems(ExtActor):
    """Process the results of ListOrderItems()."""

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')
        order_id = mmf.Int(required=True, title='Order ID')
        items = mmf.List(mmf.Dict(), required=True, title='Order item documents')

    def perform(self, vendor_id=None, order_id=None, items=None):
        amazon = Vendor.query.filter_by(name='Amazon').one()
        vendor = Vendor.query.filter_by(id=vendor_id).one()

        for item_doc in items:
            sku = item_doc['sku']
            amz_listing = Listing.query.filter_by(vendor_id=amazon.id, sku=sku).first() \
                          or Listing(vendor=amazon, sku=sku)

            item = OrderItem.query.filter(
                OrderItem.order_id == order_id,
                OrderItem.extra['order_item_id'].astext == item_doc['order_item_id']
            ).first() or OrderItem(order_id=order_id)

            item.quantity = item_doc.pop('qty_shipped')
            item.received = item.quantity
            item.source = Inventory.query.filter_by(owner_id=vendor.id, listing_id=amz_listing.id).first() \
                          or Inventory(owner=vendor, listing=amz_listing)
            item.destination = None
            item.update(item_doc)

            db.session.add(item)
            db.session.commit()


########################################################################################################################


class ImportFinancials(ExtActor):
    """Import financial data for the given vendor."""
    public = True

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')

    def perform(self, vendor_id=None):
        dqc.pipeline([
            mws.ListFinancialEventGroups.message(vendor_id=vendor_id),
            ProcessFinancialEventGroups.message(vendor_id)
        ]).run()


class ProcessFinancialEventGroups(ExtActor):
    """Process the results of a call to mws.ListFinancialEventGroups()."""

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')
        groups = mmf.List(mmf.Dict(), required=True, title='Event group documents')

    def perform(self, vendor_id=None, docs=None):
        for group_doc in docs:
            dqc.pipeline([
                mws.ListFinancialEvents.message(group_id=group_doc['group_id'], vendor_id=vendor_id),
                ProcessFinancialEvents.message(vendor_id, group_doc)
            ]).run()


class ProcessFinancialEvents(ExtActor):
    """Process the results of a call to mws.ListFinancialEvents()."""

    class Schema(mm.Schema):
        vendor_id = mmf.Int(required=True, title='Vendor ID')
        group = mmf.Dict(required=True, title='Event group document')
        events = mmf.List(mmf.Dict(), required=True, title='Financial event documents')

    def perform(self, vendor_id, group, events):
        amazon = Vendor.query.filter_by(name='Amazon').one()
        account = FinancialAccount.query.filter_by(owner_id=vendor_id, name='Amazon').first() \
                  or FinancialAccount(owner_id=vendor_id, name='Amazon')

        db.session.add(account)

        # Get or create the event for the group
        event_group = FinancialEvent.query.filter(
            FinancialEvent.extra['group_id'].astext == group['group_id']
        ).first() or FinancialEvent(account=account, originator=amazon)

        # Update the event
        event_group.update(group)
        event_group.date = dt.datetime.strptime(group['start_date'].replace('Z', ''), ISO_8601)
        event_group.net = group.get('converted_total', None)
        event_group.description = f"FinancialEventGroup {group['start_date']} - {group.get('end_date', 'Open')}"

        # Add to the DB
        db.session.add(event_group)

        # Process ServiceFeeEvents
        for event_doc in events['service_fee_event_list']:
            event_desc = ', '.join(event_doc['fee_list'].keys())
            event_net = sum(event_doc['fee_list'].values())

            # Try to guess the appropriate event type
            event_type = {
                'FBAInboundTransportationFee': OrderEvent,
            }.get(event_desc, FinancialEvent)

            # Get or create the event
            fee_event = event_type.query.filter_by(
                account_id=account.id,
                originator_id=amazon.id,
                date=event_group.date,
                net=event_net,
                description=event_desc
            ).first() or event_type(
                account=account,
                originator=amazon,
                date=event_group.date,
                net=event_net,
                description=event_desc
            )

            # Update the event
            fee_event.update(event_doc)

            # Special processing depending on event type
            if event_desc == 'FBAInboundTransportationFee':
                # Try to attach this event to an inbound order
                order = Order.query.filter(
                    Order.source_id == vendor_id,
                    Order.dest_id == amazon.id,
                    Order.extra['shipping'].astext == str(-event_net)
                ).order_by(
                    Order.date.desc()
                ).first()

                fee_event.order = order

            db.session.add(fee_event)

        # Process ShipmentEvents
        for event_doc in events['shipment_event_list']:
            posted_date = dt.datetime.strptime(event_doc.pop('posted_date').replace('Z', ''), ISO_8601)

            # Process ShipmentItem events
            for item_doc in event_doc.pop('shipment_item_list', []):
                # Get or create the event
                item_event = OrderItemEvent.query.filter(
                    OrderItemEvent.extra['order_item_id'].astext == item_doc['order_item_id']
                ).first() or OrderItemEvent(
                    account=account,
                    originator=amazon,
                    date=posted_date,
                )

                # Update the event
                item_event.update(item_doc)
                item_event.description = item_doc['msku']
                item_event.net = sum(item_doc.get('charges', {}).values()) \
                                 + sum(item_doc.get('fees', {}).values()) \
                                 + sum(promo['amount'] for promo in item_doc.get('promotions', []))

                # Try to attach to an OrderItem
                item = OrderItem.query.filter(
                    OrderItem.extra['order_item_id'].astext == item_doc['order_item_id']
                ).first()

                item_event.item = item

                # Add to the DB
                db.session.add(item_event)

        # Process RefundEventList
        for event_doc in events['refund_event_list']:
            posted_date = dt.datetime.strptime(event_doc.get('posted_date').replace('Z', ''), ISO_8601)

            for item_doc in event_doc.pop('shipment_item_adjustment_list', []):
                msku = item_doc['msku']
                item_doc['amazon_order_id'] = event_doc['amazon_order_id']

                # Try to get the OrderItem this event corresponds to
                item = OrderItem.query.filter(
                    OrderItem.order_id == Order.id,
                    OrderItem.extra['msku'].astext == item_doc['msku']
                ).join(Order).filter(
                    Order.order_number == event_doc['amazon_order_id']
                ).one_or_none()

                # Get or create the event
                item_event = OrderItemEvent.query.filter(
                    OrderItemEvent.extra['adjustment_id'].astext == item_doc['adjustment_id']
                ).one_or_none() or OrderItemEvent(account=account, originator=amazon)

                # Update the event
                item_event.item = item
                item_event.update(item_doc)
                item_event.date = posted_date
                item_event.description = f'Refund - {msku}'
                item_event.net = sum(item_doc.get('charge_adjustments', {}).values()) \
                                 + sum(item_doc.get('fee_adjustments', {}).values()) \
                                 + sum(promo['amount'] for promo in item_doc.get('promotion_adjustments', {}).values())

                # Add to the db
                db.session.add(item_event)

        # Commit
        db.session.commit()
