from flask import request
from flask_restful import Resource, reqparse
from webargs import fields, validate
from webargs.flaskparser import use_args
from app import db
from models import *


########################################################################################################################


class Objects(Resource):
    """Handles creation, deletion, and filtering of objects."""

    unaliased = {
        'vendor': Vendor,
        'listing': Listing,
        'inventory': Inventory,
        'order': Order,
    }

    def get(self, type_alias):
        """Filter objects of the given type using query string parameters."""
        args = request.args
        page = int(args.get('pageNum', 1))
        per_page = int(args.get('perPage', 10))
        attrs = args.getlist('getAttrs') or ['abbreviated']
        obj_type = self.unaliased[type_alias]
        filters = {
            a: args[a]
            for a in args if a not in ('getAttrs', 'pageNum', 'perPage')
        }

        query = obj_type.query.filter_by(**filters) if args else obj_type.query
        page = query.paginate(page=page, per_page=per_page)

        if attrs == ['all']:
            items = [m.as_json() for m in page.items]
        elif attrs == ['abbreviated']:
            items = [m.abbr_json() for m in page.items]
        else:
            items = [m.as_json(*attrs) for m in page.items]

        return {
            'total': page.total,
            'items': items
        }

    def post(self, type_alias):
        """Create an object using POST data."""
        data = dict(request.json)
        obj_type = self.unaliased[type_alias]

        obj = obj_type()
        obj.update(data)
        db.session.add(obj)
        db.session.commit()

        return {
            'status': 'ok',
            'id': obj.id
        }

    def delete(self, type_alias):
        """Delete objects specified in the DELETE data."""
        ids = request.json['ids']
        obj_type = self.unaliased[type_alias]

        try:
            obj_type.query.filter(obj_type.id.in_(ids)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {
                'status': 'error',
                'exception': type(e).__name__,
                'message': str(e)
            }

        return {
            'status': 'ok'
        }


########################################################################################################################


class Attributes(Resource):
    """Provides low-level get and set functionality for database models."""

    obj_types = {
        'vendor': Vendor,
        'listing': Listing,
        'qmap': QuantityMap
    }

    def get(self, type_alias, obj_id):
        attrs = [a for a in request.args] or ['abbreviated']

        obj_type = self.obj_types[type_alias]

        obj = obj_type.query.filter_by(id=obj_id).one()

        if attrs == ['abbreviated']:
            response = obj.abbr_json()
        elif attrs == ['all']:
            response = obj.as_json()
        else:
            response = obj.as_json(*attrs)

        return response

    def post(self, obj_type, obj_id):
        """Modify attributes on an object."""
        update = dict(request.json)
        obj_type = self.obj_types[obj_type]
        obj = obj_type.query.filter_by(id=obj_id).one()

        obj.update(update)
        db.session.commit()

        return {
            'status': 'ok'
        }
