"""Cursors for iterating over documents."""
from .query import Query
from .utils import get_projection


class Cursor(object):
    """
    Cursors are used to iterate over multiple documents or to further refine the results of a
    find().
    """

    def __init__(self, document, collection, query, fields, raw, **options):
        """
        Initialize the cursor with the given find query. The find will be executed against the
        given connection. Additional args are passed to pymongo's find().
        """
        self.document = document
        self.collection = collection
        self.query = self._make_query(query)
        self.fields = fields
        self.raw = raw
        self.options = options
        self.options.pop('manipulate', None)

    def _make_query(self, query):
        """Return a query for an object of dubious origin."""
        if query is not None and not isinstance(query, Query):
            query = Query(query)
        return query

    @property
    def _criteria(self):
        """Return the encoded criteria for the cursor."""
        if self.query is None:
            return None
        return self.query.encode(self.document, self.raw)

    @property
    def connection(self):
        """Return the connection for the cursor."""
        return self.collection._connection

    @property
    def pymongo(self):
        """Return the pymongo cursor which underlies this object."""
        if not getattr(self, '_pymongo_cursor', None):
            self._pymongo_cursor = self.collection.find(
                self._criteria, projection=get_projection(self.fields), **self.options)
        return self._pymongo_cursor

    def count(self):
        """Count the number of objects matching this cursor."""
        return self.pymongo.count()

    def find(self, query):
        """Refine the cursor's scope with an additional query. Return a new cursor."""
        query = self.query & self._make_query(query)
        return Cursor(self.document, self.collection, query, self.fields, self.raw, **self.options)

    def remove(self):
        """Remove the documents matched by this cursor."""
        res = self.collection.remove(self._criteria)
        return res.get('n', 0)

    def __getitem__(self, index):
        """Return the document at the given index."""
        return self.document._decode(self.pymongo[index], get_projection(self.fields))

    def __iter__(self):
        """Return the cursor iterator."""
        return self

    def __len__(self):
        return self.pymongo.count()

    def next(self):
        """Return the next item in the iterator."""
        def decode_next():
            return self.document._decode(self.pymongo.next(), self.fields)
        return self.connection.autoreconnect(decode_next)()

    def close(self):
        """Explicitly close the cursor."""
        if getattr(self, '_pymongo_cursor', None):
            self._pymongo_cursor.close()
            self._pymongo_cursor = None
