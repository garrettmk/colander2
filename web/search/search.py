import elasticsearch as es

import core


########################################################################################################################


class ColanderSearch:
    """Provides text-search functionality."""

    def __init__(self, app=None):
        self.es = None
        self._template = False

        if app:
            self.init_app(app)

    def init_app(self, app):
        self.es = es.Elasticsearch(app.config['ELASTICSEARCH_URL'])

    def _setup_template(self):
        index_template = {
            'index_patterns': '*',
            'mappings': {
                'doc': {
                    'properties': {
                        '__model_type__': {
                            'type': 'keyword'
                        }
                    }
                }
            }
        }

        self.es.indices.put_template(name='models_template', body=index_template)
        self._template = True

    def _index(self, model_or_type):
        """Return the index name for the given model."""
        try:
            index = getattr(model_or_type, '__search_index__')
        except AttributeError:
            model_type = model_or_type if isinstance(model_or_type, type) else type(model_or_type)
            index = f'{model_type.__name__.lower()}_index'
            model_type.__search_index__ = index

        return index

    def add_to_index(self, model):
        """Add a model its index."""
        if not self._template:
            self._setup_template()

        payload = {
            field: getattr(model, field)
            for field in model.__search_fields__ if getattr(model, field) is not None
        }
        payload['__model_type__'] = type(model).full_name()

        self.es.index(
            index=self._index(model),
            doc_type='doc',
            id=model.id,
            body=payload
        )

    def remove_from_index(self, model):
        """Remove a model from an index."""
        self.es.delete(
            index=self._index(model),
            doc_type='doc',
            id=model.id
        )

    def reindex(self, cls):
        """Re-index all objects of the given class."""
        indexes = ','.join(set(self._index(sub) for sub in cls.all_subclasses()))
        body = {
            'query': {
                'bool': {
                    'must': {'match_all': {}},
                    'filter': {'terms': {'__model_type__': [mt.full_name() for mt in cls.all_subclasses()]}}
                }
            }
        }

        self.es.delete_by_query(index=indexes, doc_type='doc', body=body, ignore=404)

        for obj in cls.query.all():
            self.add_to_index(obj)

    def delete_index(self, model_or_type):
        """Delete an entire index."""
        index = self._index(model_or_type)
        self.es.indices.delete(index=index, ignore=400)

    def _search(self, query, model_types=None, min_score=None, page=1, per_page=10):
        indexes = '_all' #','.join(set([self._index(mt) for mt in model_types]))
        query_filter = query.pop('filter', [])
        if model_types:
            body = {
                'query': {
                    'bool': {
                        'filter': [{'terms': {'__model_type__': [mt.full_name() for mt in model_types]}}] \
                                  + (query_filter if isinstance(query_filter, list) else [query_filter]),
                        **query
                    }
                }
            }
        else:
            body = {
                'query': query
            }

        if min_score:
            body['min_score'] = min_score

        body['from'] = (page - 1) * per_page
        body['size'] = per_page
        body['_source'] = ['__model_type__']

        results = self.es.search(index=indexes, doc_type='doc', body=body)
        total = results['hits']['total']
        max_score = results['hits']['max_score']
        hits = [
            {
                'score': h['_score'],
                'n_score': h['_score'] / max_score if max_score else None,
                'id': h['_id'],
                'type': h['_source']['__model_type__']
            } for h in results['hits']['hits']
        ]

        return hits, total

    def search(self, query, **kwargs):
        """Get a list of models that match the query."""
        query = {
            'must': [
                {
                    'multi_match': {
                        'query': query,
                        'fields': ['*']
                    }
                }
            ]
        }

        return self._search(query, **kwargs)

    def find_similar(self, model, **kwargs):
        """Find objects similar to the given model."""
        model_type = type(model)
        query = model.similarity_query()
        model_types = kwargs.pop('model_types', model_type.all_subclasses())

        return self._search(query, model_types=model_types, **kwargs)

    def find_matching_listings(self, listing, **kwargs):
        """Find listings for the same type of product."""
        brand_match = {
            'multi_match': {
                'query': listing.brand,
                'fuzziness': 'AUTO',
                'fields': ['brand^2', 'title']
            }
        } if listing.brand else None

        model_match = {
            'multi_match': {
                'query': listing.model,
                'fuzziness': 'AUTO',
                'fields': ['model^3', 'title']
            }
        } if listing.model else None

        title_match = {
            'multi_match': {
                'query': listing.title,
                'fuzziness': 'AUTO',
                'fields': ['brand^2', 'model^3', 'title']
            }
        } if listing.title is not None else None

        if model_match:
            must = [model_match]
            should = [m for m in (brand_match, title_match) if m is not None]
        elif brand_match:
            must = [brand_match]
            should = [title_match] if title_match else []
        elif title_match:
            must = [title_match]
            should = []
        else:
            return []

        query = {k: v for k, v in {
            'must': must,
            'should': should,
            'must_not': [{'ids': {'values': [listing.id]}}],
        }.items() if v}

        model_types = kwargs.pop('model_types', type(listing).all_subclasses())

        return self._search(query, model_types=model_types, **kwargs)
