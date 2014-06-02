from .meta import DocumentBuilder
from .value import Value


class Document(object):
    __metaclass__ = DocumentBuilder

    def find(self, *args, **kwargs):
        pass

    def find_one(self, *args, **kwargs):
        pass

    def save(self, update=False):
        self._dirty = {}

    def update(self, *args, **kwargs):
       pass
