"""Tests for the field module."""
import unittest
from datetime import date, datetime, time
from bearfield import errors
from bearfield.field import Field


class TestField(unittest.TestCase):
    """Test Field class."""

    def test_encode(self):
        """Field.encode"""
        field = Field(int, strict=False)
        value = field.encode('test', 'test', "12")
        self.assertEqual(value, "12", "encoded non-strict value is incorrect")

        field = Field(int)
        value = field.encode('test', 'test', "12")
        self.assertEqual(value, 12, "encoded strict value is incorrect")

        self.assertRaises(errors.EncodingError, field.encode, 'test', 'test', 'invalid')

    def test_decode(self):
        """Field.decode"""
        today = date.today()
        midnight = datetime.combine(today, time(0))

        field = Field(date, strict=False)
        value = field.decode('test', 'test', midnight)
        self.assertEqual(value, midnight, "decoded non-strict value is incorrect")

        field = Field(date)
        value = field.decode('test', 'test', midnight)
        self.assertEqual(value, today, "decoded strict value is incorrect")

        self.assertRaises(errors.EncodingError, field.decode, 'test', 'test', 'invalid')

    def test_validate(self):
        """Field.validate"""
        def validate(cls, name, value):
            if value != "validate":
                raise errors.ValidationError(None, cls, name, value)

        field = Field(str, strict=False)
        field.ensure(validate)
        field.validate('test', 'test', 'invalid')
        field.validate('test', 'test', 'validate')

        field = Field(str)
        field.ensure(validate)
        field.validate('test', 'test', 'validate')
        self.assertRaises(errors.ValidationError, field.validate, 'test', 'test', 'invalid')
