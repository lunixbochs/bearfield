"""Define field types that may be encoded and/or decoded."""
from collections import OrderedDict
from datetime import date, datetime, time
from errors import EncodingError

epoch = date(1970, 1, 1)
registered_field_types = []


def is_type(cls, typ):
    if not isinstance(cls, type):
        return False
    return issubclass(cls, typ)


def is_field_type(typ):
    """Return True if the type looks like a FieldType."""
    return isinstance(typ, FieldType)


def is_date_type(typ):
    """Return True if type is a date."""
    return is_type(typ, date) and not is_type(typ, datetime)


def is_datetime_type(typ):
    """Return True if type is a datetime."""
    return is_type(typ, datetime)


def is_time_type(typ):
    """Return True if type is a time."""
    return is_type(typ, time)


def is_document_type(typ):
    """Return True if type is a Document."""
    from .document import Document
    return is_type(typ, Document)


def is_list_type(typ):
    """Return True if obj is a list or tuple."""
    return is_type(typ, list) or is_type(typ, tuple)


def is_set_type(typ):
    """Return True if obj is a set."""
    return is_type(typ, set)


def is_dict_type(typ):
    """Return True if obj is a dict."""
    return is_type(typ, dict)


def is_date_obj(obj):
    """Return True if obj is a date."""
    return isinstance(obj, date) and not isinstance(obj, datetime)


def is_datetime_obj(obj):
    """Return True if obj is a datetime."""
    return isinstance(obj, datetime)


def is_time_obj(obj):
    """Return True if obj is a time."""
    return isinstance(obj, time)


def is_document_obj(obj):
    """Return True if obj is a Document."""
    from .document import Document
    return isinstance(obj, Document)


def is_list_obj(obj):
    """Return True if obj is a list or tuple."""
    return isinstance(obj, (list, tuple))


def is_set_obj(obj):
    """Return True if obj is a set."""
    return isinstance(obj, set)


def is_dict_obj(obj):
    """Return True if obj is a dict."""
    return isinstance(obj, dict)


def register_field_type(check, field_type):
    """
    Register a field type. The check is called on typ and should return True if the field type
    supports the type. The field_type is the field type class.
    """
    registered_field_types.append((check, field_type))


class FieldType(object):
    """Abstract class used for defining a field type."""

    @classmethod
    def create(cls, typ):
        if is_field_type(typ):
            return typ
        for check, field_type in registered_field_types:
            if check(typ):
                return field_type(typ)
        return BuiltinType(typ)

    def __init__(self, *args, **kwargs):
        pass

    def encode(self, cls, name, value):
        """Return the value encoded for storage in the database."""
        return value

    def decode(self, cls, name, value):
        """Return the value decoded from database storage."""
        return value

    def validate(self, cls, name, value):
        """Raise ValidationError if the field fails to validate."""


class BuiltinType(FieldType):
    """Used for built-in Python types which can be called with a single argument."""

    def __init__(self, builtin):
        """Create a field type using the given builtin type."""
        if isinstance(builtin, type) and issubclass(builtin, basestring):
            builtin = unicode
        self.builtin = builtin

    def encode(self, cls, name, value):
        """Return the encoded value."""
        try:
            return self.builtin(value)
        except (TypeError, ValueError):
            msg = "failed to encode value as {}".format(self.builtin.__class__.__name__)
            raise EncodingError(msg, cls, name, value, True)


class DateType(FieldType):
    """Support date values."""

    def encode(self, cls, name, value):
        """Return a date value as a datetime."""
        if is_datetime_obj(value):
            value = value.date()
        if is_date_obj(value):
            value = datetime.combine(value, time(0))
        if not is_datetime_obj(value):
            raise EncodingError(None, cls, name, value, True)
        return value

    def decode(self, cls, name, value):
        """Return the date value from the stored datetime."""
        if not is_datetime_obj(value):
            raise EncodingError(None, cls, name, value, False)
        return value.date()


class DateTimeType(FieldType):
    """Support datetime values."""

    def encode(self, cls, name, value):
        """Convert time and date values into a datetime."""
        if is_date_obj(value):
            value = datetime.combine(value, time(0))
        elif is_time_obj(value):
            value = datetime.combine(epoch, value)
        elif not is_datetime_obj(value):
            raise EncodingError(None, cls, name, value, True)
        return value

    def decode(self, cls, name, value):
        """Return the datetime value for the stored value."""
        if not is_datetime_obj(value):
            raise EncodingError(None, cls, name, value, False)
        return value


