from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config
from search.search import ColanderSearch

from .models import Base, ColanderJSONEncoder


########################################################################################################################


app = Flask(__name__, static_folder='static/dist')
app.config.from_object(Config)
app.json_encoder = ColanderJSONEncoder

db = SQLAlchemy(model_class=Base)
db.init_app(app)

search = ColanderSearch()
search.init_app(app)


########################################################################################################################


