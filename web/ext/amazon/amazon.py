from datetime import datetime, timedelta
from dramatiq.composition import group, pipeline

from app import db
from models.entities import Vendor, Customer
from models.listings import Listing, ListingDetails, Inventory
from models.orders import Order, OrderItem, Shipment
from models.finances import FinancialAccount, FinancialEvent, OrderEvent, OrderItemEvent
from ext.core import ext_actor, ExtActor
from .tasks import mws, pa
from .tasks.common import ISO_8601
import tasks.ops.listings


########################################################################################################################


@ext_actor
def process_listings(docs):
    for doc in docs:
        pipeline([
            mws.GetCompetitivePricingForASIN.message(doc),
            pa.ItemLookup.message(),
            mws.GetMyFeesEstimate.message(),
            import_listing.message()
        ]).run()


@ext_actor
def process_inbound_orders(docs, vendor_id):
    for doc in docs:
        order_id = import_inbound_order(doc, vendor_id=vendor_id)
        pipeline([
            mws.ListInboundShipmentItems.message(doc, vendor_id=vendor_id),
            process_inbound_order_items.message(vendor_id=vendor_id),
            mws.GetTransportContent.message(doc),
            process_inbound_shipments.message(order_id=order_id)
        ]).run()


@ext_actor
def process_inbound_order_items(docs, vendor_id):
    amazon = Vendor.query.filter_by(name='Amazon').one()

    for doc in docs:
        order_number = doc.pop('order_number')
        vendor_sku = doc.pop('msku')
        fnsku = doc.pop('fnsku')

        # Get the order
        order = Order.query.filter_by(source_id=vendor_id, dest_id=amazon.id, order_number=order_number).first()\
                or Order(source_id=vendor_id, dest_id=amazon.id, order_number=order_number)

        db.session.add(order)

        # Get the listings
        listing = Listing.query.filter_by(vendor_id=order.source_id, sku=vendor_sku).one()
        amz_listing = Listing.query.filter(Listing.vendor_id == amazon.id, Listing.extra['fnsku'].astext == fnsku).one()

        # Get the inventories
        src_inv = listing.inventory
        dest_inv = Inventory.query.filter_by(listing_id=amz_listing.id, owner_id=listing.vendor.id).first()\
                   or Inventory(listing=amz_listing, owner=listing.vendor)

        db.session.add(dest_inv)

        # Get the order item
        item = OrderItem.query.filter_by(order_id=order.id, source_id=src_inv.id, dest_id=dest_inv.id).first()\
               or OrderItem(order=order, source=src_inv, destination=dest_inv)

        item.update(doc)

        # If this is a new order item, send_inventory()
        if item.id is None:
            item.send_inventory()

        db.session.add(item)
        db.session.commit()


@ext_actor
def process_inbound_shipments(order_and_shipment_docs, order_id):
    order_doc, shipment_docs = order_and_shipment_docs
    order = Order.query.filter_by(id=order_id).one()
    order.update(order_doc)

    for doc in shipment_docs:
        shipment = Shipment.query.filter_by(tracking_number=doc['tracking_number']).first()\
                   or Shipment(order_id=order_id)

        shipment.update(doc)

        db.session.add(shipment)
        db.session.commit()

    if len(shipment_docs) == 1:
        for item in order.items:
            item.shipment_id = shipment.id

    db.session.commit()


@ext_actor
def process_orders(docs, vendor_id):
    amazon = Vendor.query.filter_by(name='Amazon').one()

    for cust_doc, order_doc in docs:
        if 'name' in cust_doc:
            customer = Customer.query.filter_by(name=cust_doc['name']).first() or Customer()
            customer.update(cust_doc)
            db.session.add(customer)
        else:
            customer = None

        order = Order.query.filter_by(source_id=amazon.id, order_number=order_doc['order_number']).first()\
                or Order()

        order.update(order_doc)
        order.source = amazon
        order.destination = customer
        order.date = datetime.strptime(order_doc['date'].replace('Z', ''), ISO_8601)

        db.session.add(order)
        db.session.commit()

        pipeline([
            mws.ListOrderItems.message(order.order_number),
            process_order_items.message(vendor_id, order.id),
        ]).run()


@ext_actor
def process_order_items(vendor_id, order_id, docs):
    amazon = Vendor.query.filter_by(name='Amazon').one()
    vendor = Vendor.query.filter_by(id=vendor_id).one()

    for item_doc in docs:
        sku = item_doc['sku']
        amz_listing = Listing.query.filter_by(vendor_id=amazon.id, sku=sku).first()\
                    or Listing(vendor=amazon, sku=sku)

        item = OrderItem.query.filter(
            OrderItem.order_id == order_id,
            OrderItem.extra['order_item_id'].astext == item_doc['order_item_id']
        ).first() or OrderItem(order_id=order_id)

        item.quantity = item_doc.pop('qty_shipped')
        item.received = item.quantity
        item.source = Inventory.query.filter_by(owner_id=vendor.id, listing_id=amz_listing.id).first()\
                      or Inventory(owner=vendor, listing=amz_listing)
        item.destination = None
        item.update(item_doc)

        db.session.add(item)
        db.session.commit()


@ext_actor
def process_financial_event_groups(vendor_id, docs):
    """Process the output of ListFinancialEventGroups."""
    for group_doc in docs:
        pipeline([
            mws.ListFinancialEvents.message(group_id=group_doc['group_id'], vendor_id=vendor_id),
            process_financial_events.message(vendor_id, group_doc)
        ]).run()


