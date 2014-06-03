"""Meta functionality used for document creation."""
from .connection import find_connection
from .errors import DocumentError
from .field import Field
from bson import ObjectId
from collections import defaultdict
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
            if not hasattr(attrs, '__getitem__'):
                attrs = vars(attrs)
            for name, attr in attrs.items():
                if isinstance(attr, Field):
                    self.fields[name] = attr

        if meta:
            self.options.update(vars(meta))

        self._connection = self.options.pop('connection', None)
        self._collection = self.options.pop('collection', None)
        if not self._collection:
            self._collection = to_snake_case(cls.__name__)

        self.subdocument = not bool(self._connection)

        if not self.subdocument and '_id' not in fields:
            self.fields['_id'] = Field(ObjectId)

        self.bind_fields()

    def bind_init(meta):
        """Bind init hook to the document class."""
        parent = meta.cls.__init__
        # prevent recursive decoration
        if hasattr(parent, 'parent'):
            parent = parent.parent

        def __init__(self, *args, **kwargs):
            self._raw = meta.defaults
            self._dirty = defaultdict(bool)
            return parent(self, *args, **kwargs)

        __init__.name = parent.__name__
        __init__.hook = True
        __init__.parent = parent
        meta.cls.__init__ = __init__

    def bind_fields(self):
        """Bind fields to the document class."""
        defaults = {}
        for name, field in self.fields.items():
            setattr(self.cls, name, field(name))
            defaults[name] = field.default

        self.defaults = defaults

    def get_connection(self):
        """Return the connection associated with this document."""
        if self._connection:
            return find_connection(self._connection)
        return None

    def get_collection(self, connection=None):
        """Return the collection associated with this document."""
        connection = connection or self.get_connection()
        if connection:
            return connection[self._collection]
        return None

    def __repr__(self):
        return '<DocumentMeta ({})>'.format(self.cls.__name__)


class DocumentBuilder(type):
    """Metaclass for building document classes."""

    def __new__(meta, name, bases, attrs):
        """Create and attach metadata to the document."""
        Meta = attrs.pop('Meta', {})
        cls = type.__new__(meta, name, bases, attrs)
        cls._meta = DocumentMeta(cls, attrs, Meta)
        return cls
