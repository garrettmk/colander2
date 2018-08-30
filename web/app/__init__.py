from flask import render_template

from core import app, db, search
from .api import ColanderAPI


########################################################################################################################


# We're doing a single-page app with ReactJS, so we only need to install a default route
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return render_template('index.html')


api = ColanderAPI(prefix='/api')
api.init_app(app)


########################################################################################################################