@ext_actor
def process_financial_events(vendor_id, group_doc, event_docs):
    amazon = Vendor.query.filter_by(name='Amazon').one()
    account = FinancialAccount.query.filter_by(owner_id=vendor_id, name='Amazon').first()\
                or FinancialAccount(owner_id=vendor_id, name='Amazon')

    db.session.add(account)

    # Get or create the event for the group
    event_group = FinancialEvent.query.filter(
        FinancialEvent.extra['group_id'].astext == group_doc['group_id']
    ).first() or FinancialEvent(account=account, originator=amazon)

    # Update the event
    event_group.update(group_doc)
    event_group.date = datetime.strptime(group_doc['start_date'].replace('Z', ''), ISO_8601)
    event_group.net = group_doc.get('converted_total', None)
    event_group.description = f"FinancialEventGroup {group_doc['start_date']} - {group_doc.get('end_date', 'Open')}"

    # Add to the DB
    db.session.add(event_group)

    # Process ServiceFeeEvents
    for event_doc in event_docs['service_fee_event_list']:
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
    for event_doc in event_docs['shipment_event_list']:
        posted_date = datetime.strptime(event_doc.pop('posted_date').replace('Z', ''), ISO_8601)

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
    for event_doc in event_docs['refund_event_list']:
        posted_date = datetime.strptime(event_doc.get('posted_date').replace('Z', ''), ISO_8601)

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
            item_event.net = sum(item_doc.get('charge_adjustments', {}).values())\
                             + sum(item_doc.get('fee_adjustments', {}).values())\
                             + sum(promo['amount'] for promo in item_doc.get('promotion_adjustments', {}).values())

            # Add to the db
            db.session.add(item_event)

    # Commit
    db.session.commit()


@ext_actor
def process_inventory(docs, vendor_id):
    vendor = Vendor.query.filter_by(id=vendor_id).one()

    for doc in docs:
        # Import the Amazon
        amz_doc = {'sku': doc['sku'], 'fnsku': doc['fnsku']}
        amz_id = import_listing(amz_doc)

        # Import the vendor listing
        vnd_doc = {'vendor_id': vendor_id, 'sku': doc['msku']}
        vnd_id = getattr(vendor.extension, 'import_listing', tasks.ops.listings.import_listing_default)(vnd_doc)

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
        pipeline([
            mws.GetCompetitivePricingForASIN.message(amz_doc, vendor_id=vendor_id),
            pa.ItemLookup.message(vendor_id=vendor_id),
            mws.GetMyFeesEstimate.message(vendor_id=vendor_id),
            import_listing.message(),
            copy_to_listing.message(vnd_id)
        ]).run()


@ext_actor
def copy_to_listing(dest_id, source_id):
    source = Listing.query.filter_by(id=source_id).one()
    dest = Listing.query.filter_by(id=dest_id).one()
    fields = ('title', 'brand', 'model', 'features', 'description')

    for field in fields:
        if getattr(dest, field) is None:
            setattr(dest, field, getattr(source, field))

    db.session.commit()


########################################################################################################################


@ext_actor
def import_listing(doc):
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

    return listing.id


@ext_actor
def update_listings(listing_ids):
    listings = Listing.query.filter(Listing.id.in_(listing_ids)).all()

    for listing in listings:
        doc = {'sku': listing.sku}

        pipeline([
            mws.GetCompetitivePricingForASIN.message(doc),
            pa.ItemLookup.message(),
            mws.GetMyFeesEstimate.message(),
            import_listing.message()
        ]).run()


@ext_actor
def import_matches(listing_id):
    """Import any ASINs that might match listing."""
    listing = Listing.query.filter_by(id=listing_id).one()

    if listing.brand and listing.model:
        query_str = f'{listing.brand} {listing.model}'
    elif listing.title:
        query_str = listing.title
    else:
        raise ValueError('Listing does not contain enough information to match.')

    pipeline([
        mws.ListMatchingProducts.message(query_str),
        process_listings.message()
    ]).run()


@ext_actor
def import_inventory(vendor_id):
    """Import any ASINs that have had inventory activity in the last 90 days."""
    pipeline([
        mws.ListInventorySupply.message(vendor_id=vendor_id),
        process_inventory.message(vendor_id=vendor_id)
    ]).run()


@ext_actor
def import_inbound_order(doc, vendor_id):
    amazon = Vendor.query.filter_by(name='Amazon').one()
    vendor = Vendor.query.filter_by(id=vendor_id).one()

    order = Order.query.filter_by(order_number=doc['order_number']).first() or Order()
    order.update(source_id=vendor.id, dest_id=amazon.id, **doc)

    db.session.add(order)
    db.session.commit()

    return order.id


@ext_actor
def import_inbound_orders(vendor_id):
    pipeline([
        mws.ListInboundShipments.message(vendor_id=vendor_id),
        process_inbound_orders.message(vendor_id=vendor_id)
    ]).run()


@ext_actor
def import_orders(vendor_id):
    pipeline([
        mws.ListOrders.message(vendor_id=vendor_id),
        process_orders.message(vendor_id=vendor_id)
    ]).run()


@ext_actor
def import_financials(vendor_id):
    pipeline([
        mws.ListFinancialEventGroups.message(vendor_id=vendor_id),
        process_financial_event_groups.message(vendor_id)
    ]).run()
