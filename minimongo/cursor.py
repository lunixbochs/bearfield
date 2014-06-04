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

    @property
    def pymongo(self):
        """Return the pymongo cursor which underlies this object."""
        if not getattr(self, '_pymongo_cursor', None):
            print("criteria: {}".format(self.criteria))
            print("collection: {}".format(self.collection.name))
            self._pymongo_cursor = self.collection.find(self.criteria, **self.options)
        return self._pymongo_cursor

    def find(self, criteria):
        """Refine the cursor's scope with additional criteria. Return a new cursor."""
        if len(self.criteria) == 1 and '$and' in self.criteria:
            criteria_chain = deepcopy(self.criteria)
        else:
            criteria_chain = {'$and': [deepcopy(self.criteria)]}
        criteria_chain['$and'].append(criteria)
        return Cursor(self.document, self.collection, criteria_chain, **self.options)

    def remove(self):
        """Remove the documents matched by this cursor."""
        res = self.collection.remove(self.criteria)
        return res.get('n', 0)

    def __iter__(self):
        """Return the cursor iterator."""
        return self

    def __len__(self):
        return self.pymongo.count()

    def next(self):
        """Return the next item in the iterator."""
        def decode_next():
            return self.document._decode(self.pymongo.next())
        return self.connection.autoreconnect(decode_next)()
