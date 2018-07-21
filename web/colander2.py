from pprint import pprint
from app import create_app, db, search
app = create_app()


########################################################################################################################


@app.shell_context_processor
def make_shell_context():

    def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]

    models = {m.__name__: m for m in all_subclasses(db.Model)}
    return {
        'pprint': pprint,
        'app': app,
        'db': db,
        'search': search,
        **models
    }
