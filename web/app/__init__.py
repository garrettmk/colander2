from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from search.search import ColanderSearch

from app.core import bp as core_bp


########################################################################################################################


db = SQLAlchemy()
search = ColanderSearch()


def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static/dist')
    app.config.from_object(config_class)

    app.register_blueprint(core_bp)

    db.init_app(app)
    search.init_app(app)

    from app.api import api
    api.init_app(app)

    return app


########################################################################################################################


