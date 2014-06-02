from .field import Field
from collections import defaultdict


class DocumentMeta(object):
    """Metadata container for Document classes."""

    def __init__(self, cls, attrs, meta):
        self.cls = cls
        self.fields = {}
        self.options = {}

        cls.__init__ = self.init_hook()

        if attrs:
            if not hasattr(attrs, '__getitem__'):
                attrs = vars(attrs)
            for name, attr in attrs.items():
                if isinstance(attr, Field):
                    self.fields[name] = attr
        if meta:
            self.options = vars(meta)

        self.bind()

    def init_hook(meta):
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
        return __init__

    def bind(self):
        defaults = {}
        for name, field in self.fields.items():
            setattr(self.cls, name, field(name))
            defaults[name] = field.default

        self.defaults = defaults

    def __repr__(self):
        return '<Meta ({})>'.format(self.cls.__name__)


class DocumentBuilder(type):
    """Metaclass for building document classes."""
    def __new__(meta, name, bases, attrs):
        Meta = attrs.pop('Meta', {})
        cls = type.__new__(meta, name, bases, attrs)
        cls._meta = DocumentMeta(cls, attrs, Meta)
        return cls
