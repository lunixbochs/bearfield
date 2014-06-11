"""Test encoders module."""
import re
import unittest
from bearfield import Document, Field, encoders
from bearfield.errors import EncodingError
from collections import OrderedDict
from datetime import date, datetime, time


def sortdict(items):
    """Recursively sort a dictionary by keys."""
    ordered = OrderedDict()
    for key in sorted(items.keys()):
        value = items[key]
        if isinstance(value, dict):
            value = sortdict(value)
        ordered[key] = value
    return ordered


class Subdocument(Document):
    index = Field(int)
    name = Field(str)


class ForEncoders(Document):
    boolean = Field(bool)
    number = Field(int)
    text = Field(str)
    date = Field(date)
    datetime = Field(datetime)
    time = Field(time)
    array = Field([int])
    sub = Field(Subdocument)
    subarray = Field([Subdocument])


class ForString(object):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class TestSortEncoder(unittest.TestCase):
    """Test SortEncoder class."""

    def test_encode(self):
        """SortEncoder.encode"""
        def test(value, want):
            enc = encoders.SortEncoder(ForEncoders)
            if isinstance(want, type) and issubclass(want, Exception):
                self.assertRaises(want, enc.encode, value)
            else:
                have = enc.encode(value)
                if want is None:
                    self.assertIsNone(have)
                else:
                    self.assertEqual(have, want)

        # one field
        want = OrderedDict([('index', 1)])
        test({'index': 1}, want)
        test({'index': '1'}, want)
        test({'index': 'nope'}, EncodingError)

        # two fields
        want = OrderedDict([('index', 1), ('name', -1)])
        test({'index': 1, 'name': -1}, want)
        test({'index': '1', 'name': -1}, want)
        test({'index': '1', 'name': '-1'}, want)
        test({'index': 1, 'name': '-1'}, want)
        test({'index': 1, 'name': 'nope'}, EncodingError)
        test({'index': 'nope', 'name': -1}, EncodingError)
        test({'index': 'nope', 'name': 'nope'}, EncodingError)

        # no fields
        want = OrderedDict()
        test({}, want)

        # None
        test(None, None)

        # bad dictionary
        test('nope', EncodingError)


