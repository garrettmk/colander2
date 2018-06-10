from flask import request
from flask_restful import Resource
from webargs import fields, validate
from webargs.flaskparser import use_kwargs
from marshmallow import Schema, post_load

from app import db
from models import Inventory, Listing
from .common import model_types


########################################################################################################################


class GetInventory(Resource):
    """Handles inventory-related requests."""

    class GetInventorySchema(Schema):
        owner_id = fields.Int(required=True)
        filter = fields.Str(validate=validate.OneOf(('all', 'own', 'foreign')), missing='all')
        getAttrs = fields.List(fields.Str(), missing=['abbreviated'])
        pageNum = fields.Int(missing=1)
        perPage = fields.Int(missing=10)

        class Meta:
            strict = True

    @use_kwargs(GetInventorySchema)
    def get(self, owner_id, filter, getAttrs, pageNum, perPage):
        q = Inventory.query.filter_by(owner_id=owner_id)

        if filter == 'own':
            q = q.join(Listing).filter(Listing.vendor_id == owner_id)
        elif filter == 'foreign':
            q = q.join(Listing).filter(Listing.vendor_id != owner_id)

        page = q.paginate(page=pageNum, per_page=perPage)

        if getAttrs == ['all']:
            items = [m.as_json() for m in page.items]
        elif getAttrs == ['abbreviated']:
            items = [m.abbr_json() for m in page.items]
        else:
            items = [m.as_json(*getAttrs) for m in page.items]

        return {
            'total': page.total,
            'page': page.page,
            'pages': page.pages,
            'per_page': page.per_page,
            'items': items
        }
