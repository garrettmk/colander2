from marshmallow import fields, Schema

from app import db
from core import URL, JSONB

from .mixins import PolymorphicMixin, SearchMixin


########################################################################################################################


class Entity(db.Model, PolymorphicMixin, SearchMixin):
    """Represents an owner of Listings (a vendor, market, or business) or a customer."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    image_url = db.Column(db.Text)

    # Relationships
    accounts = db.relationship('FinancialAccount', back_populates='owner', lazy='dynamic')
    financials = db.relationship('FinancialEvent', back_populates='originator')
    inventories = db.relationship('Inventory', back_populates='owner', lazy='dynamic')

    orders_from = db.relationship(
        'Order',
        primaryjoin='Order.source_id == Entity.id',
        back_populates='source',
        lazy='dynamic'
    )

    orders_to = db.relationship(
        'Order',
        primaryjoin='Order.dest_id == Entity.id',
        back_populates='destination',
        lazy='dynamic'
    )

    class QuickResult(Schema):
        id = fields.Int()
        type = fields.Str()
        title = fields.Str(attribute='name')
        image = fields.Str(attribute='image_url')

    def __repr__(self):
        return f'<{type(self).__name__} {self.name}>'


########################################################################################################################


class Customer(Entity):
    """A consumer of listings."""
    id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), primary_key=True)
    email = db.Column(db.Text, unique=True)
    city = db.Column(db.Text)
    state = db.Column(db.String(2))
    zip = db.Column(db.String(10))

    class QuickResults(Schema):
        description = fields.Function(func=lambda m: f'{m.city}, {m.state} {m.zip}')


########################################################################################################################


class Vendor(Entity):
    """An owner of listings."""
    id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), primary_key=True)
    url = db.Column(URL, unique=True)
    avg_shipping = db.Column(db.Float, nullable=False, default=0)
    avg_tax = db.Column(db.Float, nullable=False, default=0)
    ext_id = db.Column(db.Integer, db.ForeignKey('extension.id'))

    ext = db.relationship('Extension')
    listings = db.relationship('Listing', back_populates='vendor', passive_deletes=True, lazy='dynamic')

    class QuickResult(Schema):
        description = fields.Str(attribute='url')
