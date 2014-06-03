"""Cursors for iterating over documents."""
from copy import deepcopy


class Cursor(object):
    """
    Cursors are used to iterate over multiple documents or to further refine the results of a
    find().
    """

    def __init__(self, document, collection, criteria, **options):
        """
        Initialize the cursor with the given find criteria. The find will be executed against the
        given connection. Additional args are passed to pymongo's find().
        """
        self.document = document
        self.collection = collection
        self.criteria = criteria
        self.options = options

    @property
    def connection(self):
        """Return the connection for the cursor."""
        return self.collection._connection

    def find(self, criteria):
        """Refine the cursor's scope with additional criteria. Return a new cursor."""
        if len(self.criteria) == 1 and '$and' in self.criteria:
            criteria_chain = deepcopy(self.criteria)
        else:
            criteria_chain = {'$and': [deepcopy(self.criteria)]}
        criteria_chain['$and'].append(self.criteria)
        return Cursor(self, criteria_chain, self.connection, **self.options)

    def __iter__(self):
        """Return the cursor iterator."""
        return CursorIterator(self)


class CursorIterator(object):
    """Iterate over cursor results."""

    def __init__(self, cursor):
        """Initialize the cursor iterator."""
        self.document = cursor.document
        self.connection = cursor.connection
        self.pymongo_cursor = cursor.collection.find(cursor.criteria, **cursor.options)

    def next(self):
        """Return the next item in the iterator."""
        def decode_next():
            return self.document._decode(self.pymongo_cursor.next())
        return self.connection.autoreconnect(decode_next)()
