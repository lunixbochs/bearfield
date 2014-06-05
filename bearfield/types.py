"""Define additional field types that require encodeing and/or decoding."""
from datetime import date, datetime, time
from errors import EncodingError

epoch = date(1970, 1, 1)
registered_field_types = []


def is_field_type(typ):
    """Return True if the type looks like a FieldType."""
    return isinstance(typ, FieldType)


def is_date_type(typ):
    """Return True if type is a date."""
    return issubclass(typ, date) and not issubclass(typ, datetime)


def is_datetime_type(typ):
    """Return True if type is a datetime."""
    return issubclass(typ, datetime)


def is_time_type(typ):
    """Return True if type is a time."""
    return issubclass(typ, time)


def is_document_type(obj):
    """Return True if type is a Document."""
    from .document import Document
    return issubclass(obj, Document)


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
        if issubclass(builtin, basestring):
            builtin = unicode
        self.builtin = builtin

    def encode(self, cls, name, value):
        """Return the encoded value."""
        try:
            return self.builtin(value)
        except (TypeError, ValueError) as e:
            raise EncodingError(cls, name, value, True, e)


class DateType(FieldType):
    """Support date values."""

    def encode(self, cls, name, value):
        """Return a date value as a datetime."""
        if is_datetime_obj(value):
            value = value.date()
        if is_date_obj(value):
            value = datetime.combine(value, time(0))
        if not is_datetime_obj(value):
            raise EncodingError(cls, name, value, True)
        return value

    def decode(self, cls, name, value):
        """Return the date value from the stored datetime."""
        if not is_datetime_obj(value):
            raise EncodingError(cls, name, value, False)
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
            raise EncodingError(cls, name, value, True)
        return value

    def decode(self, cls, name, value):
        """Return the datetime value for the stored value."""
        if not is_datetime_obj(value):
            raise EncodingError(cls, name, value, False)
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
            raise EncodingError(cls, name, value, True)
        return value

    def decode(self, cls, name, value):
        """Return the time value from the stored datetime."""
        if is_datetime_obj(value):
            return value.time()
        raise EncodingError(cls, name, value, False)


class DocumentType(FieldType):
    """Support subdocuments."""

    def __init__(self, document):
        """Create a document type object with the given document class."""
        self.document = document

    def encode(self, cls, name, value):
        """Return the value encoded as a raw subdocument."""
        if is_document_obj(value):
            return value._encode()
        raise EncodingError(cls, name, value, True)

    def decode(self, cls, name, value):
        """Return the value decoded as a subdocument object."""
        if hasattr(value, 'get'):
            return self.document._decode(value)
        raise EncodingError(cls, name, value, False)

    def validate(self, cls, name, value):
        """Raise ValidationError if the field fails to validate."""
        self.document._validate(value)


register_field_type(is_date_type, DateType)
register_field_type(is_datetime_type, DateTimeType)
register_field_type(is_time_type, TimeType)
register_field_type(is_document_type, DocumentType)
