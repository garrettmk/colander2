import re
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
import sqlalchemy_jsonbase as jb
import marshmallow as mm
import marshmallow.fields as mmf
import flask_sqlalchemy

from app import db
from core import URL, CURRENCY, quantize_decimal

from .mixins import SearchMixin
from .entities import Vendor
from .orders import Inventory, InventoryDetails


########################################################################################################################


def detail_property(name, **kwargs):
    """Creates a property that is a pass-through to the most recent detail object. Will not overwrite committed
     objects, but will create a new object."""

    def getter(self):
        details = getattr(self, 'details')
        try:
            return getattr(details[-1], name)
        except IndexError:
            return None

    def setter(self, value):
        details = getattr(self, 'details')
        if not details or details[-1].id:
            details.append(ListingDetails(listing_id=self.id))

        setattr(details[-1], name, value)

    def expr(cls):
        return db.select([
            getattr(ListingDetails, name)
        ]).where(
            ListingDetails.listing_id == cls.id
        ).order_by(
            ListingDetails.timestamp.desc()
        ).limit(1).label(name)

    return jb.hybrid_property(fset=setter, expr=expr, **kwargs)(getter)


def inventory_property(name, **kwargs):
    """A shortcut for using detail_property with InventoryDetails."""

    def getter(self):
        details = getattr(self, 'details')
        try:
            return getattr(details[-1], name)
        except IndexError:
            return None

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

    return jb.hybrid_property(fset=setter, expr=expr, **kwargs)(getter)


########################################################################################################################


class QuantityMap(db.Model):
    """A mapping of a quantity and its textual representation."""
    id = jb.Column(db.Integer, primary_key=True, label='QuantityMap ID')
    quantity = jb.Column(db.Integer, nullable=False, default=1, label='Quantity')
    text = jb.Column(db.String(64), nullable=False, unique=True, label='Description')

    def __repr__(self):
        return f'<QuantityMap {self.text} = {self.quantity}>'

    @classmethod
    def __declare_last__(cls):
        db.event.listen(flask_sqlalchemy.SignallingSession, 'before_flush', cls._maybe_update_products)

    @staticmethod
    def _maybe_update_products(session, context, instances):
        qmaps = [obj for obj in session.new if isinstance(obj, QuantityMap)] + \
                [obj for obj in session.dirty if isinstance(obj, QuantityMap)]

        for qmap in qmaps:
            qmap.update_products()

    def update_products(self):
        """Update all products affected by this quantity map."""
        Listing.query.filter(
            db.or_(
                Listing.quantity_desc.ilike(self.text),
                Listing.title.op('~*')(f'[[:<:]]{self.text}[[:>:]]')
            )
        ).update(
            {
                'quantity': self.quantity,
                'last_modified': datetime.utcnow()
            },
            synchronize_session=False
        )


########################################################################################################################


class ListingDetails(db.Model):
    """Contains a Listing's transient details, like price, rank, rating, etc."""
    id = jb.Column(db.Integer, primary_key=True, label='ListingDetails ID')
    listing_id = jb.Column(db.Integer, db.ForeignKey('listing.id', ondelete='CASCADE'), nullable=False, label='Listing ID')
    timestamp = jb.Column(db.DateTime, default=lambda: datetime.utcnow(), label='Timestamp')
    price = jb.Column(CURRENCY, label='Price')
    rank = jb.Column(db.Integer, label='Rank')
    rating = jb.Column(db.Float, label='Rating')

    listing = jb.relationship('Listing', back_populates='details', label='Listing')

    __table_args__ = (sa.UniqueConstraint('timestamp', 'listing_id'),)


########################################################################################################################


