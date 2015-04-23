"""Additional data encoders."""
from .errors import EncodingError
from collections import OrderedDict


class BaseEncoder(object):
    """Base encoder class."""

    def __init__(self, document):
        """Create an encoder for the given document."""
        self.document = document

    def is_array_value(self, value):
        """Return True if the value can be encoded to an array."""
        return isinstance(value, (list, tuple, set))

    def is_array_field(self, field):
        """Return True if a field stores an array."""
        typ = getattr(field, 'typ', None)
        return typ and hasattr(typ, 'encode_element')

    def encode_default(self, name, value):
        """Return a value with default encoding."""
        return value

    def encode_builtin(self, builtin, name, value):
        try:
            return builtin(value)
        except (TypeError, ValueError):
            msg = "unable to encode {} value".format(builtin.__name__)
            raise EncodingError(msg, self.document, name, value)

    def encode_int(self, name, value):
        """Return a value encoded as an integer."""
        return self.encode_builtin(int, name, value)

    def encode_float(self, name, value):
        """Return a value encoded as a float."""
        return self.encode_builtin(float, name, value)

    def encode_bool(self, name, value):
        """Return a value encoded as a boolean."""
        return self.encode_builtin(bool, name, value)

    def encode_str(self, name, value):
        """Return a value encoded as a string."""
        return self.encode_builtin(str, name, value)

    def encode_geojson_coords(self, name, value):
        """Return a value encoded as GeoJSON coordinates."""
        if not self.is_array_value(value):
            return self.encode_float(name, value)

        encoded = []
        for item in value:
            encoded.append(self.encode_geojson_coords(name, item))
        return encoded

    def encode_geojson(self, name, value):
        """Return a value encoded as a GeoJSON value."""
        try:
            value = OrderedDict(value)
        except (TypeError, ValueError):
            msg = "unable to encode value as GeoJSON"
            raise EncodingError(msg, self.document, name, value)

        encoded = OrderedDict()
        for item_name, item_value in value.iteritems():
            if item_name == 'type':
                item_value = self.encode_str(item_name, item_value)
            elif item_name == 'coordinates':
                item_value = self.encode_geojson_coords(item_name, item_value)
            else:
                item_value = self.encode_default(item_name, item_value)
            encoded[item_name] = item_value
        return encoded


class OperatorEncoder(BaseEncoder):
    """Base encoder for specs with operators."""
    ops = {}

    def get_encode_method(self, op):
        """Return the encode method for an operator."""
        name = self.ops.get(op)
        if name:
            name = 'encode_' + name
            if hasattr(self, name):
                return getattr(self, name)
        return self.encode_default

    def get_field(self, name):
        """Return the field for the given name."""
        return self.document._meta.get_field(name)


class SortEncoder(BaseEncoder):
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
                direction = self.encode_int(field, direction)
                field = self.encode_str(field, field)
                encoded[field] = direction
            return encoded.items()
        except (TypeError, ValueError):
            pass

        try:
            return int(value)
        except (TypeError, ValueError):
            pass

        raise EncodingError('unable to encode sort value', value=value)


