"""A few useful utilities."""
import re


def to_snake_case(name):
    """Convert a camel case string to snake case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def get_projection(fields):
    if fields:
        return list(fields)
    return None
