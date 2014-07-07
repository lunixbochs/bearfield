"""Field objects."""
from .errors import EncodingError
from .types import FieldType


class BaseField(object):
    """Base field object which all fields inherit from."""
    default = None

    def getter(self, obj, name):
        """Return a document attribute as this field."""
        if name not in obj._attrs:
            value = obj._raw.get(name)
            if value is not None:
                try:
                    value = self.decode(obj.__class__, name, value)
                except EncodingError as e:
                    raise TypeError(e)
            obj._attrs[name] = value
        return obj._attrs[name]

    def setter(self, obj, name, value):
        """Set a document attribute as this field."""
        obj._attrs[name] = value
        obj._dirty.add(name)
        if obj._partial:
            obj._partial.add(name)

    def __call__(field, doc, name):
        """Return the document property used to access the field."""
        @property
        def prop(self):
            return field.getter(self, name)

        @prop.setter
        def prop(self, value):
            return field.setter(self, name, value)

        return prop

    def encode(self, cls, name, value):
        """Return the value encoded for storage in the database."""
        return value

    def decode(self, cls, name, value):
        """Return the value decoded from database storage."""
        return value

    def validate(self, cls, name, value):
        """Validate the field value. Raise ValidationError on failure."""


class Field(BaseField):
    """A field object defines how a document field behaves."""

    def __init__(self, typ, require=False, default=None, strict=True, modifier=None):
        """
        Initialize a new field. typ is the type of the field and may be a FieldType or a built-in
        Python type. require is a boolean that indicates whether or not the field is required.
        default is the default value to be stored if the field's value is None. strict determines
        whether or not type conversion and validation should occur during storage and retrieval of
        the field. modifier is a callable used to modify the value before insert or update. It
        takes the current field value as its only parameter. The return value is encoded and saved.
        """
        self.typ = FieldType.create(typ)
        self.require = require
        self.default = default
        self.strict = strict
        self.validators = [self.typ.validate]
        self.modifier = modifier

    def ensure(self, func):
        """
        Ensure the field value passes the provided validation function. The validation function
        takes three arguments: the document, the field name, and the field value. It raises
        ValidationError if validation failes.
        """
        self.validators.append(func)

    def encode(self, cls, name, value):
        """Return the value encoded for storage in the database."""
        if self.strict:
            value = self.typ.encode(cls, name, value)
        return value

    def decode(self, cls, name, value):
        """Return the value decoded from database storage."""
        if self.strict:
            value = self.typ.decode(cls, name, value)
        return value

    def validate(self, cls, name, value):
        """Validate the field value. Raise ValidationError on failure."""
        if self.strict:
            for validator in self.validators:
                validator(cls, name, value)
