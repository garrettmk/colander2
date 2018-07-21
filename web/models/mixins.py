from sqlalchemy.ext.declarative import declared_attr
from flask_sqlalchemy import SignallingSession

from app import db, search


########################################################################################################################


class PolymorphicMixin:
    """Base class for extended models."""
    type = db.Column(db.String(64), nullable=False)

    @declared_attr
    def __mapper_args__(cls):
        return {
            'polymorphic_identity': cls.__name__,
            'polymorphic_on': cls.type
        }

    def __repr__(self):
        return f'<{type(self).__name__} {self.id}>'


########################################################################################################################


class SearchMixin:
    """A mixin that enables search indexing and a search function to work alongside SQLAlchemy."""
    __search_index__ = 'default'

    @classmethod
    def before_commit(cls, session):
        """Hold on to any searchable instances so that we can index them after the commit."""
        session._add_to_index = [obj for obj in session.new if isinstance(obj, cls)] + \
                                [obj for obj in session.dirty if isinstance(obj, cls)]
        session._remove_from_index = [obj for obj in session.deleted if isinstance(obj, cls)]

    @classmethod
    def after_commit(cls, session):
        """Add or remove objects from the search index."""
        for obj in session._add_to_index:
            search.add_to_index(obj)
        session._add_to_index = None

        for obj in session._remove_from_index:
            search.remove_from_index(obj)
        session._remove_from_index = None

    @classmethod
    def register_hooks(cls):
        db.event.listen(SignallingSession, 'before_commit', cls.before_commit)
        db.event.listen(SignallingSession, 'after_commit', cls.after_commit)

    @classmethod
    def search(cls, expression, page=1, per_page=10):
        hits, total = search.search(
            expression,
            index=cls.__search_index__,
            model_types=[cls] + cls.all_subclasses(),
            page=page,
            per_page=per_page
        )
        ids = [h['id'] for h in hits]
        whens = [(id, i) for i, id in enumerate(ids)]

        if hits:
            return cls.query.filter(cls.id.in_(ids)).order_by(db.case(whens, value=cls.id)), total
        else:
            return cls.query.filter_by(id=0), 0

    @classmethod
    def reindex(cls):
        search.reindex(cls)


SearchMixin.register_hooks()
