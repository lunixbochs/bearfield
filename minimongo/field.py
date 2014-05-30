from errors import ValidationError, StrictTypeError

class Field:
    def __init__(self, typ, require=True, default=None, strict=True, index=False):
        if typ in (str, unicode):
            typ = basestring

        self.typ = typ
        self.require = require
        self.default = default
        self.strict = strict
        self.index = index
        self.validators = []

    def __call__(field, name):
        @property
        def var(self):
            return self._raw[name]

        @var.setter
        def setter(self, value):
            field.validate(self.__class__.__name__, name, value)
            self._raw[name] = value
            self._dirty[name] = True

        return setter

    def ensure(self, func):
        self.validators.append(func)

    def validate(self, cls, name, value):
        typ = self.typ
        if not (typ is None or isinstance(value, typ)) and self.strict:
            try:
                # TODO: implement explicit conversion routines between types
                value = typ(value)
            except (TypeError, Exception), e:
                raise StrictTypeError(cls, name, value, e)


        for func in self.validators:
            if not func(value):
                raise ValidationError(cls, name, value)
