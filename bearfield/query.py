"""Query tools."""
from collections import OrderedDict
from copy import deepcopy


class QueryEncoder(object):
    """Encode query specs."""
    scalars = {
        '$gt',
        '$gte',
        '$lt',
        '$lte',
        '$ne',
    }

    lists = {
        '$in',
        '$nin',
    }

    def __init__(self, document):
        """Create an encoder for the given document class."""
        self.document = document

    def field(self, name, value):
        """Return the encoded query value for the given field."""
        field = self.document._meta.fields[name]
        if isinstance(value, dict):
            encoded = OrderedDict()
            for comparison, value in value.iteritems():
                if comparison in self.lists:
                    encoded_value = []
                    for item in value:
                        if item is not None:
                            item = field.encode(self.document, name, item)
                        encoded_value.append(item)
                    value = encoded_value
                elif comparison in self.scalars:
                    value = field.encode(self.document, name, value)
                encoded[comparison] = value
        else:
            encoded = field.encode(self.document, name, value)
        return encoded

    def encode(self, criteria):
        """Return an encoded query value."""
        if not isinstance(criteria, dict):
            raise TypeError("query criteria must be of type dict")
        if not criteria:
            return None
        encoded = OrderedDict()
        for name, value in criteria.iteritems():
            if name in self.document._meta.fields:
                value = self.field(name, value)
            elif isinstance(value, dict):
                value = self.encode(value)
            elif isinstance(value, (tuple, list, set)):
                value = [self.encode(item) for item in value]
            encoded[name] = value
        return encoded


class Query(object):
    """A query abstracts a MongoDB query."""

    def __init__(self, criteria):
        """Initialize the query with the provided criteria."""
        if criteria is None:
            criteria = OrderedDict()
        elif isinstance(criteria, Query):
            criteria = criteria.criteria.copy()
        elif not isinstance(criteria, OrderedDict):
            criteria = OrderedDict(criteria)
        self.criteria = criteria

    def copy(self):
        """Return a copy of the query."""
        return Query(deepcopy(self.criteria))

    def encode(self, document):
        """Return the encoded query in the context of the given document."""
        return QueryEncoder(document).encode(self.criteria)

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
