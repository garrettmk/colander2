from importlib import import_module
from sqlalchemy.orm import reconstructor

from app import db
from .core import PolymorphicBase, UpdateMixin, URL

########################################################################################################################


class Entity(db.Model, PolymorphicBase, UpdateMixin):
    """Represents an owner of Listings (a vendor, market, or business) or a customer."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True)

    # Relationships
    accounts = db.relationship('FinancialAccount', back_populates='owner')
    financials = db.relationship('FinancialEvent', back_populates='originator')
    inventories = db.relationship('Inventory', back_populates='owner')

    orders_from = db.relationship(
        'Order',
        primaryjoin='Order.source_id == Entity.id',
        back_populates='source'
    )

    orders_to = db.relationship(
        'Order',
        primaryjoin='Order.dest_id == Entity.id',
        back_populates='destination'
    )

    def __repr__(self):
        return f'<{type(self).__name__} {self.name}>'


########################################################################################################################


class Customer(Entity):
    """A consumer of listings."""
    id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), primary_key=True)
    city = db.Column(db.Text)
    state = db.Column(db.String(2))
    zip = db.Column(db.String(10))


########################################################################################################################


class Vendor(Entity):
    """An owner of listings."""
    id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), primary_key=True)
    url = db.Column(URL, unique=True)
    avg_shipping = db.Column(db.Float, nullable=False, default=0)
    avg_tax = db.Column(db.Float, nullable=False, default=0)

    ext_module = db.Column(db.String(128))

    listings = db.relationship('Listing', back_populates='vendor', passive_deletes=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._extension = None

    @reconstructor
    def __init_on_load__(self):
        self._extension = None

    @property
    def extension(self):
        if self._extension:
            return self._extension
        elif self.ext_module is None:
            return None

        try:
            self._extension = import_module('ext.' + self.ext_module)
        except ModuleNotFoundError:
            self._extension = None

        return self._extension


########################################################################################################################