class TestQueryEncoder(unittest.TestCase):
    """Test QueryEncoder class."""

    def test_encode(self):
        """QueryEncoder.encode"""
        def test(value, want):
            enc = encoders.QueryEncoder(ForEncoders)
            if isinstance(want, type) and issubclass(want, Exception):
                self.assertRaises(want, enc.encode, value)
            else:
                if isinstance(value, dict):
                    value = sortdict(value)
                have = enc.encode(value)
                if want is None:
                    self.assertIsNone(have)
                else:
                    self.assertEqual(have, want)

        # test simple query (single field, multiple fields)
        test(None, None)
        want = OrderedDict([('number', 1)])
        test({'number': 1}, want)
        test({'number': '1'}, want)
        test({'number': 'one'}, EncodingError)
        want = OrderedDict([('number', None)])
        test({'number': None}, want)
        want = OrderedDict([('boolean', True)])
        test({'boolean': True}, want)
        test({'boolean': 1}, want)
        test({'boolean': 'yes'}, want)
        want = OrderedDict([('boolean', False)])
        test({'boolean': False}, want)
        test({'boolean': 0}, want)
        test({'boolean': ''}, want)
        want = OrderedDict([('number', 1), ('text', 'here')])
        test({'number': 1, 'text': 'here'}, want)
        test({'number': '1', 'text': 'here'}, want)
        test({'number': 'nope', 'text': 'here'}, EncodingError)
        want = OrderedDict([('array', [1, 2, 3])])
        test({'array': [1, 2, 3]}, want)
        test({'array': [1, 2, '3']}, want)
        test({'array': [1, 2, 'nope']}, EncodingError)

        # test field operators
        want = OrderedDict([('number', OrderedDict([('$gt', 1)]))])
        test({'number': {'$gt': 1}}, want)
        test({'number': {'$gt': 1.9}}, want)
        test({'number': {'$gt': '1'}}, want)
        test({'number': {'$gt': 'nope'}}, EncodingError)
        want = OrderedDict([('number', OrderedDict([('$gt', None)]))])
        test({'number': {'$gt': None}}, want)

        # test logical operators
        want = OrderedDict([
            ('$and', [
                OrderedDict([('number', 3)]),
                OrderedDict([('text', 'value')]),
            ])])
        test({'$and': [{'number': 3}, {'text': 'value'}]}, want)
        test({'$and': [{'number': '3'}, {'text': 'value'}]}, want)
        test({'$and': [{'number': 'nope'}, {'text': 'value'}]}, EncodingError)
        test({'$and': {'number': {'$gt': 5}}}, EncodingError)
        want = OrderedDict([('$and', None)])
        test({'$and': None}, want)

        # test negation
        want = OrderedDict([('$not', OrderedDict([('number', 5)]))])
        test({'$not': {'number': 5}}, want)
        test({'$not': {'number': '5'}}, want)
        test({'$not': {'number': 'nope'}}, EncodingError)

        # test mod operator
        want = OrderedDict([('number', OrderedDict([('$mod', [12.3, 3.1])]))])
        test({'number': {'$mod': [12.3, 3.1]}}, want)
        test({'number': {'$mod': ['12.3', 3.1]}}, want)
        test({'number': {'$mod': [12.3, '3.1']}}, want)
        test({'number': {'$mod': ['12.3', '3.1']}}, want)
        test({'number': {'$mod': ['12.3', 'nope']}}, EncodingError)
        test({'number': {'$mod': 12.3}}, EncodingError)

        # test geo operator
        want = OrderedDict([
            ('index', OrderedDict([
                ('$near', OrderedDict([
                    ('$geometry', OrderedDict([
                        ('coordinates', [1.3, 4.5]),
                        ('nope',  5),
                        ('type', 'Point'),
                    ])),
                    ('$maxDistance', 1500),
                    ('$nope', 5),
                ])),
            ])),
        ])
        value = lambda x, y, z: {
            'index': {
                '$near': {
                    '$geometry': {
                        'coordinates': [x, y],
                        'type': 'Point',
                        'nope': 5,
                    },
                    '$maxDistance': z,
                    '$nope': 5,
                }
            }
        }
        test(value(1.3, 4.5, 1500), want)
        test(value(1.3, '4.5', 1500), want)
        test(value('1.3', 4.5, '1500'), want)
        test(value('1.3', '4.5', '1500'), want)
        test(value('nope', 4.5, 1500), EncodingError)
        test(value('1.3', 'nope', 1500), EncodingError)
        test(value('1.3', 4.5, 'nope'), EncodingError)
        test({'index': {'$near': {'$geometry': [1.3, 4.5]}}}, EncodingError)
        test({'index': {'$near': [1.3, 4.5]}}, EncodingError)

        # test array element match
        want = OrderedDict([
            ('subarray', OrderedDict([
                ('$elemMatch', OrderedDict([
                    ('index', 15),
                    ('name', 'value'),
                ])),
            ])),
        ])
        test({'subarray': {'$elemMatch': {'index': 15, 'name': 'value'}}}, want)
        test({'subarray': {'$elemMatch': {'index': '15', 'name': 'value'}}}, want)
        test({'subarray': {'$elemMatch': {'index': 'nope', 'name': 'value'}}}, EncodingError)
        want = OrderedDict([
            ('nope', OrderedDict([
                ('$elemMatch', OrderedDict([
                    ('index', '15'),
                    ('name', 'value'),
                ])),
            ])),
        ])
        test({'nope': {'$elemMatch': {'index': '15', 'name': 'value'}}}, want)

        # test element operators
        want = OrderedDict([
            ('nope', OrderedDict([
                ('$exists', True),
            ])),
        ])
        test({'nope': {'$exists': True}}, want)
        test({'nope': {'$exists': 1}}, want)
        test({'nope': {'$exists': 'yes'}}, want)

        want = OrderedDict([
            ('text', OrderedDict([
                ('$type', 2),
            ])),
        ])
        test({'text': {'$type': 2}}, want)
        test({'text': {'$type': '2'}}, want)
        test({'text': {'$type': 'nope'}}, EncodingError)

        # test regex operator
        want = OrderedDict([('text', re.compile('^value$'))])
        test({'text': re.compile('^value$')}, want)

        want = OrderedDict([
            ('text', OrderedDict([
                ('$options', 'i'),
                ('$regex', '^value$'),
            ])),
        ])
        test({'text': {'$regex': '^value$', '$options': 'i'}}, want)

        # test empty values
        enc = encoders.QueryEncoder(ForEncoders)
        self.assertIsNone(enc.encode(None))
        self.assertIsNone(enc.encode(''))
        self.assertIsNone(enc.encode({}))
        self.assertIsNone(enc.encode([]))
        self.assertIsNone(enc.encode(OrderedDict()))
        self.assertRaises(EncodingError, enc.encode, 'nope')


