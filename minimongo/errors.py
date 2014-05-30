class ValidationError(Exception):
    def __init__(self, cls, name, value, msg=None):
        self.cls = cls
        self.name = name
        self.value = value
        self.msg = msg

    def __str__(self):
        msg = "{}.{} = {}: invalid value".format(
            self.cls, self.name, repr(self.value))
        if self.msg:
            msg = '{}\n({})'.format(msg, self.msg)
        return msg


class StrictTypeError(ValidationError):
    pass
