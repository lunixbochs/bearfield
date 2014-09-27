"""A few useful utilities."""
import re


def to_snake_case(name):
    """Convert a camel case string to snake case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def duck_punch(obj, name, prop):
    """Add a property to an object instance."""
    cls = obj.__class__
    if not hasattr(cls, '__duck'):
        cls = type(cls.__name__, (cls,), {})
        cls.__duck = True
        setattr(cls, name, prop)
        obj.__class__ = cls
