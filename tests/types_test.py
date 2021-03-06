"""Tests for the types module."""
from __future__ import absolute_import
import unittest
from bearfield import errors, types, Document, Field
from collections import OrderedDict
from datetime import date, datetime, time
import six


class ExampleType(types.FieldType):
    """Valid test field type."""


class TestFunctions(unittest.TestCase):
    """Test module functions."""

    def test_is_field_type(self):
        """types.is_field_type"""
        self.assertFalse(types.is_field_type("not a field"), "returns True for string object")
        self.assertTrue(
            types.is_field_type(types.FieldType.create(str)), "returns False for builtin str type")
        self.assertTrue(types.is_field_type(ExampleType()), "returns False for ExampleType")

    def test_is_date_type(self):
        """types.is_date"""
        self.assertTrue(types.is_date_type(date), "returns False for date")
        self.assertFalse(types.is_date_type(datetime), "returns True for datetime")
        self.assertFalse(types.is_date_type(time), "returns True for time")

    def test_is_datetime_type(self):
        """types.is_datetime_type"""
        self.assertTrue(types.is_datetime_type(datetime), "returns False for datetime")
        self.assertFalse(types.is_datetime_type(date), "returns True for date")
        self.assertFalse(types.is_datetime_type(time), "returns True for time")

    def test_is_time_type(self):
        """types.is_date"""
        self.assertTrue(types.is_time_type(time), "returns False for time")
        self.assertFalse(types.is_time_type(date), "returns True for date")
        self.assertFalse(types.is_time_type(datetime), "returns True for datetime")

    def test_is_date_obj(self):
        """types.is_date"""
        now = datetime.now()
        self.assertTrue(types.is_date_obj(now.date()), "returns False for date")
        self.assertFalse(types.is_date_obj(now), "returns True for datetime")
        self.assertFalse(types.is_date_obj(now.time()), "returns True for time")

    def test_is_datetime_obj(self):
        """types.is_datetime_obj"""
        now = datetime.now()
        self.assertTrue(types.is_datetime_obj(now), "returns False for datetime")
        self.assertFalse(types.is_datetime_obj(now.date()), "returns True for date")
        self.assertFalse(types.is_datetime_obj(now.time()), "returns True for time")

    def test_is_time_obj(self):
        """types.is_date"""
        now = datetime.now()
        self.assertTrue(types.is_time_obj(now.time()), "returns False for time")
        self.assertFalse(types.is_time_obj(now.date()), "returns True for date")
        self.assertFalse(types.is_time_obj(now), "returns True for datetime")

    def test_register_field_type(self):
        """types.register_field_type"""
        old_types = list(types.registered_field_types)
        try:
            check = lambda t: True
            field_type = ExampleType

            want = list(types.registered_field_types)
            want.append((check, field_type))

            types.register_field_type(check, field_type)
            self.assertEqual(types.registered_field_types, want, "failed to add field type")
        finally:
            types.registered_field_types = old_types


class TestFieldType(unittest.TestCase):
    """Test FieldType class."""

    def test_create(self):
        """FieldType.create"""
        typ = ExampleType()
        self.assertEqual(types.FieldType.create(typ), typ, "does not return ExampleType object")

        typ = types.FieldType.create(int)
        self.assertIsInstance(typ, types.BuiltinType, "does not return BuiltinType for int")
        self.assertEqual(typ.builtin, int, "does not return BuiltinType with correct type")

        typ = types.FieldType.create(date)
        self.assertIsInstance(typ, types.DateType, "does not return DateType for date")

    def test_encode(self):
        """FieldType.encode"""
        typ = types.FieldType()
        value = "valid value"
        self.assertEqual(typ.encode('test', 'test', value), value, "does not pass through values")

    def test_decode(self):
        """FieldType.decode"""
        typ = types.FieldType()
        value = "valid value"
        self.assertEqual(typ.decode('test', 'test', value), value, "does not pass through values")


class TestBuiltinType(unittest.TestCase):
    """Test the BuiltinType class."""

    def test_encode(self):
        """BuiltinType.encode"""
        typ = types.BuiltinType(str)
        value = typ.encode('test', 'test', 12)
        self.assertIsInstance(value, six.text_type, "returned value is not unicode")
        self.assertEqual(value, '12', "returned unicode value is incorrect")

        typ = types.BuiltinType(int)
        value = typ.encode('test', 'test', 12.3)
        self.assertIsInstance(value, int, "returned value is not an int")
        self.assertEqual(value, 12, "returned int value is incorrect")
        self.assertRaises(errors.EncodingError, typ.encode, 'test', 'test', 'nan')

    def test_decode(self):
        """BuiltinType.decode"""
        typ = types.BuiltinType(str)
        value = typ.decode('test', 'test', u'test')
        self.assertIsInstance(value, six.text_type, "returned value is not unicode")
        self.assertEqual(value, u'test', "returnd string value is incorrect")


