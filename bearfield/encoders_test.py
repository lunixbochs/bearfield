"""Test encoders module."""
import unittest
from bearfield import Document, Field, encoders
from bearfield.errors import EncodingError
from collections import OrderedDict
from datetime import date, datetime, time


class ForUpdate(Document):
    number = Field(int)
    text = Field(str)
    date = Field(date)
    datetime = Field(datetime)
    time = Field(time)
    array = Field([int])


class ForString(object):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class TestUpdateEncoder(unittest.TestCase):
    """Test UpdateEncoder class."""

    def test_operators(self):
        """UpdateEncoder Scalars"""
        def test(op, field, update_value, want_value=None):
            value = {op: {field: update_value}}
            enc = encoders.UpdateEncoder(ForUpdate)
            if isinstance(want_value, type) and issubclass(want_value, Exception):
                self.assertRaises(want_value, enc.encode, value)
            else:
                want = OrderedDict([(op, OrderedDict([(field, want_value)]))])
                have = enc.encode(value)
                self.assertEqual(have, want)

        date_ = date(2014, 1, 1)
        datet = datetime.combine(date_, time(0))
        now = datetime.now()
        nowtime = now.time()

        test('$inc', 'number', 2, 2)
        test('$inc', 'number', '2', 2)
        test('$inc', 'number', 'nope', EncodingError)
        test('$mul', 'number', 2, 2)
        test('$mul', 'number', '2', 2)
        test('$mul', 'number', 'nope', EncodingError)
        test('$rename', 'number', 'integer', 'integer')
        test('$rename', 'number', ForString('integer'), 'integer')
        test('$setOnInsert', 'text', 'insert', 'insert')
        test('$setOnInsert', 'text', 12.5, '12.5')
        test('$setOnInsert', 'array', [1, 2], [1, 2])
        test('$setOnInsert', 'array', [1, '2'], [1, 2])
        test('$setOnInsert', 'array', (1, 2), [1, 2])
        test('$setOnInsert', 'array', (1, '2'), [1, 2])
        test('$setOnInsert', 'array', (1, 'nope'), EncodingError)
        test('$set', 'text', 'update', 'update')
        test('$set', 'text', 18, '18')
        test('$set', 'array', [1, 2], [1, 2])
        test('$set', 'array', [1, '2'], [1, 2])
        test('$set', 'array', (1, 2), [1, 2])
        test('$set', 'array', (1, '2'), [1, 2])
        test('$set', 'array', (1, 'nope'), EncodingError)
        test('$unset', 'date', '', '')
        test('$unset', 'date', date_, '')
        test('$unset', 'number', 3, '')
        test('$unset', 'array', [1, 2], '')
        test('$min', 'number', 100, 100)
        test('$min', 'number', '100', 100)
        test('$min', 'number', 'nope', EncodingError)
        test('$max', 'number', 200, 200)
        test('$max', 'number', '200', 200)
        test('$max', 'number', 'nope', EncodingError)
        test('$pop', 'array', 1, 1)
        test('$pop', 'array', '1', 1)
        test('$pop', 'array', 'nope', EncodingError)
        test('$pullAll', 'array', [1, 2], [1, 2])
        test('$pullAll', 'array', [1, '2'], [1, 2])
        test('$pullAll', 'array', [1, 'nope'], EncodingError)
        test('$pushAll', 'array', [1, 2], [1, 2])
        test('$pushAll', 'array', [1, '2'], [1, 2])
        test('$pushAll', 'array', [1, 'nope'], EncodingError)
        test('$push', 'array', 1, 1)
        test('$push', 'array', '1', 1)
        test('$push', 'array', 'nope', EncodingError)

        want = OrderedDict([('and', 5)])
        test('$bit', 'number', OrderedDict([('and', 5)]), want)
        test('$bit', 'number', OrderedDict([('and', '5')]), want)
        test('$bit', 'number', OrderedDict([('and', 'nope')]), EncodingError)

        want = OrderedDict([('array', OrderedDict([('$gte', 5)]))])
        test('$pull', 'array', {'array': {'$gte': 5}}, want)
        test('$pull', 'array', {'array': {'$gte': '5'}}, want)
        test('$pull', 'array', {'array': {'$gte': 'nope'}}, EncodingError)

        want = OrderedDict([('$each', [1, 2])])
        test('$addToSet', 'array', {'$each': [1, 2]}, want)
        test('$addToSet', 'array', {'$each': [1, '2']}, want)
        test('$addToSet', 'array', {'$each': [1, 'none']}, EncodingError)
        test('$addToSet', 'array', 1, 1)
        test('$addToSet', 'array', '1', 1)
        test('$addToSet', 'array', 'nope', EncodingError)

        want = OrderedDict([('$type', 'timestamp')])
        test('$currentDate', 'date', {'$type': 'timestamp'}, want)
        test('$currentDate', 'date', {'$type': ForString('timestamp')}, want)
        test('$currentDate', 'date', True, True)
        test('$currentDate', 'date', False, False)
        test('$currentDate', 'date', 'yes', True)
        test('$currentDate', 'date', '', False)