class Listing(db.Model, SearchMixin):
    """A description of a product for sale."""
    id = jb.Column(db.Integer, primary_key=True, label='Listing ID')
    vendor_id = jb.Column(db.Integer, db.ForeignKey('vendor.id', ondelete='CASCADE'), nullable=False, label='Vendor ID')
    sku = jb.Column(db.String(64), nullable=False, label='SKU')
    title = jb.Column(db.Text, label='Title')
    brand = jb.Column(db.Text, label='Brand')
    model = jb.Column(db.Text, label='Model')
    quantity = jb.Column(db.Integer, default=1, label='Quantity')
    quantity_desc = jb.Column(db.Text, label='Quantity Description')
    features = jb.Column(db.Text, label='Features')
    description = jb.Column(db.Text, label='Description')
    detail_url = jb.Column(URL, label='Detail page URL', format='url')
    image_url = jb.Column(URL, label='Image URL', format='url')
    last_modified = jb.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), label='Last modified')

    __table_args__ = (sa.UniqueConstraint('vendor_id', 'sku'),)

    # Pass-through properties
    price = detail_property('price', field=mmf.Decimal, label='Price')
    rank = detail_property('rank', field=mmf.Integer, label='Rank')
    rating = detail_property('rating', field=mmf.Float, label='Rating', format='percent')

    details = jb.relationship(
        'ListingDetails',
        order_by=ListingDetails.timestamp.asc(),
        back_populates='listing',
        passive_deletes=True,
        uselist=True,
        label='Detail history'
    )

    # Relationships
    vendor = jb.relationship('Vendor', back_populates='listings', label='Vendor')
    inventories = jb.relationship('Inventory', back_populates='listing', uselist=True, label='Inventories')
    inventory = jb.relationship(
        'Inventory',
        primaryjoin='and_(Inventory.listing_id == Listing.id, Inventory.owner_id == Listing.vendor_id)',
        uselist=False,
        label='Inventory'
    )

    class QuickResult(mm.Schema):
        id = mmf.Int()
        type = mmf.Str()
        title = mmf.Str(attribute='title')
        image = mmf.Str(attribute='image_url')
        description = mmf.Function(lambda obj: f'{obj.vendor.name if obj.vendor else obj.vendor_id} {obj.sku}')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.suppress_guessing = False
        if self.inventory is None:
            self.inventory = Inventory(listing=self, owner=self.vendor)
            db.session.add(self.inventory)

    def __repr__(self):
        vnd_name = self.vendor.name if self.vendor else None
        return f'<{type(self).__name__} {vnd_name} {self.sku}>'

    @sa.orm.reconstructor
    def __init_on_load__(self):
        self.suppress_guessing = False

    # Event handlers

    @classmethod
    def __declare_last__(cls):
        db.event.listen(flask_sqlalchemy.SignallingSession, 'before_flush', cls._maybe_guess_quantity)

    @staticmethod
    def _maybe_guess_quantity(session, context, instances):
        def should_guess(o):
            if isinstance(o, Listing) and not o.suppress_guessing:
                insp = db.inspect(o)
                return insp.attrs['title'].history.has_changes() or \
                       insp.attrs['quantity_desc'].history.has_changes()
            else:
                return False

        new_listings = [listing for listing in session.new if should_guess(listing)]
        mod_listings = [listing for listing in session.dirty if should_guess(listing)]

        for listing in new_listings + mod_listings:
            listing.guess_quantity()

    # Hybrid properties

    @sa.ext.hybrid.hybrid_property
    def estimated_cost(self):
        """The price plus tax and shipping, based on the vendor's averages."""
        if self.price is not None:
            tax = self.price * Decimal(self.vendor.avg_tax)
            shipping = self.price * Decimal(self.vendor.avg_shipping)
            return quantize_decimal(self.price + tax + shipping)

        return None

    @estimated_cost.expression
    def estimated_cost(cls):
        return db.select([
            db.cast(
                ListingDetails.price * (1 + Vendor.avg_shipping + Vendor.avg_tax),
                CURRENCY
            )
        ]).where(
            db.and_(
                ListingDetails.listing_id == cls.id,
                Vendor.id == cls.vendor_id
            )
        ).order_by(
            ListingDetails.timestamp.desc()
        ).limit(1).label('estimated_cost')

    @sa.ext.hybrid.hybrid_property
    def estimated_unit_cost(self):
        """The estimated cost divided by the listing quantity."""
        cost = self.estimated_cost
        if None in (cost, self.quantity):
            return None

        return cost / self.quantity

    @estimated_unit_cost.expression
    def estimated_unit_cost(cls):
        return cls.estimated_cost / cls.quantity

    def guess_quantity(self):
        """Guess listing quantity based on QuantityMap data."""
        if self.quantity_desc:
            qmap = QuantityMap.query.filter_by(text=self.quantity_desc).first()
            if qmap and self.quantity is None:
                self.quantity = qmap.quantity
            return

        elif self.quantity is None:
            all_qmaps = QuantityMap.query.order_by(
                db.func.char_length(QuantityMap.text).desc()
            ).all()

            for qmap in all_qmaps:
                if re.search(f'(\W|\A){qmap.text}(\W|\Z)', self.title, re.IGNORECASE):
                    self.quantity = qmap.quantity
                    self.quantity_desc = qmap.text
                    break
