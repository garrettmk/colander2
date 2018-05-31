import decimal
import itertools
import functools

from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import UniqueConstraint

from app import db
from .core import PolymorphicBase, UpdateMixin, SearchMixin, CURRENCY
from .finances import OrderEvent, OrderItemEvent, InventoryAdjustment


########################################################################################################################


def inventory_property(name, default=None):
    """A shortcut for using detail_property with InventoryDetails."""

    def getter(self):
        details = getattr(self, 'details')
        try:
            return getattr(details[-1], name)
        except IndexError:
            return default

    def setter(self, value):
        details = getattr(self, 'details')
        if not details or details[-1].id:
            details.append(InventoryDetails(inventory_id=self.id))

        setattr(details[-1], name, value)

    def expr(cls):
        return db.select([
            getattr(InventoryDetails, name)
        ]).where(
            InventoryDetails.inventory_id == cls.id
        ).order_by(
            InventoryDetails.timestamp.desc()
        ).limit(1).label(name)

    return hybrid_property(fget=getter, fset=setter, expr=expr)


########################################################################################################################


class Order(db.Model, PolymorphicBase, UpdateMixin, SearchMixin):
    """Represents a transfer of inventory from one entity to another."""
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='RESTRICT'), nullable=False)
    dest_id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='RESTRICT'))
    date = db.Column(db.DateTime, default=db.func.now())
    order_number = db.Column(db.String(64))

    source = db.relationship(
        'Entity',
        primaryjoin='Order.source_id == Entity.id',
        back_populates='orders_from',
    )
    destination = db.relationship(
        'Entity',
        primaryjoin='Order.dest_id == Entity.id',
        back_populates='orders_to'
    )
    items = db.relationship('OrderItem', back_populates='order', passive_deletes=True)
    shipments = db.relationship('Shipment', back_populates='order')
    financials = db.relationship('OrderEvent', back_populates='order')

    __search_fields__ = ['order_number']

    def __repr__(self):
        src_name = self.source.name if self.source else None
        dest_name = self.destination.name if self.destination else None
        return f'<{type(self).__name__} ({self.id}) {self.order_number} {src_name} -> {dest_name}>'

    def send_inventory(self):
        for item in self.items:
            item.send_inventory()

    def receive_inventory(self):
        for item in self.items:
            item.receive_inventory()

    def charge_account(self, account):
        for item in self.items:
            item.charge_account(account)

    def charge_transfer(self, account):
        for item in self.items:
            item.charge_transfer(account)

    @property
    def total(self):
        order_cost = sum(e.net for e in self.financials)
        item_cost = sum(sum(e.net for e in i.financials) for i in self.items)
        return order_cost + item_cost

    def profit(self):
        profits = [i.profit() for i in self.items]
        profits = [p for p in profits if p is not None]
        return sum(profits)


########################################################################################################################


class OrderItem(db.Model, PolymorphicBase, UpdateMixin, SearchMixin):
    """A single SKU in an order."""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE'), nullable=False)
    source_id = db.Column(db.Integer, db.ForeignKey('inventory.id', ondelete='RESTRICT'))
    dest_id = db.Column(db.Integer, db.ForeignKey('inventory.id', ondelete='RESTRICT'))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shipment.id'))
    received = db.Column(db.Integer, nullable=False, default=0)

    order = db.relationship('Order', back_populates='items')
    financials = db.relationship('OrderItemEvent', back_populates='item')
    source = db.relationship(
        'Inventory',
        primaryjoin='Inventory.id == OrderItem.source_id',
        back_populates='order_items',
        single_parent=True
    )
    destination = db.relationship(
        'Inventory',
        primaryjoin='Inventory.id == OrderItem.dest_id',
        back_populates='fulfillments',
        single_parent=True
    )
    shipment = db.relationship('Shipment', back_populates='items')

    def __init__(self, *args, **kwargs):
        self.quantity = 1
        self.received = 0
        super().__init__(*args, **kwargs)

    def __repr__(self):
        source_sku = self.source.listing.sku if self.source and self.source.listing else None
        dest_sku = self.destination.listing.sku if self.destination and self.destination.listing else None
        return f'<{type(self).__name__} ({self.id}) {self.quantity}x {source_sku}->{dest_sku}>'

    def send_inventory(self, sent=None):
        """Modify the sender's inventory levels."""
        sent = sent or self.quantity
        self.quantity = sent

        self.source.fulfillable = (self.source.fulfillable or 0) - sent

    def receive_inventory(self, received=None):
        """Modify inventory levels for the received amount."""
        received = received or self.quantity
        self.received = received

        self.destination.fulfillable = (self.destination.fulfillable or 0) + received

    def charge_account(self, account, cost=None):
        """"""
        if self.source.owner_id == self.destination.owner_id:
            cost = cost or None
        else:
            try:
                cost = cost or (-self.source.listing.price * self.quantity)
            except:
                cost = None

        event = OrderItemEvent(
            account=account,
            originator=self.order.source,
            item=self,
            net=cost,
            description=f'Transfer {self.quantity}x of {self.source.listing.sku} to {self.destination.listing.sku}'
        )

        db.session.add(event)
        db.session.commit()

    def refund_account(self, account, cost):
        raise NotImplementedError

    def profit(self):
        total_cost, cost_ea = self.source.calculate_cost()
        revenue = sum(e.net for e in self.financials if e.net is not None)

        try:
            return revenue + cost_ea
        except:
            return None


