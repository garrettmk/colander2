import os
basedir = os.path.abspath(os.path.dirname(__file__))

from core.models import ColanderJSONEncoder


########################################################################################################################


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI', 'postgresql://')

    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

    MWS_ACCESS_KEY = os.environ.get('MWS_ACCESS_KEY')
    MWS_SECRET_KEY = os.environ.get('MWS_SECRET_KEY')
    MWS_SELLER_ID = os.environ.get('MWS_SELLER_ID')
    PA_ACCESS_KEY = os.environ.get('PA_ACCESS_KEY')
    PA_SECRET_KEY = os.environ.get('PA_SECRET_KEY')
    PA_ASSOCIATE_TAG = os.environ.get('PA_ASSOCIATE_TAG')

    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL', 'http://localhost:9200')

    RESTFUL_JSON = {'cls': ColanderJSONEncoder}
