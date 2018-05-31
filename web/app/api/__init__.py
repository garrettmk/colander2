from flask_restful import Api, Resource
from .vendors import VendorActions
from .search import TextSearch
from .objects import Objects, Attributes
from .tasks import Tasks


########################################################################################################################

"""
/search?
/<obj_type>
    GET - Filter
    POST - Create object
    DELETE - Delete object

/<obj_type>/<obj_id>
    GET - Get attributes
    POST - Set attributes
      

"""



api = Api(prefix='/api')

api.add_resource(TextSearch, '/search')
api.add_resource(Objects, '/obj/<type_alias>')
api.add_resource(Attributes, '/obj/<type_alias>/<int:obj_id>')
api.add_resource(VendorActions, '/obj/vendor/<int:obj_id>/<action>')

api.add_resource(Tasks, '/tasks')
