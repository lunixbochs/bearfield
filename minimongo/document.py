from .meta import DocBuilder
from .value import Value


class Document(Value):
    __metaclass__ = DocBuilder

    def _encode(self):
        return self._raw

    def _decode(self):
        return self._raw

    def find(self, *args, **kwargs):
        pass

    def find_one(self, *args, **kwargs):
        pass

    def save(self, update=False):
        self._dirty = {}

    def update(self, *args, **kwargs):
       pass
