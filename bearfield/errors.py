"""Framework errors."""


class Error(Exception):
    """Base error type."""


class ConfigError(Error):
    """Raised on configuration error."""


class DocumentError(Error):
    """Base class for all document related errors."""
    message = "document error"

    def __init__(self, message=None, document=None, field=None, value=None):
        """Format a document or field error message."""
        message = message or self.message
        if document:
            if isinstance(document, type):
                document = document.__name__
            elif isinstance(document, object):
                document = document.__class__.__name__
            if field:
                message = "{}: {}.{} = {}".format(message, document, field, repr(value))
            else:  # pragma: no cover
                message = "{}: {}".format(message, document)
        elif field and value:
            message = "{}: {} = {}".format(message, field, repr(value))
        elif field:  # pragma: no cover
            message = "{}: {}".format(message, field)
        elif value:
            message = "{}: {}".format(message, repr(value))
        super(DocumentError, self).__init__(message)


class OperationError(DocumentError):
    """Raised when an operation fails for a document."""
    message = "operation failed"


class ValidationError(DocumentError):
    """Raised when document or field validation fails."""
    message = "value is invalid"


class EncodingError(DocumentError):
    """Raised on field encoding/decoding error."""
    encode_message = "failed to encode value"
    decode_message = "failed to decode value"

    def __init__(self, message=None, document=None, field=None, value=None, encode=True):
        """Format an encoding error message."""
        self.message = encode and self.encode_message or self.decode_message
        super(EncodingError, self).__init__(message, document, field, value)
