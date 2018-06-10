from flask import request
from flask_restful import Resource

from webargs import fields
from webargs.flaskparser import use_kwargs
from marshmallow import Schema

from models import Task
from tasks.broker import setup_dramatiq
setup_dramatiq()

from .common import format_response


########################################################################################################################


def make_start_schema(request):
    if 'id' in request.args:
        opt = {'only': ('id',)}
    else:
        opt = {'exclude': ('id',)}

    return Tasks.StartSchema(**opt, context={'request': request})


class Tasks(Resource):
    """Task-related API."""
    method_decorators = [format_response]

    class StartSchema(Schema):
        id = fields.Int(required=True)
        module = fields.Str(required=True)
        action = fields.Str(required=True)
        args = fields.List(fields.Raw(), missing=list)
        kwargs = fields.Dict(missing=dict)
        options = fields.Dict(missing=dict)

        class Meta:
            strict = True

    @use_kwargs(make_start_schema)
    def post(self, id=None, module=None, action=None, args=None, kwargs=None, options=None):
        """Start a task using the POST data."""
        task = Task.query.filter_by(id=id).first()\
               or Task(module=module, action=action, args=args, kwargs=kwargs, options=options)

        return task.send()