class TimeType(FieldType):
    """Support time values."""

    def encode(self, cls, name, value):
        """Convert a datetime into a time."""
        if is_datetime_obj(value):
            value = value.time()
        if is_time_obj(value):
            value = datetime.combine(epoch, value)
        else:
            raise EncodingError(None, cls, name, value, True)
        return value

    def decode(self, cls, name, value):
        """Return the time value from the stored datetime."""
        if is_datetime_obj(value):
            return value.time()
        raise EncodingError(None, cls, name, value, False)


class DocumentType(FieldType):
    """Support subdocuments."""

    def __init__(self, document):
        """Create a document type object with the given document class."""
        self.document = document

    def encode(self, cls, name, value):
        """Return the value encoded as a raw subdocument."""
        if is_document_obj(value):
            return value._encode()
        raise EncodingError(None, cls, name, value, True)

    def decode(self, cls, name, value):
        """Return the value decoded as a subdocument object."""
        if hasattr(value, 'get'):
            return self.document._decode(value)
        raise EncodingError(None, cls, name, value, False)

    def validate(self, cls, name, value):
        """Raise ValidationError if the field fails to validate."""
        self.document._validate(value)


class ListType(FieldType):
    """Support a list of typed values."""

    def __init__(self, typ):
        """Create a list type using the given type."""
        if is_list_type(typ) or is_list_obj(typ) and len(typ) == 0:
            self.typ = None
        elif is_list_obj(typ):
            self.typ = FieldType.create(typ[0])

    def encode_element(self, cls, name, value):
        """Return the encoded value for a single list element."""
        if self.typ:
            return self.typ.encode(cls, name, value)
        return value

    def encode(self, cls, name, value):
        """Return the value encoded as a list of encoded values."""
        if self.typ is not None:
            encoded = []
            for item in value:
                encoded.append(self.encode_element(cls, name, item))
            return encoded
        return list(value)

    def decode(self, cls, name, value):
        """Return the value decoded as a list of decoded values."""
        if self.typ is not None:
            decoded = []
            for item in value:
                decoded.append(self.typ.decode(cls, name, item))
            return decoded
        return list(value)


class SetType(FieldType):
    """Support a set of typed values."""

    def __init__(self, typ):
        """Create a set type using the given type."""
        if is_set_type(typ) or is_set_obj(typ) and len(typ) == 0:
            self.typ = None
        elif is_set_obj(typ):
            self.typ = FieldType.create(list(typ)[0])

    def encode_element(self, cls, name, value):
        """Return the encoded value for a single set element."""
        if self.typ:
            return self.typ.encode(cls, name, value)
        return value

    def encode(self, cls, name, value):
        """Return the value encoded as a set of encoded values."""
        if self.typ is not None:
            encoded = []
            for item in value:
                encoded.append(self.encode_element(cls, name, item))
            return encoded
        return list(value)

    def decode(self, cls, name, value):
        """Return the value decoded as a list of decoded values."""
        if self.typ is not None:
            decoded = set()
            for item in value:
                decoded.add(self.typ.decode(cls, name, item))
            return decoded
        return set(value)


class DictType(FieldType):
    """Support a list of type dict values with strings for keys."""

    def __init__(self, typ):
        """Create s dict type using the given type."""
        if is_dict_type(typ) or is_dict_obj(typ) and len(typ) == 0:
            self.typ = None
        elif is_dict_obj(typ):
            self.typ = FieldType.create(typ.values()[0])

    def encode(self, cls, name, value):
        """Return the value encoded as a dict of encoded values."""
        if self.typ is not None:
            encoded = OrderedDict()
            for key, item in value.iteritems():
                encoded[str(key)] = self.typ.encode(cls, name, item)
            return encoded
        return OrderedDict(value)

    def decode(self, cls, name, value):
        """Return the value decoded as a list of decoded values."""
        if self.typ is not None:
            decoded = OrderedDict()
            for key, item in value.iteritems():
                decoded[key] = self.typ.decode(cls, name, item)
            return decoded
        return OrderedDict(value)


register_field_type(is_date_type, DateType)
register_field_type(is_datetime_type, DateTimeType)
register_field_type(is_time_type, TimeType)
register_field_type(is_document_type, DocumentType)
register_field_type(lambda t: is_list_type(t) or is_list_obj(t), ListType)
register_field_type(lambda t: is_set_type(t) or is_set_obj(t), SetType)
register_field_type(is_dict_type, DictType)
