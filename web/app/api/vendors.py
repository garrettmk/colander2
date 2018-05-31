from flask import request
from flask_restful import Resource

from models import Vendor
from tasks.broker import setup_dramatiq
setup_dramatiq()


########################################################################################################################


class VendorActions(Resource):

    def post(self, vendor_id, action):
        """Execute a vendor extension action."""
        vendor = Vendor.query.filter_by(id=vendor_id).one()
        data = request.json

        try:
            m = getattr(vendor.extension, action).send(**data)
        except Exception as e:
            return {
                'status': 'error',
                'exception': repr(e),
                'message': str(e)
            }

        return {
            'status': 'ok',
            'id': m.message_id,
        }
