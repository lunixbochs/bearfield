"""Document and subdocument classes."""
from __future__ import absolute_import
from .cursor import Cursor
from .encoders import SortEncoder, UpdateEncoder
from .errors import OperationError, ValidationError
from .meta import DocumentBuilder
from .query import Query
from .utils import get_projection
import six


class Document(six.with_metaclass(DocumentBuilder, object)):
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

    def __new__(cls, *args, **kwargs):
        """Create new instance of Document."""
        doc = object.__new__(cls)
        doc._raw = {}
        doc._attrs = {}
        doc._dirty = set()
        doc._partial = None
        return doc

    @classmethod
    def _decode(cls, raw, fields=None):
        """
        Return a document decoded from a MongoDB record. If fields is not None then a partial
        document will be created with those field values.
        """
        if raw is None:
            return None
        doc = cls.__new__(cls)
        doc._raw = raw.copy()
        doc._partial = cls._meta.get_partial(fields)
        doc.__init__()
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
        for name, field in six.iteritems(cls._meta.get_fields(partial)):
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
    def create_indexes(cls, connection=None, indexes=None, **kwargs):
        """
        Create all indexes from this document's Meta, or  on the collection.
        Indexes must be a list of pymongo.IndexModel().
        Be careful about calling this for large collections.
        """
        if indexes is None:
            indexes = cls._meta.indexes
        if not indexes:
            return
        collection = cls._meta.get_collection(connection)
        return collection.create_indexes(indexes, **kwargs)

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
        Query the database for a document and update it. If new is true, returns the modified
        document, otherwise returns the original document. Additional args are passed to pymongo's
        find_one_and_update() and include:
            upsert: When true, if no documents match, a new document is created.
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
        if options.get('upsert'):
            specified_update_fields = {fieldname
                                       for doc in update.keys()
                                       for fieldname in update[doc]}
            defaults = {}
            for name, default in six.iteritems(cls._meta.defaults):
                if default is not None and name not in specified_update_fields:
                    if hasattr(default, '__call__'):
                        field = cls._meta.get_field(name)
                        default = field.encode(cls._meta.cls, name, default())
                    defaults[name] = default
            set_on_insert = update.get('$setOnInsert', {})
            defaults.update(set_on_insert)
            update.update({
                '$setOnInsert': defaults
            })
        raw = collection.find_one_and_update(criteria, update, projection=get_projection(fields),
                                             new=new, sort=sort, **options)
        return cls._decode(raw, fields)

    @classmethod
    def count(cls, connection=None):
        """Count the number of objects in this collection."""
        collection = cls._meta.get_collection(connection)
        return collection.count()

    def __init__(self, *args, **kwargs):
        """Initialize the document with values."""
        for name, value in six.iteritems(kwargs):
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
            for name, field in six.iteritems(self._meta.get_fields(self._partial)):
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
            for name, field in six.iteritems(self._meta.get_fields(self._partial)):
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

    def __repr__(self):
        attrs = ['{}={}'.format(name, repr(value)) for name, value in self._encode().items()]
        return '{}({})'.format(self.__class__.__name__, ', '.join(attrs))

    def save(self, connection=None, **options):
        """
        Save the model to the database. Effectively performs an insert if the _id field is None and
        a full document update otherwise. Additional args are passed to pymongo's save().
        Returns self for assignment.
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
        return self

    def insert(self, connection=None, **options):
        """
        Insert the document. This ignores the state of the _id field and forces an insert. This may
        necessitate setting _id to None prior to calling insert. Though this could be used to
        insert the same document into multiple databases. Additional args are passed to pymongo's
        insert().
        Returns self for assignment.
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
        return self

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
