"""Document and subdocument classes."""
from .cursor import Cursor
from .encoders import SortEncoder, UpdateEncoder
from .errors import OperationError, ValidationError
from .meta import DocumentBuilder
from .query import Query
from .utils import get_projection


class Document(object):
    """
    A document or subdocument. Document properties are defined in an optional Meta subclass. In
    order for a document to be saved to a database it must associate itself with a named connection
    by setting the 'connection' meta attribute to that connection name. The collection name is the
    connection prefix plus the snake cased class name of the document. This may be overridden by
    setting the 'collection' property to the desired name of the collection. The connection's
    prefix will still be prepended to the name.

    Fields are defined on the document by assigning Field objects to class attributes. See the
    Field class for details on field parameters.

    A document may be provided as the type to a Field. This will cause that field to be treated as
    a subdocument.
    """
    __metaclass__ = DocumentBuilder

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
        doc._partial = cls._meta.get_partial(fields)
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
        for name, field in cls._meta.get_fields(partial).iteritems():
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
    def find(cls, query=None, fields=None, connection=None, raw=None, sort=None, **options):
        """
        Query the database for documents. Return a cursor for further refining or iterating over
        the results. If fields is not None only return the field values in that list. Additional
        args are passed to pymongo's find().
        """
        collection = cls._meta.get_collection(connection)
        fields = cls._meta.get_partial(fields)
        if not raw:
            sort = SortEncoder(cls).encode(sort)
        return Cursor(cls, collection, query, fields, raw, sort=sort, **options)

    @classmethod
    def find_one(cls, query=None, fields=None, connection=None, raw=None, sort=None, **options):
        """
        Query the database for a single document. Return the document or None if not found.
        Additional args are passed to pymongo's find(). If fields is not None only return the field
        values in that list.
        """
        collection = cls._meta.get_collection(connection)
        fields = cls._meta.get_partial(fields)
        options.pop('manipulate', None)
        criteria = Query(query).encode(cls, raw)
        if not raw:
            sort = SortEncoder(cls).encode(sort)
        return cls._decode(collection.find_one(criteria, projection=get_projection(fields),
                                               sort=sort, **options), fields)

    @classmethod
    def find_and_modify(cls, query, update, fields=None, connection=None, raw=None, sort=None,
                        new=None, **options):
        """
        Query the database for a document, update it, then return the old document before
        modification. Additional args are passed to pymongo's find_and_modify().
        """
        if cls._meta.disable_update:
            msg = "updates to {} are disabled".format(cls.__class__.__name__)
            raise OperationError(msg)

        collection = cls._meta.get_collection(connection)
        fields = cls._meta.get_partial(fields)
        criteria = Query(query).encode(cls, raw)
        if new is None:
            new = False
        if not raw:
            sort = SortEncoder(cls).encode(sort)
            update = UpdateEncoder(cls).encode(update)
        raw = collection.find_and_modify(criteria, update, projection=get_projection(fields),
                                         new=new, sort=sort, **options)
        return cls._decode(raw, fields)

    @classmethod
    def count(cls, connection=None):
        """Count the number of objects in this collection."""
        collection = cls._meta.get_collection(connection)
        return collection.count()

    def __init__(self, *args, **kwargs):
        """Initialize the document with values."""
        for name, value in kwargs.iteritems():
            setattr(self, name, value)

    def _encode(self, update=False):
        """
        Return the document as a dictionary suitable for saving. If update is
        True then an update document is returned.
        """
        def modify(name, field):
            if getattr(field, 'modifier', None):
                setattr(self, name, field.modifier(getattr(self, name)))

        raw = {}
        if update:
            sets = {}
            unsets = {}
            for name, field in self._meta.get_fields(self._partial).iteritems():
                modify(name, field)
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
            for name, field in self._meta.get_fields(self._partial).iteritems():
                modify(name, field)
                if name in self._attrs:
                    value = self._attrs[name]
                    if value is not None:
                        value = field.encode(self.__class__, name, value)
                else:
                    value = self._raw.get(name)
                if value is not None:
                    raw[name] = value
        return raw

    def _reset(self, raw):
        """Reset internal field storage using the raw document."""
        self._raw.update(raw)
        self._attrs = {}
        self._dirty = set()

    def save(self, connection=None, **options):
        """
        Save the model to the database. Effectively performs an insert if the _id field is None and
        a full document update otherwise. Additional args are passed to pymongo's save().
        """
        if self._meta.disable_save:
            msg = "saves to {} are disabled".format(self.__class__.__name__)
            raise OperationError(msg)

        if self._partial:
            raise OperationError("unable to save partial document")

        collection = self._meta.get_collection(connection)
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
        if self._meta.disable_insert:
            msg = "inserts to {} are disabled".format(self.__class__.__name__)
            raise OperationError(msg)

        collection = self._meta.get_collection(connection)
        raw = self._encode()
        self._validate(raw, self._partial)
        options.pop('manipulate', None)
        self._id = collection.insert(raw, manipulate=True, **options)
        self._reset(raw)

    def update(self, update=None, connection=None, raw=None, sort=None, **options):
        """
        Update the document in the database using the provided update statement. If update is None
        (the default) an update statement is created to set all of the dirty fields in the
        document. This uses the _id field to find the document to update and will raise an error if
        no _id is set. Additional args are passed to pymongo's update(). Return True if an update
        was performed or False if no update was needed.
        """
        if self._meta.disable_update:
            msg = "updates to {} are disabled".format(self.__class__.__name__)
            raise OperationError(msg)

        if not self._id:
            raise OperationError("unable to update document without an _id")

        collection = self._meta.get_collection(connection)

        if not raw:
            sort = SortEncoder(self.__class__).encode(sort)

        if not update:
            update = self._encode(True)
        elif not raw:
            update = UpdateEncoder(self.__class__).encode(update)

        self._validate(update.get('$set', {}), self._partial, True)
        if update:
            options.pop('multi', None)
            options.pop('new', None)
            options.pop('fields', None)
            res = collection.find_and_modify(
                {'_id': self._id}, update, projection=get_projection(self._partial), multi=False,
                new=True, sort=sort, **options)
            self._reset(res)
            return True
        return False

    def remove(self, connection=None, **options):
        """
        Remove the document from the database. Additional args are passed to pymongo's remove().
        Return True if the document was removed or False if there was nothing to remove.
        """
        if self._meta.disable_remove:
            msg = "removal of {} is disabled".format(self.__class__.__name__)
            raise OperationError(msg)

        collection = self._meta.get_collection(connection)
        if self._id:
            res = collection.remove(self._id)
            return res.get('n', 0) > 0
        return False
