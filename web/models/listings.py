import re
from datetime import datetime
from decimal import Decimal
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import reconstructor
from sqlalchemy.ext.hybrid import hybrid_property
from flask_sqlalchemy import SignallingSession

from app import db, search
from .core import PolymorphicBase, UpdateMixin, SearchMixin, URL, CURRENCY, quantize_decimal
from .entities import Vendor
from .orders import Inventory, InventoryDetails

########################################################################################################################


def detail_property(name):
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

    return hybrid_property(fget=getter, fset=setter, expr=expr)


def inventory_property(name):
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

    return hybrid_property(fget=getter, fset=setter, expr=expr)


########################################################################################################################


class QuantityMap(db.Model):
    """A mapping of a quantity and its textual representation."""
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    text = db.Column(db.String(64), nullable=False, unique=True)

    def __repr__(self):
        return f'<QuantityMap {self.text} = {self.quantity}>'

    @classmethod
    def __declare_last__(cls):
        db.event.listen(SignallingSession, 'before_flush',cls._maybe_update_products)

    @staticmethod
    def _maybe_update_products(session, context, instances):
        qmaps = [obj for obj in session.new if isinstance(obj, QuantityMap)] +\
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


class ListingDetails(db.Model, PolymorphicBase, UpdateMixin):
    """Contains a Listing's transient details, like price, rank, rating, etc."""
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    price = db.Column(CURRENCY)
    rank = db.Column(db.Integer)
    rating = db.Column(db.Float)

    listing = db.relationship('Listing', back_populates='details')

    __table_args__ = (UniqueConstraint('timestamp', 'listing_id'),)


########################################################################################################################


class Listing(db.Model, PolymorphicBase, UpdateMixin, SearchMixin):
    """A description of a product for sale."""
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id', ondelete='CASCADE'), nullable=False)
    sku = db.Column(db.String(64), nullable=False)
    title = db.Column(db.Text)
    brand = db.Column(db.Text)
    model = db.Column(db.Text)
    quantity = db.Column(db.Integer, default=1)
    quantity_desc = db.Column(db.Text)
    features = db.Column(db.Text)
    description = db.Column(db.Text)
    detail_url = db.Column(URL)
    image_url = db.Column(URL)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow())

    __table_args__ = (UniqueConstraint('vendor_id', 'sku'),)
    __search_fields__ = ['sku', 'title', 'brand', 'model', 'features', 'description']
    __search_index__ = 'listings'

    # Pass-through properties
    price = detail_property('price')
    rank = detail_property('rank')
    rating = detail_property('rating')

    details = db.relationship(
        'ListingDetails',
        order_by=ListingDetails.timestamp.asc(),
        back_populates='listing',
        passive_deletes=True
    )

    # Relationships
    vendor = db.relationship('Vendor', back_populates='listings')
    inventories = db.relationship('Inventory', back_populates='listing')
    inventory = db.relationship(
        'Inventory',
        primaryjoin='and_(Inventory.listing_id == Listing.id, Inventory.owner_id == Listing.vendor_id)',
        uselist=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.suppress_guessing = False
        if self.inventory is None:
            self.inventory = Inventory(listing=self, owner=self.vendor)
            db.session.add(self.inventory)

    def __repr__(self):
        vnd_name = self.vendor.name if self.vendor else None
        return f'<{type(self).__name__} {vnd_name} {self.sku}>'

    @reconstructor
    def __init_on_load__(self):
        self.suppress_guessing = False

    # Event handlers

    @classmethod
    def __declare_last__(cls):
        db.event.listen(SignallingSession, 'before_flush', cls._maybe_guess_quantity)

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

    @hybrid_property
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

    @hybrid_property
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


########################################################################################################################
