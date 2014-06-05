"""Document and subdocument classes."""
from .cursor import Cursor
from .errors import OperationError, ValidationError
from .meta import DocumentBuilder
from .query import Query
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
    def _make_partial(cls, fields):
        """Return a valid partial value from a list of fields."""
        if fields:
            return {'_id'} | set(fields)
        return None

    @classmethod
    def _make_criteria(cls, query):
        """Return a criteria dict for a query."""
        if isinstance(query, Query):
            query = Query(query).encode(self)
        return query

    @classmethod
    def _fields(cls, partial):
        """Return a dictionary containing active fields."""
        if partial:
            return {k: cls._meta.fields[k] for k in partial if k in cls._meta.fields}
        return cls._meta.fields

    @classmethod
    def _decode(cls, raw, fields=None):
        """
        Return a document decoded from a MongoDB record. If fields is not None then a partial
        document will be created with those field values.
        """
        if raw is None:
            return None
        doc = cls()
        doc._raw = raw.copy()
        doc._partial = cls._make_partial(fields)
        return doc

    @classmethod
    def _validate(cls, raw, partial=None, update=False):
        """
        Validate the raw document. Raise a ValidationError if validation fails. If the raw document
        is an update document then update should be set to True.
        """
        if update:
            raw = raw.get('$set', {})
        required = []
        for name, field in cls._fields(partial).iteritems():
            value = raw.get(name)
            if value is None:
                if field.require:
                    required.append(name)
            else:
                field.validate(cls, name, value)

        if not update and required:
            doc = cls.__name__
            required = ', '.join(sorted(required))
            raise ValidationError("{} is missing required fields: {}".format(doc, required))

    @classmethod
    def _collection(cls, connection, method):
        """
        Return a collection to operate against. Raise an OperationError if the document is a
        subdocument or is not associated with a collection. The method param should be the name of
        the method on the document that is being called.
        """
        if cls._meta.subdocument:
            raise OperationError(
                "{}.{}(): invalid subdocument operation".format(cls.__name__, method))
        collection = cls._meta.get_collection(connection)
        if not collection:
            raise OperationError(
                "{}.{}(): no collection associated with document".format(cls.__name__, method))
        return collection

    @classmethod
    def find(cls, query=None, fields=None, connection=None, **options):
        """
        Query the database for documents. Return a cursor for further refining or iterating over
        the results. If fields is not None only return the field values in that list. Additional
        args are passed to pymongo's find().
        """
        collection = cls._collection(connection, 'find')
        fields = cls._make_partial(fields)
        return Cursor(cls, collection, query, fields, **options)

    @classmethod
    def find_one(cls, query=None, fields=None, connection=None, **options):
        """
        Query the database for a single document. Return the document or None if not found.
        Additional args are passed to pymongo's find(). If fields is not None only return the field
        values in that list.
        """
        collection = cls._collection(connection, 'find_one')
        fields = cls._make_partial(fields)
        options.pop('manipulate', None)
        criteria = cls._make_criteria(query)
        return cls._decode(collection.find_one(criteria, fields=fields, **options), fields)

    @classmethod
    def find_and_modify(cls, query, update, fields=None, connection=None, **options):
        """
        Query the database for a document, update it, then return the new document. Additional args
        are passed to pymongo's find_and_modify().
        """
        collection = cls._collection(connection, 'find_and_modify')
        fields = cls._make_partial(fields)
        options.pop('new', None)
        criteria = cls._make_criteria(query)
        raw = collection.find_and_modify(criteria, update, fields=fields, new=True, **options)
        return cls._decode(raw, fields)

    def __init__(self, *args, **kwargs):
        """Initialize the document with values."""
        self._attrs.update(kwargs)

    def _encode(self, update=False):
        """
        Return the document as a dictionary suitable for saving. If update is
        True then an update document is returned.
        """
        raw = {}
        if update:
            sets = {}
            unsets = {}
            for name, field in self._fields(self._partial).iteritems():
                if name not in self._dirty:
                    continue
                value = self._attrs.get(name)
                if value is None:
                    unsets[name] = ""
                else:
                    sets[name] = field.encode(self.__class__, name, value)
            if sets:
                raw['$set'] = sets
            if unsets:
                raw['$unset'] = unsets
        else:
            for name, field in self._fields(self._partial).iteritems():
                if name in self._attrs:
                    value = self._attrs[name]
                    if value is not None:
                        value = field.encode(self.__class__, name, value)
                else:
                    value = self._raw.get(name)
                if value is not None:
                    raw[name] = value
        return raw

    def _reset(self, raw, update=False):
        """Reset internal field storage using the raw document."""
        if update:
            unsets = {k: None for k in raw.get('$unset', {}).iteritems()}
            raw = raw.get('$set', {})
            raw.update(unsets)
        self._raw.update(raw)
        self._attrs = {}
        self._dirty = set()

    def save(self, connection=None, **options):
        """
        Save the model to the database. Effectively performs an insert if the _id field is None and
        a full document update otherwise. Additional args are passed to pymongo's save().
        """
        if self._partial:
            raise OperationError("unable to save partial document")
        collection = self._collection(connection, 'save')
        raw = self._encode()
        self._validate(raw, self._partial)
        options.pop('manipulate', None)
        self._id = collection.save(raw, manipulate=True, **options)
        self._reset(raw)

    def insert(self, connection=None, **options):
        """
        Insert the document. This ignores the state of the _id field and forces an insert. This may
        necessitate setting _id to None prior to calling insert. Though this could be used to
        insert the same document into multiple databases. Additional args are passed to pymongo's
        insert().
        """
        collection = self._collection(connection, 'insert')
        raw = self._encode()
        self._validate(raw, self._partial)
        options.pop('manipulate', None)
        self._id = collection.insert(raw, manipulate=True, **options)
        self._reset(raw)

    def update(self, update=None, connection=None, **options):
        """
        Update the document in the database using the provided update statement. If update is None
        (the default) an update statement is created to set all of the dirty fields in the
        document. This uses the _id field to find the document to update and will raise an error if
        no _id is set. Additional args are passed to pymongo's update(). Return True if an update
        was performed or False if no update was needed.
        """
        if not self._id:
            raise OperationError("unable to update document without an _id")
        collection = self._collection(connection, 'update')
        reset = not bool(update)
        update = update or self._encode(True)
        self._validate(update.get('$set', {}), self._partial, True)
        if update:
            options.pop('multi', None)
            options.pop('fields', None)
            self._attrs = collection.find_and_modify(
                {'_id': self._id}, update, fields=self._partial, multi=False, **options)
            if reset:
                self._reset(update, True)
            return True
        return False

    def remove(self, connection=None, **options):
        """
        Remove the document from the database. Additional args are passed to pymongo's remove().
        Return True if the document was removed or False if there was nothing to remove.
        """
        collection = self._collection(connection, 'remove')
        if self._id:
            res = collection.remove(self._id)
            return res.get('n', 0) > 0
        return False