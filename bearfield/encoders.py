"""Additional data encoders."""
from .errors import EncodingError
from .types import ListType
from collections import OrderedDict


class SortEncoder(object):
    """Encode sort specs."""

    def encode(self, value):
        """
        Encode a sort value. Value must be convertible to an int or OrderedDict or raises an
        EncodingError.
        """
        if value is None:
            return None

        try:
            value = OrderedDict(value)
            encoded = OrderedDict()
            for field, direction in value.iteritems():
                try:
                    encoded[str(field)] = int(direction)
                except (TypeError, ValueError):
                    raise EncodingError(
                        'unable to encode sort field', field=field, value=direction)
            return encoded
        except (TypeError, ValueError):
            pass

        try:
            return int(value)
        except (TypeError, ValueError):
            pass

        raise EncodingError('unable to encode sort value', value=value)


class QueryEncoder(object):
    """Encode query specs."""
    scalars = {
        '$gt',
        '$gte',
        '$lt',
        '$lte',
        '$ne',
    }

    lists = {
        '$in',
        '$nin',
    }

    def __init__(self, document):
        """Create an encoder for the given document class."""
        self.document = document

    def field(self, name, value):
        """Return the encoded query value for the given field."""
        field = self.document._meta.fields[name]
        if isinstance(value, dict):
            encoded = OrderedDict()
            for comparison, value in value.iteritems():
                if comparison in self.lists:
                    encoded_value = []
                    for item in value:
                        if item is not None:
                            item = field.encode(self.document, name, item)
                        encoded_value.append(item)
                    value = encoded_value
                elif comparison in self.scalars:
                    if (isinstance(field.typ, ListType) and
                            not isinstance(value, (list, tuple, set))):
                        value = field.typ.encode_element(self.document, name, value)
                    else:
                        value = field.encode(self.document, name, value)
                encoded[comparison] = value
        else:
            encoded = field.encode(self.document, name, value)
        return encoded

    def encode(self, criteria):
        """Return an encoded query value."""
        if not criteria:
            return None
        try:
            criteria = OrderedDict(criteria)
        except (TypeError, ValueError):
            raise TypeError("query criteria type must be OrderedDict")

        encoded = OrderedDict()
        for name, value in criteria.iteritems():
            if name in self.document._meta.fields:
                value = self.field(name, value)
            elif isinstance(value, dict):
                value = self.encode(value)
            elif isinstance(value, (tuple, list, set)):
                value = [self.encode(item) for item in value]
            encoded[name] = value
        return encoded


