"""Framework errors."""

class Error(Exception):
    """Base error type.""" 


class ConfigError(Error):
    """Raised on configuration error."""


class DocumentError(Error):
    """Base class for all document related errors."""


class FieldError(DocumentError):
    """Raised on field/value error."""
    brief = "invalid field value"

    def __init__(self, cls, name, value, msg=None):
        self.cls = cls
        self.name = name
        self.value = value
        self.msg = msg

    def __str__(self):
        msg = "{}.{} = {}: {}".format(
            self.cls, self.name, repr(self.value), self.brief)
        if self.msg:
            msg = '{}\n({})'.format(msg, self.msg)
        return msg


class ValidationError(FieldError):
    """Raised when field validation fails."""
    brief = "field failed validation"


class EncodingError(FieldError):
    """Raised on field encoding/decoding error."""
    brief = "field encoding failed"