class TestDateType(unittest.TestCase):
    """Test the DateType class."""

    def test_encode(self):
        """DateType.encode"""
        typ = types.DateType()

        def test(invalue, outvalue):
            value = typ.encode('test', 'test', invalue)
            self.assertTrue(types.is_datetime_obj(value), "returned value is not datetime")
            self.assertEqual(value, outvalue, "returned date value is incorrect")

        now = datetime.now()
        today = date.today()
        test(now, datetime.combine(now.date(), time(0)))
        test(today, datetime.combine(today, time(0)))
        self.assertRaises(errors.EncodingError, typ.encode, 'test', 'test', now.time())
        self.assertRaises(errors.EncodingError, typ.encode, 'test', 'test', 36)

    def test_decode(self):
        """DateType.decode"""
        typ = types.DateType()
        today = datetime.combine(date.today(), time(0))
        value = typ.decode('test', 'test', today)
        self.assertIsInstance(value, date, "returned value is not date")
        self.assertEqual(value, today.date(), "returned date value is incorrect")
        self.assertRaises(errors.EncodingError, typ.decode, 'test', 'test', 'invalid')

    def test_create(self):
        """FieldType.create(date)"""
        typ = types.FieldType.create(date)
        self.assertIsInstance(typ, types.DateType)


class TestDateTimeType(unittest.TestCase):
    """Test the DateTimeType class."""

    def test_encode(self):
        """DateTimeType.encode"""
        typ = types.DateTimeType()

        def test(invalue, outvalue):
            value = typ.encode('test', 'test', invalue)
            self.assertTrue(types.is_datetime_obj(value), "returned value is not datetime")
            self.assertEqual(value, outvalue, "returned datetime value is incorrect")

        now = datetime.now()
        today = date.today()
        nowtime = now.time()
        test(now, now)
        test(today, datetime.combine(today, time(0)))
        test(nowtime, datetime.combine(date(1970, 1, 1), nowtime))

    def test_decode(self):
        """DateTimeType.decode"""
        typ = types.DateTimeType()
        now = datetime.now()
        value = typ.decode('test', 'test', now)
        self.assertIsInstance(value, datetime, "returned value is not datetime")
        self.assertEqual(now, value, "returned datetime value is incorrect")
        self.assertRaises(errors.EncodingError, typ.decode, 'test', 'test', 'invalid')

    def test_create(self):
        """FieldType.create(datetime)"""
        typ = types.FieldType.create(datetime)
        self.assertIsInstance(typ, types.DateTimeType)


class TestTimeType(unittest.TestCase):
    """Test the TimeType class."""

    def test_encode(self):
        """TimeType.encode"""
        typ = types.TimeType()

        def test(invalue, outvalue):
            value = typ.encode('test', 'test', invalue)
            self.assertTrue(types.is_datetime_obj(value), "returned value is not datetime")
            self.assertEqual(value, outvalue, "returned time value is incorrect")

        now = datetime.now()
        nowtime = now.time()
        want = datetime.combine(date(1970, 1, 1), nowtime)
        test(now, want)
        test(nowtime, want)
        self.assertRaises(errors.EncodingError, typ.encode, 'test', 'test', 'invalid')

    def test_decode(self):
        """TimeType.decode"""
        typ = types.TimeType()
        nowtime = datetime.combine(date(1970, 1, 1), datetime.now().time())
        value = typ.decode('test', 'test', nowtime)
        self.assertIsInstance(value, time, "returned value it not time")
        self.assertRaises(errors.EncodingError, typ.decode, 'test', 'test', 'invalid')

    def test_create(self):
        """FieldType.create(time)"""
        typ = types.FieldType.create(time)
        self.assertIsInstance(typ, types.TimeType)


class TestDocumentType(unittest.TestCase):
    """Test the DocumentType class."""

    class Doc(Document):
        index = Field(int, require=True)
        name = Field(str, require=True)

    def test_encode(self):
        """DocumentType.encode"""
        index = '12'
        name = 'the twelth'
        value = self.Doc(index=index, name=name)

        typ = types.DocumentType(self.Doc)
        raw = typ.encode('test', 'test', value)
        self.assertIsInstance(raw, dict, "returned value has incorrect type")
        self.assertEqual(raw['index'], int(index), "returned value is incorrect")
        self.assertEqual(raw['name'], str(name), "returned value is incorrect")
        self.assertRaises(errors.EncodingError, typ.encode, 'test', 'test', 'invalid')

    def test_decode(self):
        """DocumentType.decode"""
        index = 12
        name = 'the twelth'
        value = {'index': index, 'name': name}

        typ = types.DocumentType(self.Doc)
        doc = typ.decode('test', 'test', value)
        self.assertIsInstance(doc, self.Doc, "returned value has incorrect type")
        self.assertEqual(doc.index, index, "returned value is incorrect")
        self.assertEqual(doc.name, name, "returned value is incorrect")
        self.assertRaises(errors.EncodingError, typ.decode, 'test', 'test', 'invalid')

    def test_validate(self):
        """DocumentType.validate"""
        value = {'index': 12}
        typ = types.DocumentType(self.Doc)
        self.assertRaises(errors.ValidationError, typ.validate, 'test', 'test', value)