class QueryEncoder(OperatorEncoder):
    """Encode query specs."""

    ops = {
        '$gt': 'field',
        '$gte': 'field',
        '$lt': 'field',
        '$lte': 'field',
        '$ne': 'field',
        '$in': 'field',
        '$nin': 'field',
        '$or': 'logical',
        '$and': 'logical',
        '$not': 'negation',
        '$nor': 'logical',
        '$exists': 'bool',
        '$type': 'int',
        '$mod': 'mod',
        '$regex': 'str',
        '$options': 'str',
        '$search': 'str',
        '$language': 'str',
        '$where': 'str',
        '$all': 'field',
        '$elemMatch': 'array_query',
        '$size': 'int',
        '$geoWithin': 'geo',
        '$geoIntersects': 'geo',
        '$near': 'geo',
        '$nearSphere': 'geo',
    }

    def __init__(self, document):
        """Create a query encoder for a document type."""
        self.document = document

    def is_operator_name(self, name):
        """Return True if the name is an operator name."""
        return str(name)[:1] == '$'

    def is_operator_value(self, value):
        """Return True if a value contains operators."""
        try:
            value = OrderedDict(value)
            for name in value.keys():
                if self.is_operator_name(name):
                    return True
        except (TypeError, ValueError):
            pass
        return False

    def is_compiled_regex(self, value):
        """Return True if a value is a compiled regular expression."""
        return hasattr(value, 'pattern')

    def encode_logical(self, name, value):
        """Return a value encoded for a logical operator."""
        if not self.is_array_value(value):
            raise EncodingError("unable to encode logical operator", field=name, value=value)
        return [self.encode(v) for v in value]

    def encode_negation(self, name, value):
        """Return a value encoded for negation."""
        return self.encode(value)

    def encode_mod(self, name, value):
        """Return a value encoded for modulus division."""
        if not self.is_array_value(value):
            raise EncodingError("unable to encode mod operator", field=name, value=value)
        return [self.encode_float(name, v) for v in value]

    def encode_array_query(self, name, value):
        """Return a value encoded as an array."""
        from .types import DocumentType
        field = self.get_field(name)
        if field and self.is_array_field(field) and isinstance(field.typ.typ, DocumentType):
            document = field.typ.typ.document
        else:
            from .document import Document
            document = Document
        return QueryEncoder(document).encode(value)

    def encode_geo(self, name, value):
        """Return a value encoded as a geo query."""
        try:
            value = OrderedDict(value)
        except (TypeError, ValueError):
            raise EncodingError("unable to encode geo query", self.document, name, value)

        encoded = OrderedDict()
        for item_name, item_value in value.iteritems():
            if item_name == '$geometry':
                item_value = self.encode_geojson(item_name, item_value)
            elif item_name == '$maxDistance':
                item_value = self.encode_int(item_name, item_value)
            else:
                item_value = self.encode_default(item_name, item_value)
            encoded[item_name] = item_value
        return encoded

    def encode_field(self, name, value):
        """Return a value encoded as a field value."""
        if value is None:
            return None
        if self.is_compiled_regex(value):
            return self.encode_default(name, value)

        field = self.get_field(name)
        if field:
            if self.is_array_value(value):
                if self.is_array_field(field):
                    value = field.encode(self.document, name, value)
                else:
                    value = [field.encode(self.document, name, v) for v in value]
            else:
                if self.is_array_field(field):
                    value = field.typ.encode_element(self.document, name, value)
                else:
                    value = field.encode(self.document, name, value)
        else:
            value = self.encode_default(name, value)
        return value

    def encode_operator(self, name, value):
        """Return a value encoded as an operator dictionary."""
        if value is None:
            return None
        encode_method = self.get_encode_method(name)
        return encode_method(name, value)

    def encode_operators(self, name, value):
        """Return a value encoded as an operator dictionary."""
        encoded = OrderedDict()
        for item_name, item_value in value.iteritems():
            item_name = self.encode_str(name, item_name)
            if item_value is not None:
                encode_method = self.get_encode_method(item_name)
                item_value = encode_method(name, item_value)
            encoded[item_name] = item_value
        return encoded

    def encode(self, value):
        """Return an encoded query value."""
        if not value:
            return None
        try:
            value = OrderedDict(value)
        except (TypeError, ValueError):
            raise EncodingError("unable to encode query", self.document, '<query>', value)

        encoded = OrderedDict()
        for item_name, item_value in value.iteritems():
            item_name = self.encode_str('<query>', item_name)
            if self.is_operator_name(item_name):
                item_value = self.encode_operator(item_name, item_value)
            if self.is_operator_value(item_value):
                item_value = self.encode_operators(item_name, item_value)
            else:
                item_value = self.encode_field(item_name, item_value)
            encoded[item_name] = item_value
        return encoded


class UpdateEncoder(OperatorEncoder):
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
        return super(UpdateEncoder, self).get_field(name)

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
            if self.is_array_value(values):
                if self.is_array_field(field):
                    values = field.encode(self.document, name, values)
                else:
                    values = [field.encode(self.document, name, value) for value in values]
            else:
                if self.is_array_field(field):
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
            if self.is_array_field(field):
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
        return SortEncoder(self.document).encode(value)

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
