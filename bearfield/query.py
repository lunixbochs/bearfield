"""Query tools."""
from .encoders import QueryEncoder
from collections import OrderedDict
from copy import deepcopy


class Query(object):
    """A query abstracts a MongoDB query."""

    def __init__(self, criteria):
        """
        Initialize the query with the provided criteria. The criteria may be a Query or any value
        that may be converted to an OrderedDict which is the internal query representation. Raises
        a TypeError if criteria does not fit these requirements.
        """
        if criteria is None:
            criteria = OrderedDict()
        elif isinstance(criteria, Query):
            criteria = criteria.criteria.copy()
        elif not isinstance(criteria, OrderedDict):
            try:
                criteria = OrderedDict(criteria)
            except (TypeError, ValueError):
                raise TypeError("invalid query value {}".format(repr(criteria)))
        self.criteria = criteria

    def copy(self):
        """Return a copy of the query."""
        return Query(deepcopy(self.criteria))

    def encode(self, document, raw=None):
        """Return the encoded query in the context of the given document."""
        if raw:
            return self.criteria
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
        """Logically and this query (left side) with the provided query (right side)."""
        return self._op('$and', query)

    def __or__(self, query):
        """Logically or this query (left side) with the provided query (right side)."""
        return self._op('$or', query)

    def __eq__(self, query):
        """Return True if the query is equal to this one."""
        if isinstance(query, Query):
            return self.criteria == query.criteria
        return False


Q = Query
