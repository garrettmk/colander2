from webargs import fields
from webargs.flaskparser import use_kwargs
from marshmallow import Schema
from marshmallow_jsonschema import JSONSchema

from models import Extension, Task
from tasks.broker import setup_dramatiq
setup_dramatiq()

from .common import ColanderResource


########################################################################################################################


def make_start_schema(request):
    if 'id' in request.args:
        opt = {'only': ('id',)}
    else:
        opt = {'exclude': ('id',)}

    return Tasks.StartSchema(**opt, context={'request': request})


class Tasks(ColanderResource):
    """Task-related API."""

    class StartSchema(Schema):
        id = fields.Int()
        ext_id = fields.Int(missing=None)
        action = fields.Str(required=True)
        params = fields.Dict(missing=dict)

        class Meta:
            strict = True

    @use_kwargs(make_start_schema)
    def post(self, id=None, ext_id=None, action=None, params=None):
        """Start a task using the POST data."""
        if id:
            task = Task.query.filter_by(id=id).one()
            return task.send()
        else:
            if ext_id:
                ext = Extension.query.filter_by(id=ext_id).one()
            else:
                ext = Extension.query.filter_by(module='core').one()

            return ext.send(action, **params)