class UpdateEncoder(object):
    """Encode update specs."""

    ops = {
        '$inc': 'scalar',
        '$mul': 'scalar',
        '$rename': 'str',
        '$setOnInsert': 'scalar',
        '$set': 'scalar',
        '$unset': 'unset',
        '$min': 'scalar',
        '$max': 'scalar',
        '$currentDate': 'currentdate',
        '$addToSet': 'add',
        '$pop': 'int',
        '$pullAll': 'array',
        '$pull': 'query',
        '$pushAll': 'array',
        '$push': 'push',
        '$bit': 'bitwise',
    }

    def __init__(self, document):
        """Create an encoder for the given document class."""
        self.document = document

    def is_positional(self, name):
        """Return True if the field name has a positional operator attached."""
        return name[-2:] == '.$'

    def get_field_name(self, name):
        """Return a clean field name."""
        if self.is_positional(name):
            return name[:-2]
        return name

    def get_field(self, name):
        """Return a named document field."""
        name = self.get_field_name(name)
        return self.document._meta.get_field(name)

    def get_encode_method(self, op):
        """Return the encode method for an update operator."""
        name = self.ops.get(op)
        if name:
            name = 'encode_' + name
            if hasattr(self, name):
                return getattr(self, name)
        return self.encode_default

    def encode_default(self, name, value):
        """Default encoder for unrecognized data."""
        return value

    def encode_scalar(self, name, value):
        """Encode a scalar update value."""
        if self.is_positional(name):
            return self.encode_array_element(name, value)
        field = self.get_field(name)
        if field:
            return field.encode(self.document, name, value)
        return self.encode_default(name, value)

    def encode_unset(self, name, value):
        """Encode an unset update value."""
        return ''

    def encode_array(self, name, values):
        """Encode an array update value."""
        field = self.get_field(name)
        if field:
            if isinstance(values, (list, tuple, set)):
                if isinstance(field.typ, ListType):
                    values = field.encode(self.document, name, values)
                else:
                    values = [field.encode(self.document, name, value) for value in values]
            else:
                if isinstance(field.typ, ListType):
                    values = field.typ.encode_element(self.document, name, values)
                else:
                    values = field.encode(self.document, name, values)
        else:
            values = self.encode_default(name, values)
        return values

    def encode_array_element(self, name, value):
        """Encode an array element update value."""
        field = self.get_field(name)
        if field:
            if isinstance(field.typ, ListType):
                return field.typ.encode_element(self.document, name, value)
            else:
                return field.typ.encode(self.document, name, value)
        return self.encode_default(name, value)

    def encode_add(self, name, value):
        """Encode an value for adding to a set."""
        if isinstance(value, dict):
            encoded = OrderedDict()
            for item_name, item_value in value.iteritems():
                if item_name == '$each':
                    encoded[item_name] = self.encode_array(name, item_value)
                else:
                    encoded[item_name] = self.encode_default(name, item_value)
            value = encoded
        else:
            value = self.encode_array_element(name, value)
        return value

    def encode_sort(self, name, value):
        """Encode a sort spec."""
        return SortEncoder().encode(value)

    def encode_push(self, name, value):
        """Encode a push update value."""
        if isinstance(value, dict):
            encoded = OrderedDict()
            for item_name, item_value in value.iteritems():
                if item_name == '$each':
                    encoded[item_name] = self.encode_array(name, item_value)
                elif item_name == '$slice':
                    encoded[item_name] = self.encode_int(name, item_value)
                elif item_name == '$sort':
                    encoded[item_name] = self.encode_sort(name, item_value)
                elif item_name == '$position':
                    encoded[item_name] = self.encode_int(name, item_value)
                else:
                    encoded[item_name] = self.encode_default(name, item_value)
            value = encoded
        else:
            value = self.encode_array_element(name, value)
        return value

    def encode_query(self, name, value):
        """Encode a query update value."""
        from .query import Query
        if not isinstance(value, Query):
            value = Query(value)
        return value.encode(self.document)

    def encode_currentdate(self, name, value):
        """Encode a currentdate value."""
        if isinstance(value, dict):
            encoded = OrderedDict()
            for item_name, item_value in value.iteritems():
                if item_name == '$type':
                    encoded[item_name] = self.encode_str(name, item_value)
                else:
                    encoded[item_name] = self.encode_default(name, item_value)
            value = encoded
        else:
            value = bool(value)
        return value

    def encode_bitwise(self, name, value):
        """Encode a bitwise value."""
        try:
            value = OrderedDict(value)
        except (TypeError, ValueError):
            raise EncodingError("unable to encode bitwise value", self.document, name, value)

        encoded = OrderedDict()
        for item_name, item_value in value.iteritems():
            encoded[str(item_name)] = self.encode_int(name, item_value)
        return encoded

    def encode_str(self, name, value):
        """Encode a value as a string."""
        return str(value)

    def encode_int(self, name, value):
        """Encode a value as an integer."""
        try:
            return int(value)
        except (TypeError, ValueError):
            raise EncodingError("unable to encode integer value", self.document, name, value)

    def encode(self, value):
        """Return an encoded update value."""
        if not value:
            return None
        try:
            value = OrderedDict(value)
        except (TypeError, ValueError):
            raise EncodingError("unable to encode update", self.document, '<update>', value=value)

        encoded = OrderedDict()
        for op, values in value.iteritems():
            encode_method = self.get_encode_method(op)
            encoded_update = OrderedDict()
            for name, value in values.iteritems():
                encoded_update[name] = encode_method(name, value)
            encoded[op] = encoded_update
        return encoded
