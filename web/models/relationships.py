import functools

from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from app import db
from core import CURRENCY
from .mixins import PolymorphicMixin
from .listings import Listing, ListingDetails


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


class Relationship(db.Model, PolymorphicMixin):
    """Describes a many-to-one relationship between listings."""
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id', ondelete='CASCADE'), nullable=False)

    listing = db.relationship('Listing')
    sources = db.relationship('RelationshipSource', back_populates='relationship')


########################################################################################################################


class RelationshipSource(db.Model, PolymorphicMixin):
    """A listing on the 'many' side of the relationship."""
    id = db.Column(db.Integer, primary_key=True)
    relationship_id = db.Column(db.Integer, db.ForeignKey('relationship.id', ondelete='CASCADE'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id', ondelete='CASCADE'), nullable=False)
    units = db.Column(CURRENCY, nullable=False, default=1)

    relationship = db.relationship('Relationship', back_populates='sources')
    listing = db.relationship('Listing')

    __table_args__ = (UniqueConstraint('relationship_id', 'listing_id'),)


########################################################################################################################


class Opportunity(Relationship):
    """A hypothetical vendor-to-market sales path."""
    id = db.Column(db.Integer, db.ForeignKey('relationship.id', ondelete='CASCADE'), primary_key=True)

    # TODO: Add generated column for similarity

    @hybrid_property
    def cost(self):
        try:
            return sum(
                s.listing.estimated_unit_cost * s.units
                for s in self.sources
            ) * self.listing.quantity if self.sources else None
        except TypeError:
            return None

    @cost.expression
    def cost(cls):
        l_alias = db.aliased(Listing)
        rsl_alias = db.aliased(Listing)
        rs_alias = db.aliased(RelationshipSource)

        return db.select([
            db.func.sum(
                rsl_alias.estimated_unit_cost * rs_alias.units * l_alias.quantity
            )
        ]).where(
            db.and_(
                rsl_alias.id == rs_alias.listing_id,
                rs_alias.relationship_id == cls.id,
                l_alias.id == cls.listing_id
            )
        ).having(
            db.func.every(rsl_alias.estimated_unit_cost != None)
        ).label('cost')

    @hybrid_property
    def profit(self):

        price = self.listing.price
        cost = self.cost

        try:
            selling_fees = self.listing.selling_fees or price * self.listing.vendor.avg_selling_fees
            return price - selling_fees - cost
        except TypeError:
            return None

    @profit.expression
    def profit(cls):
        ld_alias = db.aliased(ListingDetails)
        mld_alias = db.aliased(ListingDetails)
        revenue = db.select([
            ld_alias.price - mld_alias.selling_fees
        ]).where(
            db.and_(
                ld_alias.listing_id == cls.listing_id,
                mld_alias.id == ld_alias.id
            )
        ).order_by(
            ld_alias.timestamp.desc()
        ).limit(1).label('revenue')

        return revenue - cls.cost

    @hybrid_property
    def roi(self):
        try:
            return float(self.profit / self.cost)
        except TypeError:
            return None

    @roi.expression
    def roi(cls):
        return db.cast(
            cls.profit / cls.cost,
            db.Float
        )


########################################################################################################################


class OpportunitySource(RelationshipSource):
    """A source listing of an Opportunity."""
    id = db.Column(db.Integer, db.ForeignKey('relationship_source.id', ondelete='CASCADE'), primary_key=True)
    similarity = db.Column(db.Float)

    # TODO: add generated columns for cost


########################################################################################################################


# class InventoryConversion(Relationship):
#     """Information needed to convert one or more sku's into another. Used when creating multipacks, combo packs,
#     or when repackaging a SKU."""
#     id = db.Column(db.Integer, db.ForeignKey('relationship.id', ondelete='CASCADE'), primary_key=True)
#     cost = db.Column(CURRENCY)
#
#     @property
#     def units_per_dest(self):
#         """The total number of source units used in each conversion."""
#         return sum(s.units for s in self.sources)
#
#     @property
#     def min_source_units(self):
#         """The minimum number of units required from each source, in a tuple. Sources where `units` is None
#         will be expressed as None."""
#         return tuple(lcm(s.listing.quantity or 1, s.units) for s in self.sources)
#
#     @property
#     def total_units_per_batch(self):
#         """The total number of source units used in each batch."""
#         return lcm(self.units_per_dest, *self.min_source_units)
#
#     @property
#     def source_units_per_batch(self):
#         units_per_dest = self.units_per_dest
#         total_batch_units = self.total_units_per_batch
#
#         return tuple(total_batch_units * s.units // units_per_dest for s in self.sources)
#
#     @property
#     def batch_size(self):
#         """The number of destination units produced in each batch."""
#         return self.total_units_per_batch / self.units_per_dest
#
#     def convert(self, batches=1):
#         """Convert some or all of the source listings into the destination listing."""
#         required = tuple(units * batches for units in self.source_units_per_batch)
#         produced = self.batch_size * batches
#
#         # Check to make sure there is enough inventory to make the conversion
#         sufficient_inventory = tuple(s.listing.inventory.fulfillable or 0 >= r for s, r in zip(self.sources, required))
#         if False in sufficient_inventory:
#             raise Exception(f'Insufficient inventory.')
#
#         # Perform the conversion
#         produced_cost = 0
#         for source, req in zip(self.sources, required):
#             account = FinancialAccount.query.filter_by(
#                 owner_id=source.listing.vendor_id,
#                 name='Inventory Adjustments'
#             ).first() or FinancialAccount(
#                 owner_id=source.listing.vendor_id,
#                 name='Inventory Adjustments'
#             )
#             db.session.add(account)
#
#             total_cost, cost_ea = source.listing.inventory.calculate_cost()
#             adjustment = InventoryAdjustment(
#                 account=account,
#                 inventory=source.listing.inventory,
#                 quantity=-req,
#                 net=-cost_ea * req
#             )
#             db.session.add(adjustment)
#             source.listing.inventory.fulfillable -= req
#
#             produced_cost += cost_ea * req
#
#         account = FinancialAccount.query.filter_by(
#             owner_id=self.listing.vendor_id,
#             name='Inventory Adjustments'
#         ).first() or FinancialAccount(
#             owner_id=self.listing.vendor_id,
#             name='Inventory Adjustments'
#         )
#         db.session.add(account)
#
#         adjustment = InventoryAdjustment(
#             account=account,
#             inventory=self.listing.inventory,
#             quantity=produced,
#             net=produced_cost - (self.cost or 0) * produced
#         )
#         db.session.add(adjustment)
#         self.listing.inventory.fulfillable = (self.listing.inventory.fulfillable or 0) + produced
#
#     def revert(self, quantity=None):
#         """Revert some or all of the destination listings into source listings."""
#         raise NotImplementedError
#

########################################################################################################################


class OrderSiblings(Relationship):
    """Relates listings that are often ordered together."""
    id = db.Column(db.Integer, db.ForeignKey('relationship.id', ondelete='CASCADE'), primary_key=True)


########################################################################################################################


class OrderSibling(RelationshipSource):
    """Relates listings that are often ordered together."""
    id = db.Column(db.Integer, db.ForeignKey('relationship_source.id', ondelete='CASCADE'), primary_key=True)
    frequency = db.Column(db.Float)


########################################################################################################################


class SuggestedListings(Relationship):
    id = db.Column(db.Integer, db.ForeignKey('relationship.id', ondelete='CASCADE'), primary_key=True)


########################################################################################################################


class SuggestedListing(RelationshipSource):
    id = db.Column(db.Integer, db.ForeignKey('relationship_source.id', ondelete='CASCADE'), primary_key=True)
    similarity = db.Column(db.Float)
    frequency = db.Column(db.Float)

