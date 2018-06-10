from datetime import datetime

from app import db
from .core import PolymorphicMixin, UpdateMixin, SearchMixin, CURRENCY


########################################################################################################################


class FinancialAccount(db.Model, UpdateMixin, SearchMixin):
    """A collection of FinancialEvenets."""
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('entity.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(64))

    owner = db.relationship('Entity', back_populates='accounts')
    events = db.relationship('FinancialEvent', back_populates='account', passive_deletes=True)

    __search_fields__ = ['name']

    def __repr__(self):
        owner_name = self.owner.name if self.owner else None
        return f'<{type(self).__name__} {owner_name} {self.name}>'

    @property
    def balance(self):
        return sum(e.net for e in self.events)


########################################################################################################################


class FinancialEvent(db.Model, PolymorphicMixin, UpdateMixin, SearchMixin):
    """Represents a financial event, like a debit or credit."""
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('financial_account.id', ondelete='CASCADE'), nullable=False)
    originator_id = db.Column(db.Integer, db.ForeignKey('entity.id'))

    date = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    net = db.Column(CURRENCY)
    description = db.Column(db.Text)

    account = db.relationship('FinancialAccount', back_populates='events')
    originator = db.relationship('Entity', back_populates='financials')

    __search_fields__ = ['description']


    def __repr__(self):
        return f'<{type(self).__name__} {self.net} {self.description}>'


########################################################################################################################


class OrderEvent(FinancialEvent):
    """An order-level financial event."""
    id = db.Column(db.Integer, db.ForeignKey('financial_event.id', ondelete='CASCADE'), primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    order = db.relationship('Order', back_populates='financials')

    def __repr__(self):
        order_number = self.order.order_number if self.order else None
        return f'<{type(self).__name__} {self.id}: ${self.net} {order_number}'


########################################################################################################################


class OrderItemEvent(FinancialEvent):
    """An order-item-level financial event."""
    id = db.Column(db.Integer, db.ForeignKey('financial_event.id', ondelete='CASCADE'), primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('order_item.id'))
    item = db.relationship('OrderItem', back_populates='financials')

    def __repr__(self):
        if self.item:
            return f'<{type(self).__name__} {self.id}: ${self.net} {self.item.quantity} x {self.item.source.listing.sku}>'
        else:
            return f'<{type(self).__name__} {self.id}: ${self.net}>'


########################################################################################################################


class InventoryAdjustment(FinancialEvent):
    """An inventory adjustment."""
    id = db.Column(db.Integer, db.ForeignKey('financial_event.id', ondelete='CASCADE'), primary_key=True)
    inv_id = db.Column(db.Integer, db.ForeignKey('inventory.id', ondelete='RESTRICT'), nullable=False)
    inventory = db.relationship('Inventory', back_populates='adjustments')

    quantity = db.Column(db.Integer)

    def __repr__(self):
        if self.inventory:
            return f'<{type(self).__name__} ${self.net} {self.quantity}x {self.inventory.owner.name} {self.inventory.listing.sku}>'
        else:
            return f'<{type(self).__name__} ${self.net} {self.quantity}x >'

