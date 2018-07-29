import marshmallow as mm
import marshmallow.fields as mmf
import sqlalchemy_jsonbase as jb

from app import db
from core import URL, JSONB

from .mixins import PolymorphicMixin, SearchMixin


########################################################################################################################


class Entity(db.Model, PolymorphicMixin, SearchMixin):
    """Represents an owner of Listings (a vendor, market, or business) or a customer."""
    id = jb.Column(db.Integer, primary_key=True, label='Entity ID')
    name = jb.Column(db.Text, unique=True, nullable=False, label='Entity name')
    image_url = jb.Column(db.Text, label='Image URL', format='url')

    # Relationships
    accounts = jb.relationship('FinancialAccount', back_populates='owner', uselist=True, lazy='dynamic', label='Accounts')
    financials = jb.relationship('FinancialEvent', back_populates='originator', uselist=True, lazy='dynamic', label='Financial events')
    inventories = jb.relationship('Inventory', back_populates='owner', uselist=True, lazy='dynamic', label='Inventories')

    orders_from = jb.relationship(
        'Order',
        primaryjoin='Order.source_id == Entity.id',
        back_populates='source',
        uselist=True,
        lazy='dynamic',
        label='Fulfilled orders'
    )

    orders_to = jb.relationship(
        'Order',
        primaryjoin='Order.dest_id == Entity.id',
        back_populates='destination',
        uselist=True,
        lazy='dynamic',
        label='Received orders'
    )

    class Preview(mm.Schema):
        id = mmf.Int()
        type = mmf.Str()
        title = mmf.Str(attribute='name')
        image = mmf.Str(attribute='image_url')

    def __repr__(self):
        return f'<{type(self).__name__} {self.name}>'


########################################################################################################################


class Customer(Entity):
    """A consumer of listings."""
    id = jb.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), primary_key=True, label='Customer ID')
    email = jb.Column(db.Text, unique=True, label='Email', format = 'email')
    city = jb.Column(db.Text, label='City')
    state = jb.Column(db.String(2), label='State')
    zip = jb.Column(db.String(10), label='Zip/postal code')

    class Preview(mm.Schema):
        id = mmf.Int()
        type = mmf.Str()
        title = mmf.Str(attribute='name')
        description = mmf.Function(func=lambda m: f'{m.email}\n' if m.email else '' + f'{m.city}, {m.state} {m.zip}')

    def __repr__(self):
        return f'<{type(self).__name__} {self.name or self.email}>)'


########################################################################################################################


class Vendor(Entity):
    """An owner of listings."""
    id = jb.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), primary_key=True, label='Vendor ID')
    url = jb.Column(URL, unique=True, label='Website', format='url')
    avg_shipping = jb.Column(db.Float, nullable=False, default=0, label='Avg. shipping', format='percent')
    avg_tax = jb.Column(db.Float, nullable=False, default=0, label='Avg. tax', format='percent')
    ext_id = jb.Column(db.Integer, db.ForeignKey('extension.id'), label='Extension ID')

    ext = jb.relationship('Extension', label='Extension')
    listings = jb.relationship('Listing', back_populates='vendor', passive_deletes=True, uselist=True, lazy='dynamic', label='Listings')

    class Preview(mm.Schema):
        id = mmf.Int()
        type = mmf.Str()
        title = mmf.Str(attribute='name')
        description = mmf.Str(attribute='url')
        image = mmf.Str(attribute='image_url')
        url = mmf.URL()
