"""Cursors for iterating over documents."""
from copy import deepcopy


class Cursor(object):
    """
    Cursors are used to iterate over multiple documents or to further refine the results of a
    find().
    """

    def __init__(self, document, collection, criteria, fields, **options):
        """
        Initialize the cursor with the given find criteria. The find will be executed against the
        given connection. Additional args are passed to pymongo's find().
        """
        self.document = document
        self.collection = collection
        self.criteria = criteria
        self.fields = fields
        self.options = options
        self.options.pop('manipulate', None)

    @property
    def connection(self):
        """Return the connection for the cursor."""
        return self.collection._connection

    @property
    def pymongo(self):
        """Return the pymongo cursor which underlies this object."""
        if not getattr(self, '_pymongo_cursor', None):
            self._pymongo_cursor = self.collection.find(self.criteria, fields=self.fields, **self.options)
        return self._pymongo_cursor

    def find(self, criteria):
        """Refine the cursor's scope with additional criteria. Return a new cursor."""
        if len(self.criteria) == 1 and '$and' in self.criteria:
            criteria_chain = deepcopy(self.criteria)
        else:
            criteria_chain = {'$and': [deepcopy(self.criteria)]}
        criteria_chain['$and'].append(criteria)
        return Cursor(self.document, self.collection, criteria_chain, self.fields, **self.options)

    def remove(self):
        """Remove the documents matched by this cursor."""
        res = self.collection.remove(self.criteria)
        return res.get('n', 0)

    def __getitem__(self, index):
        """Return the document at the given index.""" 
        return self.document._decode(self.pymongo[index], self.fields)

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
