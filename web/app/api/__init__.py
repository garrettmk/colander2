from flask_restful import Api
from .search import TextSearch, QuickSearch
from .objects import ObjectFilter, ObjectCreator, ObjectUpdater, ObjectDeleter
from .tasks import Tasks


########################################################################################################################


def ColanderAPI(*args, **kwargs):
    api = Api(*args, **kwargs)

    api.add_resource(TextSearch, '/search')
    api.add_resource(QuickSearch, '/quick')
    api.add_resource(Tasks, '/tasks')

    api.add_resource(ObjectFilter, '/<type_alias>/filter')
    api.add_resource(ObjectCreator, '/<type_alias>/create')
    api.add_resource(ObjectUpdater, '/<type_alias>/update')
    api.add_resource(ObjectDeleter, '/<type_alias>/delete')

    return api
