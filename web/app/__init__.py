from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

from core import Base, ColanderJSONEncoder
from config import Config
from search.search import ColanderSearch


########################################################################################################################


db = SQLAlchemy(model_class=Base)
search = ColanderSearch()


def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static/dist')
    app.config.from_object(config_class)
    app.json_encoder = ColanderJSONEncoder

    # We're doing a single-page app with ReactJS, so we only need to install a default route
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def index(path):
        return render_template('index.html')


    db.init_app(app)
    search.init_app(app)

    from .api import ColanderAPI
    api = ColanderAPI(prefix='/api')
    api.init_app(app)

    return app


########################################################################################################################


