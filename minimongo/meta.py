from collections import defaultdict

from .field import Field


class DocMeta(object):
    def __init__(self, cls, fields, meta):
        self.cls = cls
        cls.__init__ = self.init_hook()
        self.fields = {}
        self.opt = {}

        if fields:
            if not hasattr(fields, '__getitem__'):
                fields = vars(fields)
            for name, field in fields.items():
                if isinstance(field, Field):
                    self.fields[name] = field
        if meta:
            self.opt = vars(meta)

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


class DocBuilder(type):
    def __new__(meta, name, bases, attrs):
        Meta = attrs.pop('Meta', {})

        cls = type.__new__(meta, name, bases, attrs)
        cls._meta = DocMeta(cls, attrs, Meta)
        return cls
