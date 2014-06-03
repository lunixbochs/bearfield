"""Document and subdocument classes."""
from .cursor import Cursor
from .errors import OperationError
from .meta import DocumentBuilder
from collections import defaultdict


class Document(object):
    """
    A document or subdocument. Document properties are defined in an optional Meta subclass. In
    order for a document to be saved to a database it must associate itself with a named connection
    by setting the 'connection' meta attribute to that connection name. The collection name is the
    connection prefix plus the snake cased class name of the document. This may be overridden by
    setting the 'collection' property to the desired named of the colleciton. The connection's
    prefix will still be prepended to the name.

    Fields are defined on the document by assigning Field objects to class attributes. See the
    Field class for details on field parameters.

    A document may be provided as the type to a Field. This will cause that field to be treated as
    a subdocument.
    """
    __metaclass__ = DocumentBuilder

    @classmethod
    def _decode(cls, item):
        """Return a document decoded from a MongoDB record."""
        if item is None:
            return None
        doc = cls()
        for key, value in item.iteritems():
            if key in cls._meta.fields:
                setattr(doc, key, value)
        return doc

    @classmethod
    def _validate(cls, name, connection):
        """
        Validate an operation against the provided connection. Return a collectionf or operating
        against.
        """
        if cls._meta.subdocument:
            raise OperationError(
                "{}.{}(): invalid subdocument operation".format(cls.__name__, name))
        collection = cls._meta.get_collection(connection)
        if not collection:
            raise OperationError(
                "{}.{}(): no collection associated with document".format(cls.__name__, name))
        return collection

    @classmethod
    def find(cls, criteria=None, connection=None, **options):
        """
        Query the database for documents. Return a cursor for further refining or iterating over
        the results. Additional args are passed to pymongo's find().
        """
        collection = cls._validate(connection)
        return Cursor(cls, collection, criteria, **options)

    @classmethod
    def find_one(cls, criteria=None, connection=None, **options):
        """
        Query the database for a single document. Return the document or None if not found.
        Additional args are passed to pymongo's find().
        """
        collection = cls._validate(connection)
        return cls._decode(collection.find_one(criteria, **options))

    @classmethod
    def find_and_modify(cls, criteria, update, connection=None, **options):
        """
        Query the database for a document, update it, then return the new document. Additional args
        are passed to pymongo's find_and_modify().
        """
        collection = cls._validate(connection)
        options.pop('new', None)
        return cls._decode(collection.find_and_modify(criteria, update, new=True, **options))

    @property
    def _insertable(self):
        """Return the document as a dictionary suitable for inserting or saving."""
        return {k: v for k, v in self._raw.iteritems() if v is not None}

    @property
    def _updatable(self):
        """Return the document as a dictionary suitable for updating."""
        set_items = {}
        unset_items = {}
        for key, dirty in self._dirty.iteritems():
            if not dirty:
                continue
            value = self._raw.get(key)
            if value is None:
                unset_items[key] = ""
            else:
                set_items[key] = value
        update = {}
        if set_items:
            update['$set'] = set_items
        if unset_items:
            update['$unset'] = unset_items
        return update

    def save(self, connection=None, **options):
        """
        Save the model to the database. Effectively performs an insert if the _id field is None and
        a full document update otherwise. Additional args are passed to pymongo's save().
        """
        collection = self._validate(connection)
        item = self._insertable
        options.pop('manipulate', None)
        self._id = collection.save(item, manipulate=True, **options)
        self._dirty = defaultdict(bool)

    def insert(self, connection=None, **options):
        """
        Insert the document. This ignores the state of the _id field and forces an insert. This may
        necessitate setting _id to None prior to calling insert. Though this could be used to
        insert the same document into multiple databases. Additional args are passed to pymongo's
        insert().
        """
        collection = self._validate(connection)
        item = self._insertable
        options.pop('manipulate', None)
        self._id = collection.insert(item, manipulate=True, **options)
        self._dirty = defaultdict(bool)

    def update(self, update=None, connection=None, **options):
        """
        Update the document in the database using the provided update statement. If update is None
        (the default) an update statement is created to set all of the dirty fields in the
        document. This uses the _id field to find the document to update and will raise an error if
        no _id is set. Additional args are passed to pymongo's update(). Return True if an update
        was performed or False if no update was needed.
        """
        collection = self._validate(connection)
        item = update or self._updatable
        if item:
            options.pop('multi', None)
            self._raw = collection.find_and_update({'_id': self._id}, item, multi=False, **options)
            return True
        return False

    def remove(self, connection=None, **options):
        """
        Remove the document from the database. Additional args are passed to pymongo's remove().
        Return True if the document was removed or False if there was nothing to remove.
        """
        collection = self._validate(connection)
        if self._id:
            res = collection.remove(self._id)
            return res.get('n', 0) > 0
        return False