class TestListType(unittest.TestCase):
    """Test the ListType class."""

    def test_field(self):
        """Field(list)"""
        field = Field([str])
        self.assertIsInstance(field.typ, types.ListType)
        self.assertIsInstance(field.typ.typ, types.BuiltinType)
        self.assertEqual(field.typ.typ.builtin, six.text_type)

    def test_encode(self):
        """ListType.encode"""
        items = ('1', '2', 3)
        want = [1, 2, 3]
        typ = types.ListType([int])
        have = typ.encode('test', 'test', items)
        self.assertEqual(have, want, "encoded typed list value is incorrect")

        items = ('1', '2', 'some value')
        typ = types.ListType(list)
        have = typ.encode('test', 'test', items)
        self.assertEqual(have, list(items), "encoded untyped list value is incorrect")

    def test_decode(self):
        """ListType.decode"""
        typ = types.ListType([int])
        items = [1, 2, 3]
        have = typ.decode('test', 'test', items)
        self.assertEqual(have, items, "decoded typed list value is incorrect")

        typ = types.ListType(list)
        items = [1, 2, 'three']
        have = typ.decode('test', 'test', items)
        self.assertEqual(have, items, "decoded untyped list value is incorrect")


class TestSetType(unittest.TestCase):
    """Test the ListType class."""

    def test_encode(self):
        """SetType.encode"""
        items = {'1', '2', 3}
        want = {1, 2, 3}
        typ = types.SetType({int})
        have = typ.encode('test', 'test', items)
        self.assertIsInstance(have, list, "encoded set has invalid type")
        self.assertEqual(set(have), want, "encoded typed list value is incorrect")

        items = {'1', '2', 'some value'}
        typ = types.SetType(set)
        have = typ.encode('test', 'test', items)
        self.assertIsInstance(have, list, "encoded set has invalid type")
        self.assertEqual(set(have), items, "encoded untyped list value is incorrect")

    def test_decode(self):
        """SetType.decode"""
        typ = types.SetType({int})
        items = [1, 2, 3]
        have = typ.decode('test', 'test', items)
        self.assertEqual(have, set(items), "decoded typed list value is incorrect")

        typ = types.SetType(set)
        items = [1, 2, 'three']
        have = typ.decode('test', 'test', items)
        self.assertEqual(have, set(items), "decoded untyped list value is incorrect")


class TestDictType(unittest.TestCase):
    """Test the DictType class."""

    def test_encode(self):
        """DictType.encode"""
        def test(typ, items, want):
            have = typ.encode('test', 'test', items)
            self.assertIsInstance(have, OrderedDict, "returned value has incorrect type")
            self.assertEqual(dict(have), dict(want), "returned value is incorrect")

        # test regular value
        items = {'a': 'aye', 'b': 'bee'}
        want = items.copy()
        typ = types.DictType({'_': str})
        test(typ, items, want)

        # test value with non-str keys
        items = {1: '1', 4: '4'}
        want = {'1': 1, '4': 4}
        typ = types.DictType({'_': int})
        test(typ, items, want)

        # test untyped value
        items = {'one': 1, 'two': 'second'}
        want = items.copy()
        typ = types.DictType(dict)
        test(typ, items, want)

    def test_decode(self):
        """DictType.decode"""
        def test(typ, items, want):
            have = typ.decode('test', 'test', items)
            self.assertIsInstance(have, OrderedDict, "returned value has incorrect type")
            self.assertEqual(dict(have), dict(want), "returned value is incorrect")

        # test regular value
        items = {'a': 'aye', 'b': 'bee'}
        want = items.copy()
        typ = types.DictType({'_': str})
        test(typ, items, want)

        # test value with non-str keys
        items = {'1': 1, '4': 4}
        want = items.copy()
        typ = types.DictType({'_': int})
        test(typ, items, want)

        # test untyped value
        items = {'one': 1, 'two': 'second'}
        want = items.copy()
        typ = types.DictType(dict)
        test(typ, items, want)
