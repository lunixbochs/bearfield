"""Code for managing references."""
from .document import Document
from .errors import EncodingError
from .field import BaseField
from .query import Query
from bson import ObjectId
from bson.errors import InvalidId


class Reference(BaseField):
    """
    A reference is effectively a stored query against a known collections. A reference may store
    one of two values: an ObjectId or a Query object. A reference may be set using those two values
    or something else. If the value is a string an attempt is made to convert it to an ObjectId.
    An attempt is made to convert any other type to a Query. A TypeError is raised if conversion
    fails.
    """

    def __init__(self, doctype, require=True, default=None):
        """
        Initialize a new reference. The reference uses a Document class to determine which
        collection to make queries against.
        """
        self.doctype = doctype
        self.require = require
        self.default = default

    def getter(self, obj, name):
        """Return a ReferenceFinder for the reference."""
        return ReferenceFinder(self, obj, name)

    def setter(self, obj, name, value):
        """
        Set the Reference query. Raise TypeError on value conversion failure. Raise ValueError if
        the value is a Document with no _id field.
        """
        from .document import Document
        if value is not None:
            if isinstance(value, basestring):
                try:
                    value = ObjectId(value)
                except InvalidId:
                    raise TypeError("'{}' is not a valid ObjectId".format(value))
            elif isinstance(value, Document):
                _id = getattr(value, '_id', None)
                if not _id:
                    raise ValueError(
                        "Document of type {} has no _id".format(value.__class__.__name__))
                value = _id
            elif not isinstance(value, (Query, ObjectId)):
                value = Query(value)
        super(Reference, self).setter(obj, name, value)

    def encode(self, cls, name, value):
        """Return an encoded ObjectID or Query."""
        if isinstance(value, Query):
            value = value.encode(self.doctype)
        elif isinstance(value, Document):
            value = value._id
        return value

    def decode(self, cls, name, value):
        """Return a decoded ObjectID or Query."""
        if not isinstance(value, ObjectId):
            try:
                value = Query(value)
            except TypeError:
                raise EncodingError("invalid Query or ObjectId: {}".format(repr(value)))
        return value


class ReferenceFinder(object):
    """Proxy calls to the reference value."""

    def __init__(self, reference, document, name):
        self.reference = reference
        self.document = document
        self.name = name

    @property
    def value(self):
        """Return the reference value."""
        if self.name not in self.document._attrs:
            value = self.document._raw.get(self.name)
            if value is not None:
                try:
                    value = self.reference.decode(self.document.__class__, self.name, value)
                except EncodingError as e:
                    raise TypeError(e)
            self.document._attrs[self.name] = value
        return self.document._attrs[self.name]

    @property
    def query(self):
        """
        Return the reference as a query. If the reference is None then it returns the query
        {'_id': None}.
        """
        value = self.value
        if value is None or isinstance(value, ObjectId):
            value = Query({'_id': value})
        return value

    def find(self, fields=None, connection=None, **options):
        """
        Return the results of a find using the reference. Options are the same as Document.find()
        without query.
        """
        cls = self.reference.doctype
        return cls.find(self.query, fields, connection, **options)

    def find_one(self, fields=None, connection=None, **options):
        """
        Return the results of a find_one using the reference. Options are the same as
        Document.find_one() without query.
        """
        cls = self.reference.doctype
        return cls.find_one(self.query, fields, connection, **options)
