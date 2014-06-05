"""Query tools."""
from .errors import QueryError
from collections import OrderedDict
from copy import deepcopy


scalar_comparisons = {'$gt', '$gte', '$lt', '$lte', '$ne'}
list_comparisons = {'$in', '$nin'}
comparisons = scalar_comparisons | list_comparisons


class Query(object):
    """A query abstracts a MongoDB query."""

    def __init__(self, criteria):
        """Initialize the query with the provided criteria."""
        if not isinstance(criteria, OrderedDict):
            criteria = OrderedDict(criteria)
        self.criteria = criteria

    def copy(self):
        """Return a copy of the query."""
        return Query(deepcopy(self.criteria))

    def _encode_field(self, document, field, name, value):
        """Return an encoded field."""
        if isinstance(value, dict) and len(value) == 1 and value.keys()[0] in comparisons:
            comparison = value.keys()[0]
            value = value[comparison]
            if comparison in list_comparisons:
                encoded = []
                for item in value:
                    if item is not None:
                        item = field.encode(document, name, item)
                    encoded.append(item)
                value = encoded
            else:
                if value is not None:
                    value = field.encode(document, name, value)
            value = OrderedDict([(comparison, value)])
        else:
            value = field.encode(document, name, value)
        return value

    def _encode(self, document, criteria):
        """Return the encoded criteria."""
        encoded = OrderedDict()
        for name, value in criteria.iteritems():
            field = document._meta.fields.get(name)
            if field:
                encoded[name] = self._encode_field(document, field, name, value)
            elif isinstance(value, dict):
                encoded[name] = self._encode(document, value)
            elif isinstance(value, (tuple, list, set)):
                encoded[name] = [self._encode(document, item) for item in value]
        return encoded

    def encode(self, document):
        """Return the encoded query in the context of the given document."""
        return self._encode(document, self.criteria)

    def _op(self, op, query):
        """Combine two queries with an operator and return the resulting query."""
        if len(self.criteria) == 0:
            return query.copy()
        if len(query.criteria) == 0:
            return self.copy()
        if len(self.criteria) == 1 and op in self.criteria:
            criteria = deepcopy(self.criteria)
            criteria[op].append(deepcopy(query.criteria))
            return Query(criteria)
        else:
            criteria = [(op, [deepcopy(self.criteria), deepcopy(query.criteria)])]
            return Query(criteria)

    def negate(self):
        """Negate a query."""
        if len(self.criteria) == 0:
            return self.copy()
        if len(self.criteria) == 1 and '$not' in self.criteria:
            return Query(deepcopy(self.criteria['$not']))
        else:
            return Query({'$not': deepcopy(self.criteria)})

    def nor(self, query):
        """Nor this query with another and return the resulting query."""
        return self._op('$nor', query)

    def __and__(self, query):
        """Logical and. Calls qand()."""
        return self._op('$and', query)

    def __or__(self, query):
        """Logical or. Calls qor()."""
        return self._op('$or', query)


Q = Query
