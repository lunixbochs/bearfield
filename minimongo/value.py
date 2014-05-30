# TODO: somehow actually resolve encode/decode methods?
# basically means you'll be able to say name = Field(Document)
class Value(object):
    def _encode(self):
        raise NotImplementedError

    def _decode(self):
        raise NotImplementedError
