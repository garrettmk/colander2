from importlib import import_module
from sqlalchemy.orm import reconstructor

from app import db
from .core import PolymorphicBase, UpdateMixin, SearchMixin, URL

########################################################################################################################


class Entity(db.Model, PolymorphicBase, UpdateMixin, SearchMixin):
    """Represents an owner of Listings (a vendor, market, or business) or a customer."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True)

    # Relationships
    accounts = db.relationship('FinancialAccount', back_populates='owner', lazy='dynamic')
    financials = db.relationship('FinancialEvent', back_populates='originator')
    inventories = db.relationship('Inventory', back_populates='owner')

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

    # Config
    __search_fields__ = ['name']
    __extended__ = ['accounts', 'orders_from', 'orders_to']

    def __repr__(self):
        return f'<{type(self).__name__} {self.name}>'

    def encode_attribute(self, attr):
        if attr == 'orders_from':
            return {
                'total': self.orders_from.count(),
                'orders': [o.abbr_json() for o in self.orders_from.limit(10).all()]
            }

        elif attr == 'orders_to':
            return {
                'total': self.orders_to.count(),
                'orders': [o.abbr_json() for o in self.orders_to.limit(10).all()]
            }

        elif attr == 'accounts':
            return {
                'total': self.accounts.count(),
                'accounts': [a.abbr_json() for a in self.accounts.limit(10).all()]
            }

        return super().encode_attribute(attr)


########################################################################################################################


class Customer(Entity):
    """A consumer of listings."""
    id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), primary_key=True)
    city = db.Column(db.Text)
    state = db.Column(db.String(2))
    zip = db.Column(db.String(10))

    __search_fields__ = Entity.__search_fields__ + ['city']


########################################################################################################################


class Vendor(Entity):
    """An owner of listings."""
    id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), primary_key=True)
    url = db.Column(URL, unique=True)
    avg_shipping = db.Column(db.Float, nullable=False, default=0)
    avg_tax = db.Column(db.Float, nullable=False, default=0)

    ext_module = db.Column(db.String(128))

    listings = db.relationship('Listing', back_populates='vendor', passive_deletes=True, lazy='dynamic')

    __search_fields__ = Entity.__search_fields__ + ['url']
    __abbreviated__ = ['id', 'name', 'url']
    __extended__ = Entity.__extended__ + ['extension', 'listings']

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
        except ModuleNotFoundError as e:
            print(e)
            self._extension = None

        return self._extension

    def encode_attribute(self, attr):
        if attr == 'extension':
            if self.extension:
                return [
                    x for x in dir(self.extension)
                    if not x.startswith('__') or type(getattr(self.extension, x)) is type(self.extension)
                ]
            else:
                return []

        elif attr == 'listings':
            return {
                'total': self.listings.count(),
                'listings': [l.abbr_json() for l in self.listings.limit(10).all()]
            }

        return super().encode_attribute(attr)


########################################################################################################################

