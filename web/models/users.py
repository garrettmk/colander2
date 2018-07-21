from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from .mixins import SearchMixin


########################################################################################################################


class User(db.Model, SearchMixin):
    """Tracks user name, email and password."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    human_name = db.Column(db.Text)
    password_hash = db.Column(db.Text, nullable=False)

    def __init__(self, *args, password=None, **kwargs):
        """Initialize the User."""
        super().__init__(*args, **kwargs)

        if password:
            self.set_password(password)

    def __repr__(self):
        return f'<{type(self).__name__} {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


