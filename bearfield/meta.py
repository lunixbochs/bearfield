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

        fields = {}
        for base in reversed(cls.__bases__):
            if isinstance(getattr(base, '_meta', None), self.__class__):
                fields.update(base._meta.fields)

        if attrs:
            for name, attr in attrs.items():
                if isinstance(attr, BaseField):
                    fields[name] = attr

        self.fields = fields

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
            self._raw = {}
            for name, default in meta.defaults.iteritems():
                if hasattr(default, '__call__'):
                    field = self._meta.get_field(name)
                    default = field.encode(meta.cls, name, default())
                self._raw[name] = default
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
                if not hasattr(default, '__call__'):
                    default = field.encode(self.cls, name, field.default)
                field.validate(self.cls, name, default)
            defaults[name] = default

        self.defaults = defaults

    def get_connection(self, connection=None):
        """
        Return the connection associated with this document. If connection is provided then it will
        be used instead. This value may be the name of a connection or an actual connection object.

        If this document has no connection (`self.connection is None`),
        the default global connection is used.
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
        raise OperationError(
            "document {} has no connection, and no default exists".format(self.cls.__name__))

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
            if not hasattr(field, 'typ') or not isinstance(field.typ, DocumentType):
                break
            doc = field.typ.document

        if len(names):
            return None
        return field

    @property
    def readonly(self):
        """Return True if the document is readonly."""
        return bool(self.options.get('readonly', False) or (
            self.options.get('disable_save', False) and
            self.options.get('disable_insert', False) and
            self.options.get('disable_update', False) and
            self.options.get('disable_remove', False)))

    @property
    def disable_save(self):
        """Return True if save is disabled for the document."""
        return (bool(self.options.get('readonly', False) or
                self.options.get('disable_save', False)))

    @property
    def disable_insert(self):
        """Return True if insert is disabled for the document."""
        return (bool(self.options.get('readonly', False) or
                self.options.get('disable_insert', False)))

    @property
    def disable_update(self):
        """Return True if update is disabled for the document."""
        return (bool(self.options.get('readonly', False) or
                self.options.get('disable_update', False)))

    @property
    def disable_remove(self):
        """Return True if remove is disabled for the document."""
        return (bool(self.options.get('readonly', False) or
                self.options.get('disable_remove', False)))


class DocumentBuilder(type):
    """Metaclass for building document classes."""

    def __new__(meta, name, bases, attrs):
        """Create and attach metadata to the document."""
        Meta = attrs.pop('Meta', {})
        cls = type.__new__(meta, name, bases, attrs)
        cls._meta = DocumentMeta(cls, attrs, Meta)
        return cls
