import marshmallow as mm
import marshmallow.fields as mmf

from models import Vendor

from .common import db, OpsActor, search


########################################################################################################################


class ImportInventory(OpsActor):
    """Import a vendor's inventory from all other vendors."""
    public = True

    class Schema(mm.Schema):
        """Parameter schema for ImportInventory."""
        vendor_id = mmf.Int(required=True, title='Vendor ID')

    def perform(self, vendor_id=None):
        for vendor in Vendor.query.all():
            try:
                vendor.extension.send('ImportInventory', vendor_id=vendor_id)
            except (TypeError, ValueError, AttributeError):
                continue

        return vendor_id
