from elasticsearch import Elasticsearch


########################################################################################################################


class ColanderSearch:
    """Provides text-search functionality."""

    default_index = 'default'

    def __init__(self, app=None):
        self.es = None
        self._template = False

        if app:
            self.init_app(app)

    def init_app(self, app):
        self.es = Elasticsearch(app.config['ELASTICSEARCH_URL'])

    def _setup_template(self):
        index_template = {
            'index_patterns': '*',
            'mappings': {
                'model': {
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

    def add_to_index(self, model, index=None):
        """Add a model to an index."""
        if not self._template:
            self._setup_template()

        index = index or getattr(model, '__search_index__', None) or self.default_index
        model_type = type(model)
        payload = {
            field: getattr(model, field)
            for field in model.__search_fields__ if getattr(model, field) is not None
        }
        payload['__model_type__'] = model_type.full_name()

        self.es.index(
            index=index,
            doc_type='model',
            id=model.id,
            body=payload
        )

    def remove_from_index(self, model, index=None):
        """Remove a model from an index."""
        index = index or getattr(model, '__search_index__', None) or self.default_index
        self.es.delete(
            index=index,
            doc_type='model',
            id=model.id
        )

    def reindex(self, cls, index=None):
        """Re-index all objects of the given class."""
        index = index or getattr(index, '__search_index__', None) or self.default_index
        body = {
            'query': {
                'bool': {
                    'must': {'match_all': {}},
                    'filter': {'terms': {'__model_type__': [mt.full_name() for mt in cls.all_subclasses()]}}
                }
            }
        }

        self.es.delete_by_query(index=index, doc_type='model', body=body, ignore=404)

        for obj in cls.query.all():
            self.add_to_index(obj, index)

    def delete_index(self, index=None):
        """Delete an entire index."""
        index = index or getattr(index, '__search_index__', None) or self.default_index
        self.es.indices.delete(index=index, ignore=400)

    def _search(self, query, index=None, model_types=None, min_score=None, page=1, per_page=10):
        index = index if isinstance(index, str) else getattr(index, '__search_index__', None) or self.default_index
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

        results = self.es.search(index=index, doc_type='model', body=body)
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

        index = kwargs.pop('index', None) or getattr(listing, '__search_index__', self.default_index)
        model_types = kwargs.pop('model_types', [type(listing), *type(listing).all_subclasses()])

        return self._search(query, index=index, model_types=model_types, **kwargs)
