"""Meta functionality used for document creation."""
from .connection import Connection, get as get_connection
from .errors import OperationError
from .field import BaseField, Field
from bson import ObjectId
from utils import to_snake_case


class DocumentMeta(object):
    """Metadata container for Document classes."""

    def __init__(self, cls, attrs, meta):
        """Initialize new document class metadata."""
        self.cls = cls
        self.fields = {}
        self.options = {}

        self.bind_init()

        if attrs:
            for name, attr in attrs.items():
                if isinstance(attr, BaseField):
                    self.fields[name] = attr

        if meta:
            self.options.update(vars(meta))

        self.connection = self.options.pop('connection', None)
        self.collection = self.options.pop('collection', None)
        if not self.collection:
            self.collection = to_snake_case(cls.__name__)

        self.subdocument = not bool(self.connection)
        if not self.subdocument and '_id' not in self.fields:
            self.fields['_id'] = Field(ObjectId, require=False)

        self.bind_fields()

    def bind_init(meta):
        """Bind init hook to the document class."""
        parent = meta.cls.__init__
        # prevent recursive decoration
        if hasattr(parent, 'parent'):
            parent = parent.parent

        def __init__(self, *args, **kwargs):
            self._raw = meta.defaults.copy()
            self._attrs = {}
            self._dirty = set()
            self._partial = None
            return parent(self, *args, **kwargs)

        __init__.name = parent.__name__
        __init__.hook = True
        __init__.parent = parent
        meta.cls.__init__ = __init__

    def bind_fields(self):
        """Bind fields to the document class."""
        defaults = {}
        for name, field in self.fields.items():
            setattr(self.cls, name, field(self.cls, name))
            default = field.default
            if default is not None:
                default = field.encode(self.cls, name, field.default)
                field.validate(self.cls, name, default)
            defaults[name] = default

        self.defaults = defaults

    def get_connection(self, connection=None):
        """
        Return the connection associated with this document. If connection is provided then it will
        be used instead. This value may be the name of a connection or an actual connection object.
        """
        if connection:
            if isinstance(connection, Connection):
                return connection
            else:
                return get_connection(str(connection))
        return get_connection(self.connection)

    def get_collection(self, connection=None):
        """
        Return the collection associated with this document. If error it True then errors are Raise
        an OperationError if the document has no collection.
        """
        if self.collection:
            connection = self.get_connection(connection)
            if connection:
                return connection[self.collection]
        if self.subdocument:
            msg = "subdocument {} does not have a collection".format(self.cls.__name__)
        else:
            msg = "document {} does not have a connection".format(self.cls.__name__)
        raise OperationError(msg)

    def get_partial(self, fields):
        """Return a valid partial value from a list of fields."""
        if fields:
            return {'_id'} | set(fields)
        return None

    def get_fields(self, partial):
        """Return a dictionary containing active fields."""
        if partial:
            return {k: self.fields[k] for k in partial if k in self.fields}
        return self.fields

    def get_field(self, name):
        """Return the named field. Supports dot syntax to retrieve fields from subdocuments."""
        from .types import DocumentType
        names = name.split('.')
        names.reverse()
        doc = self.cls
        field = None

        while len(names):
            name = names.pop()
            field = doc._meta.fields.get(name)
            if not field or not isinstance(field.typ, DocumentType):
                break
            doc = field.typ.document

        if len(names):
            return None
        return field


class DocumentBuilder(type):
    """Metaclass for building document classes."""

    def __new__(meta, name, bases, attrs):
        """Create and attach metadata to the document."""
        Meta = attrs.pop('Meta', {})
        cls = type.__new__(meta, name, bases, attrs)
        cls._meta = DocumentMeta(cls, attrs, Meta)
        return cls