########################################################################################################################


class Shipment(db.Model, PolymorphicBase, UpdateMixin, SearchMixin):
    """An shipment of products."""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE'), nullable=False)
    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=lambda: datetime.utcnow())
    carrier = db.Column(db.String(64))
    tracking_number = db.Column(db.String(128))
    delivered_on = db.Column(db.DateTime)
    status = db.Column(db.String(32))

    order = db.relationship('Order', back_populates='shipments')
    items = db.relationship('OrderItem', back_populates='shipment')

    __search_fields__ = ['carrier', 'tracking_number', 'status']


########################################################################################################################


class InventoryDetails(db.Model, UpdateMixin):
    """Contains a listing's transient information details."""
    id = db.Column(db.Integer, primary_key=True)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.id', ondelete='CASCADE'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    fulfillable = db.Column(db.Integer, nullable=False, default=0)
    reserved = db.Column(db.Integer, nullable=False, default=0)
    unsellable = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(CURRENCY)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow())

    inventory = db.relationship('Inventory', back_populates='details')

    __table_args__ = (UniqueConstraint('timestamp', 'inventory_id'),)


########################################################################################################################


class Inventory(db.Model, UpdateMixin):
    """Maps an inventory relationship between a vendor listing and a market listing."""
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (UniqueConstraint('listing_id', 'owner_id'),)

    # Details
    active = inventory_property('active')
    fulfillable = inventory_property('fulfillable', default=0)
    reserved = inventory_property('reserved', default=0)
    unsellable = inventory_property('unsellable', default=0)
    price = inventory_property('price')
    timestamp = inventory_property('timestamp')

    details = db.relationship(
        'InventoryDetails',
        order_by=InventoryDetails.timestamp.asc(),
        back_populates='inventory',
        passive_deletes=True
    )

    # Relationships
    owner = db.relationship('Entity', back_populates='inventories')
    listing = db.relationship('Listing', back_populates='inventories')
    adjustments = db.relationship('InventoryAdjustment', back_populates='inventory')
    conversions = db.relationship('InventoryConversion', back_populates='destination')
    order_items = db.relationship(
        'OrderItem',
        primaryjoin='Inventory.id == OrderItem.source_id',
        back_populates='source',
        passive_deletes=True
    )
    fulfillments = db.relationship(
        'OrderItem',
        primaryjoin='Inventory.id == OrderItem.dest_id',
        back_populates='destination',
        passive_deletes=True
    )

    def __repr__(self):
        owner = self.owner.name if self.owner else None
        sku = self.listing.sku if self.listing else None
        return f'<{type(self).__name__} ({self.id}) {self.fulfillable}, {self.reserved}, {self.unsellable} {owner} {sku}>'

    @classmethod
    def __declare_last__(cls):
        db.event.listen(cls, 'before_insert', cls._ensure_owner)

    @staticmethod
    def _ensure_owner(mapper, conn, target):
        if target.owner_id is None:
            target.owner_id = target.listing.vendor_id

    def calculate_cost(self):
        """Calculates the total cost and average cost each for this inventory."""
        items = self.fulfillments
        item_events = [e for e in itertools.chain(*[i.financials for i in items])]
        orders = list(set(i.order for i in items))
        adjustments = self.adjustments

        # Get the cost of any converted inventory
        conversion_costs = sum(c.calculate_cost() for c in self.conversions)

        # Get the total cost of any OrderItems that fulfilled this inventory. OrderItemEvents with a `net` of None
        # are treated as a transfer, using the cost of the source inventory
        item_costs = 0
        for event in item_events:
            if event.net is None:
                item_costs += event.item.source.calculate_cost()[1] * event.item.quantity
            else:
                item_costs += event.net
        item_costs += sum(a.net for a in adjustments if a.net is not None)

        # Add up the costs of Orders that fulfilled this inventory (shipping, tax, etc)
        order_costs = sum(
            sum(e.net for e in o.financials)
            / sum(i.received for i in o.items)
            * sum(i.received for i in o.items if i.dest_id == self.id)
            for o in orders
        )

        # Add up any InventoryAdjustments for this inventory
        adjustment_costs = sum(a.net for a in adjustments)

        # Add everything up and return some answers
        total_cost = sum((
            item_costs,
            order_costs,
            conversion_costs,
            adjustment_costs
        ))

        total_received = sum((
            sum(i.received for i in items),
            sum(c.conversions_made for c in self.conversions),
            sum(a.quantity for a in adjustments)
        ))

        try:
            return total_cost, total_cost / total_received
        except:
            return None, None

    def calculate_revenues(self):
        """Return the total revenue and average revenue per sale"""
        total_sold = sum(i.quantity for i in self.order_items)
        total_revenue = sum(e.net for i in self.order_items for e in i.financials if e.net is not None)

        try:
            return total_revenue, total_revenue / total_sold
        except (TypeError, ZeroDivisionError, decimal.DivisionByZero, decimal.InvalidOperation):
            return None, None

    def calculate_profit(self):
        """Return the total profit and average profit per unit."""
        total_cost, cost_ea = self.calculate_cost()
        total_rev, rev_ea = self.calculate_revenues()

        try:
            return total_rev + total_cost, rev_ea + cost_ea
        except:
            return None, None