class TestUpdateEncoder(unittest.TestCase):
    """Test UpdateEncoder class."""

    def test_encode(self):
        """UpdateEncoder.encode"""
        def test(op, field, update_value, want_value):
            if isinstance(update_value, dict):
                update_value = sortdict(update_value)
            value = {op: {field: update_value}}
            enc = encoders.UpdateEncoder(ForEncoders)
            if isinstance(want_value, type) and issubclass(want_value, Exception):
                self.assertRaises(want_value, enc.encode, value)
            else:
                want = OrderedDict([(op, OrderedDict([(field, want_value)]))])
                have = enc.encode(value)
                self.assertEqual(have, want)

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
        test('$set', 'array.$', 1, 1)
        test('$set', 'array.$', '1', 1)
        test('$set', 'array.$', 'nope', EncodingError)
        test('$set', 'text.$', '1', '1')
        test('$set', 'text.$', 1, '1')
        test('$set', 'nope.$', 1, 1)
        test('$set', 'nope', 'string', 'string')
        test('$unset', 'date', '', '')
        test('$unset', 'date', date(2014, 1, 1), '')
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
        test('$pullAll', 'array', 1, 1)
        test('$pullAll', 'array', '1', 1)
        test('$pullAll', 'array', 'nope', EncodingError)
        test('$pullAll', 'nope', [1, 2], [1, 2])
        test('$pullAll', 'text', ['1', 'two'], ['1', 'two'])
        test('$pullAll', 'text', [1, 'two'], ['1', 'two'])
        test('$pullAll', 'text', '1', '1')
        test('$pullAll', 'text', 1, '1')
        test('$pushAll', 'array', [1, 2], [1, 2])
        test('$pushAll', 'array', [1, '2'], [1, 2])
        test('$pushAll', 'array', [1, 'nope'], EncodingError)
        test('$pushAll', 'array', 1, 1)
        test('$pushAll', 'array', '1', 1)
        test('$pushAll', 'array', 'nope', EncodingError)
        test('$pushAll', 'nope', [1, 2], [1, 2])
        test('$pushAll', 'text', ['1', 'two'], ['1', 'two'])
        test('$pushAll', 'text', [1, 'two'], ['1', 'two'])
        test('$pushAll', 'text', '1', '1')
        test('$pushAll', 'text', 1, '1')

        want = OrderedDict([('$each', [1, 2]), ('$sort', 1)])
        test('$push', 'array', {'$each': [1, 2], '$sort': 1}, want)
        test('$push', 'array', {'$each': [1, '2'], '$sort': 1}, want)
        test('$push', 'array', {'$each': [1, '2'], '$sort': '1'}, want)
        want = OrderedDict([('$each', [1, 2]), ('$sort', OrderedDict([('value', 1)]))])
        test('$push', 'array', {'$each': [1, 2], '$sort': {'value': 1}}, want)
        test('$push', 'array', {'$each': [1, '2'], '$sort': {'value': 1}}, want)
        test('$push', 'array', {'$each': [1, 2], '$sort': {'value': '1'}}, want)
        test('$push', 'array', {'$each': [1, '2'], '$sort': {'value': '1'}}, want)
        test('$push', 'array', {'$each': [1, 'nope'], '$sort': {'value': '1'}}, EncodingError)
        test('$push', 'array', {'$each': [1, 1], '$sort': {'value': 'nope'}}, EncodingError)
        test('$push', 'array', {'$each': [1, 2], '$sort': 'nope'}, EncodingError)
        want = OrderedDict([('$each', [1, 2]), ('$position', 0), ('$slice', 1), ('$sort', 1)])
        test('$push', 'array', {'$each': [1, 2], '$position': 0, '$slice': 1, '$sort': 1}, want)
        want = OrderedDict([('$nope', 32)])
        test('$push', 'array', {'$nope': 32}, want)
        test('$push', 'array', 1, 1)
        test('$push', 'array', '1', 1)
        test('$push', 'array', 'nope', EncodingError)

        want = OrderedDict([('and', 5)])
        test('$bit', 'number', OrderedDict([('and', 5)]), want)
        test('$bit', 'number', OrderedDict([('and', '5')]), want)
        test('$bit', 'number', OrderedDict([('and', 'nope')]), EncodingError)
        test('$bit', 'number', 12, EncodingError)

        want = OrderedDict([('array', OrderedDict([('$gte', 5)]))])
        test('$pull', 'array', {'array': {'$gte': 5}}, want)
        test('$pull', 'array', {'array': {'$gte': '5'}}, want)
        test('$pull', 'array', {'array': {'$gte': 'nope'}}, EncodingError)

        want = OrderedDict([('$each', [1, 2])])
        test('$addToSet', 'array', {'$each': [1, 2]}, want)
        test('$addToSet', 'array', {'$each': [1, '2']}, want)
        test('$addToSet', 'array', {'$each': [1, 'none']}, EncodingError)
        want = OrderedDict([('$each', [1, 2]), ('$slice', 'nope')])
        test('$addToSet', 'array', {'$each': [1, 2], '$slice': 'nope'}, want)
        test('$addToSet', 'array', 1, 1)
        test('$addToSet', 'array', '1', 1)
        test('$addToSet', 'array', 'nope', EncodingError)

        want = OrderedDict([('$type', 'timestamp')])
        test('$currentDate', 'date', {'$type': 'timestamp'}, want)
        test('$currentDate', 'date', {'$type': ForString('timestamp')}, want)
        want = OrderedDict([('$nope', 'datetime')])
        test('$currentDate', 'date', {'$nope': 'datetime'}, want)
        test('$currentDate', 'date', True, True)
        test('$currentDate', 'date', False, False)
        test('$currentDate', 'date', 'yes', True)
        test('$currentDate', 'date', '', False)

        test('$nope', 'text', 'string', 'string')

        self.assertIsNone(encoders.UpdateEncoder(ForEncoders).encode(None))
        self.assertRaises(EncodingError, encoders.UpdateEncoder(ForEncoders).encode, 'nope')
