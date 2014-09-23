"""Tests for the reference module."""
import common
from bearfield import Document, Field, Query, reference
from bearfield.cursor import Cursor
from collections import OrderedDict


class Child(Document):
    class Meta:
        connection = 'test'

    name = Field(str)


class Parent(Document):
    class Meta:
        connection = 'test'

    name = Field(str)
    child = reference.Reference(Child, require=False)


class TestReference(common.TestCase):
    """Test Reference class."""

    def test_getter(self):
        """Reference.getter"""
        child = Child(name='child')
        child.save()
        parent = Parent(name='parent', child=child)
        parent.save()

        ref = parent.child
        query = {'_id': child._id}
        self.assertIsInstance(ref, reference.ReferenceFinder, "reference field has invalid type")
        self.assertEqual(ref.value, child._id, "reference value is incorrect")
        self.assertEqual(ref.query.encode(Child), query, "reference query is incorrect")

        self.remove(Child)
        self.remove(Parent)

    def test_setter(self):
        """Reference.setter"""
        child = Child(name='child')
        parent = Parent(name='parent')
        self.assertRaises(ValueError, setattr, parent, 'child', child)

        child.save()

        parent = Parent(name='parent')
        parent.child = child
        self.assertEqual(parent._attrs['child'], child._id)

        parent = Parent(name='parent')
        parent.child = child._id
        self.assertEqual(parent._attrs['child'], child._id)

        parent = Parent(name='parent')
        parent.child = str(child._id)
        self.assertEqual(parent._attrs['child'], child._id)

        query = Query({'name': 'first'})
        parent = Parent(name='parent')
        parent.child = query
        self.assertEqual(parent._attrs['child'], query)

        query = {'name': 'first'}
        parent = Parent(name='parent')
        parent.child = query
        self.assertEqual(parent._attrs['child'], Query(query))

        parent = Parent(name='parent')
        self.assertRaises(TypeError, setattr, parent, 'child', 'nope')

        self.remove(Child)
        self.remove(Parent)

    def test_encode(self):
        """Reference.encode"""
        child = Child(name='child')
        child.save()
        parent = Parent(name='parent')
        self.assertEqual(parent._encode(), {'name': 'parent'})

        parent.child = child
        self.assertEqual(parent._encode(), {'name': 'parent', 'child': child._id})

        parent.child = Query({'name': 'child'})
        want = {'name': 'parent', 'child': OrderedDict({'name': 'child'})}
        self.assertEqual(parent._encode(), want)
        parent.child = {'name': 'child'}
        self.assertEqual(parent._encode(), want)

        self.remove(Child)

    def test_decode(self):
        """Reference.decode"""
        child = Child(name='child')
        child.save()

        value = {'name': 'parent', 'child': child._id}
        parent = Parent._decode(value)
        self.assertEqual(parent.child.value, child._id)

        query = {'name': 'first'}
        value = {'name': 'parent', 'child': query}
        parent = Parent._decode(value)
        self.assertEqual(parent.child.value, Query(query))

        value = {'name': 'parent', 'child': 'invalid'}
        parent = Parent._decode(value)
        self.assertRaises(TypeError, getattr, parent.child, 'value')

        self.remove(Child)

    def test_find(self):
        child = Child(name='child')
        child.save()
        parent = Parent(name='parent')
        parent.child = Query({'name': 'child'})

        cursor = parent.child.find()
        self.assertIsInstance(cursor, Cursor)
        self.assertEqual(cursor.count(), 1)
        self.assertEqual(cursor[0]._id, child._id)

        parent.child = Query({'name': 'parent'})
        cursor = parent.child.find()
        self.assertIsInstance(cursor, Cursor)
        self.assertEqual(cursor.count(), 0)

        parent.child = child
        cursor = parent.child.find()
        self.assertIsInstance(cursor, Cursor)
        self.assertEqual(cursor.count(), 1)
        self.assertEqual(cursor[0]._id, child._id)

        self.remove(Child)

    def test_find_one(self):
        child = Child(name='child')
        child.save()
        parent = Parent(name='parent', child=child)

        item = parent.child.find_one()
        self.assertIsInstance(item, Child)
        self.assertEqual(item._id, child._id)

        parent.child = None
        item = parent.child.find_one()
        self.assertIsNone(item)