########################################################################################################################


def gcd(a, b):
    """Compute the greatest common divisor of a and b."""
    while b > 0:
        a, b = b, a % b

    return a


def lcm(*args):
    """Compute the least common multiple of a and b."""
    if len(args) == 2:
        return args[0] * args[1] // gcd(args[0], args[1])
    else:
        return functools.reduce(lcm, args)


########################################################################################################################


class InvConversionSource(db.Model, UpdateMixin):
    """A source inventory used by an InventoryConversion."""
    id = db.Column(db.Integer, primary_key=True)
    conv_id = db.Column(db.Integer, db.ForeignKey('inventory_conversion.id', ondelete='CASCADE'), nullable=False)
    inv_id = db.Column(db.Integer, db.ForeignKey('inventory.id', ondelete='CASCADE'), nullable=False)
    units = db.Column(db.Integer, nullable=False, default=1)

    conversion = db.relationship('InventoryConversion', back_populates='sources')
    inventory = db.relationship('Inventory')

    __table_args__ = (UniqueConstraint('conv_id', 'inv_id'),)

    def __repr__(self):
        return f'<{type(self).__name__} ({self.id})>'


########################################################################################################################


class InventoryConversion(db.Model, UpdateMixin):
    """Converts one or more source inventories into a destination inventory."""
    id = db.Column(db.Integer, primary_key=True)
    dest_id = db.Column(db.Integer, db.ForeignKey('inventory.id', ondelete='CASCADE'), nullable=False)
    cost_ea = db.Column(CURRENCY)
    conversions_made = db.Column(db.Integer, nullable=False, default=0)

    destination = db.relationship('Inventory', back_populates='conversions')
    sources = db.relationship('InvConversionSource', back_populates='conversion')

    def __repr__(self):
        return f'<{type(self).__name__} ({self.id})>'

    @property
    def units_per_dest(self):
        """The total number of source units used in each conversion."""
        return sum(s.units for s in self.sources)

    @property
    def min_source_units(self):
        """The minimum number of units required from each source, in a tuple."""
        return tuple(lcm(s.inventory.listing.quantity or 1, s.units) for s in self.sources)

    @property
    def total_units_per_batch(self):
        """The total number of source units used in each batch."""
        return lcm(self.units_per_dest, *self.min_source_units)

    @property
    def source_units_per_batch(self):
        units_per_dest = self.units_per_dest
        total_batch_units = self.total_units_per_batch

        return tuple(total_batch_units * s.units // units_per_dest for s in self.sources)

    @property
    def batch_size(self):
        """The number of destination units produced in each batch."""
        return self.total_units_per_batch / self.units_per_dest

    def convert(self, batches=1):
        """Convert source inventory to destination inventory."""
        required = tuple(units * batches for units in self.source_units_per_batch)
        produced = self.batch_size * batches

        # Check to make sure there is enough inventory to make the conversion
        sufficient_inventory = tuple(s.inventory.fulfillable >= r for s, r in zip(self.sources, required))
        if False in sufficient_inventory:
            raise Exception('Insufficient inventory.')

        # Perform the conversion
        for source, req in zip(self.sources, required):
            source.inventory.fulfillable -= req

        self.destination.fulfillable += produced
        self.conversions_made += batches

    def calculate_cost(self):
        """Calculate the cost of all the converted inventory."""
        required = tuple(units for units in self.source_units_per_batch)
        cost_ea = sum(req * s.inventory.calculate_cost()[1] for req, s in zip(required, self.sources))
        return cost_ea * self.conversions_made