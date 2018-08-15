from flask_restful import Api
from .search import TextSearch, QuickSearch
from .objects import ObjectSchema, ObjectFilter, ObjectCreator, ObjectUpdater, ObjectDeleter
from .tasks import Tasks


########################################################################################################################


def ColanderAPI(*args, **kwargs):
    api = Api(*args, **kwargs)

    api.add_resource(TextSearch, '/search')
    api.add_resource(QuickSearch, '/preview')
    api.add_resource(Tasks, '/tasks')

    api.add_resource(ObjectSchema, '/<type_>/schema')
    api.add_resource(ObjectFilter, '/<type_>/filter')
    api.add_resource(ObjectCreator, '/<type_>/create')
    api.add_resource(ObjectUpdater, '/<type_>/update')
    api.add_resource(ObjectDeleter, '/<type_>/delete')

    return api
