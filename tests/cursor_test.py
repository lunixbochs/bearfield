"""Tests for the cursor module."""
from __future__ import absolute_import
from . import common
from bearfield import cursor, Document, Field, Query


class TestCursor(common.TestCase):
    """Test the Cursor class."""

    class Document(Document):
        class Meta:
            connection = 'test'
        index = Field(int)
        name = Field(str)

    def setUp(self):
        super(TestCursor, self).setUp()
        self.collection = self.connection['cursor']
        self.docs = [
            {'index': 1, 'name': 'first'},
            {'index': 2, 'name': 'second'},
        ]

        for doc in self.docs:
            doc['_id'] = self.collection.insert(doc)

    def test_connection(self):
        """Cursor.connection"""
        cur = cursor.Cursor(self.Document(), self.collection, None, None, False)
        self.assertEqual(cur.connection, self.connection, "cursor connection is incorrect")

    def test_find(self):
        """Cursor.find"""
        q1 = Query({'index': 1})
        q2 = Query({'name': 'first'})
        qr = q1 & q2

        cur = cursor.Cursor(self.Document(), self.collection, q1, None, False)
        cur = cur.find(q2)
        self.assertEqual(cur.query.criteria, qr.criteria, "cursor has invalid criteria")

    def test_getitem(self):
        """Cursor.__getitem___"""
        cur = cursor.Cursor(self.Document(), self.collection, {'index': 1}, None, False)
        doc = cur[0]
        have = doc._encode()
        want = {'_id': doc._id}
        want.update(self.docs[0])
        self.assertEqual(have, want, "returned document is incorrect")

    def test_iter(self):
        """Cursor.__iter__"""
        cur = cursor.Cursor(self.Document(), self.collection, {'index': 1}, None, False)
        it = cur.__iter__()
        self.assertIsInstance(it, cursor.Cursor, "returned value has invalid type")

    def test_close(self):
        """Cursor.close"""
        cur = cursor.Cursor(self.Document(), self.collection, {'index': 1}, None, False)
        cur.close()
        cur.count()
        cur.close()
