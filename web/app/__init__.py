from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from search.search import ColanderSearch


########################################################################################################################


db = SQLAlchemy()
search = ColanderSearch()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    search.init_app(app)
    return app


########################################################################################################################


from app import routes