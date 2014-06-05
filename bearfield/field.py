from .errors import EncodingError
from .types import FieldType


class Field(object):
    """A field object defines how a document field behaves."""

    def __init__(self, typ, require=True, default=None, strict=True):
        """
        Initialize a new field. typ is the type of the field and may be a FieldType of a built-in
        Python type. require is a boolean that indicates whether or not the field is required.
        default is the default value to be stored if the field's value is None. strict determines
        whether or not type conversion and validation should occur during storage and retrieval of
        the field.
        """
        self.typ = FieldType.create(typ)
        self.require = require
        self.default = default
        self.strict = strict
        self.validators = [self.typ.validate]

    def __call__(field, doc, name):
        @property
        def var(self):
            if name not in self._attrs:
                value = self._raw.get(name)
                if value is not None:
                    try:
                        value = field.decode(self.__class__, name, value)
                    except EncodingError as e:
                        raise TypeError(e)
                self._attrs[name] = value
            return self._attrs[name]

        @var.setter
        def setter(self, value):
            self._attrs[name] = value
            self._dirty.add(name)
            if self._partial:
                self._partial.add(name)

        return setter

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
