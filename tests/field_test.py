"""Tests for the field module."""
from __future__ import absolute_import
import unittest
from datetime import date, datetime, time
from bearfield import document, errors
from bearfield.field import BaseField, Field


class ForFields(document.Document):
    date = Field(date)


class TestField(unittest.TestCase):
    """Test Field class."""

    def test_base(self):
        dt = datetime.now().date()
        doc = ForFields(date=dt)
        field = BaseField()
        self.assertEqual(field.encode(doc, 'date', doc.date), dt)
        self.assertEqual(field.decode(doc, 'date', doc.date), dt)

    def test_getter(self):
        """Field.getter"""
        dt = datetime.now().date()
        doc = ForFields(date=dt)
        field = ForFields._meta.get_field('date')

        self.assertEqual(field.getter(doc, 'date'), dt)
        doc._reset({'date': 'five'})
        self.assertRaises(TypeError, field.getter, doc, 'date')

    def test_setter(self):
        """Field.setter"""
        dt = datetime.now().date()
        doc = ForFields(date=dt)
        field = ForFields._meta.get_field('date')

        field.setter(doc, 'date', dt)
        self.assertIsNone(doc._raw['date'])
        self.assertEqual(doc._attrs['date'], dt)
        self.assertTrue('date' in doc._dirty)

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
