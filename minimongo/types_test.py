"""Tests for the types module."""
import unittest
from datetime import date, datetime, time
from minimongo import errors, types


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
        check = lambda t: True
        field_type = ExampleType

        want = list(types.registered_field_types)
        want.append((check, field_type))

        types.register_field_type(check, field_type)
        self.assertEqual(types.registered_field_types, want, "failed to add field type")


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


class TestBuiltinType(unittest.TestCase):
    """Test the BuiltinType class."""

    def test_encode(self):
        """BuiltinType.encode"""
        typ = types.BuiltinType(str)
        value = typ.encode('test', 'test', 12)
        self.assertIsInstance(value, unicode, "returned value is not unicode")
        self.assertEqual(value, '12', "returned unicode value is incorrect")

        typ = types.BuiltinType(int)
        value = typ.encode('test', 'test', 12.3)
        self.assertIsInstance(value, int, "returned value is not an int")
        self.assertEqual(value, 12, "returned int value is incorrect")

    def test_decode(self):
        """BuiltinType.decode"""
        typ = types.BuiltinType(str)
        value = typ.decode('test', 'test', u'test')
        self.assertIsInstance(value, unicode, "returned value is not unicode")
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
