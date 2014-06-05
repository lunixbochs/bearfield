"""Tests for the cursor module."""
import unittest
from bearfield import cursor, Connection, Document, Field, Query

uri = 'mongodb://localhost/test'


class TestCursor(unittest.TestCase):
    """Test the Cursor class."""

    class Document(Document):
        class Meta:
            connection = 'test'
        index = Field(int)
        name = Field(str)

    def setUp(self):
        self.con = Connection(uri)
        self.collection = self.con['cursor']
        self.docs = [
            {'index': 1, 'name': 'first'},
            {'index': 2, 'name': 'second'},
        ]

        for doc in self.docs:
            doc['_id'] = self.collection.insert(doc)

    def tearDown(self):
        name = self.con.database.name
        self.con.client.drop_database(name)
        self.con.close()

    def test_connection(self):
        """Cursor.connection"""
        cur = cursor.Cursor(self.Document(), self.collection, None, None)
        self.assertEqual(cur.connection, self.con, "cursor connection is incorrect")

    def test_find(self):
        """Cursor.find"""
        q1 = Query({'index': 1})
        q2 = Query({'name': 'first'})
        qr = q1 & q2

        cur = cursor.Cursor(self.Document(), self.collection, q1, None)
        cur = cur.find(q2)
        self.assertEqual(cur.query.criteria, qr.criteria, "cursor has invalid criteria")

    def test_getitem(self):
        """Cursor.__getitem___"""
        cur = cursor.Cursor(self.Document(), self.collection, {'index': 1}, None)
        doc = cur[0]
        have = doc._encode()
        want = {'_id': doc._id}
        want.update(self.docs[0])
        self.assertEqual(have, want, "returned document is incorrect")

    def test_iter(self):
        """Cursor.__iter__"""
        cur = cursor.Cursor(self.Document(), self.collection, {'index': 1}, None)
        it = cur.__iter__()
        self.assertIsInstance(it, cursor.Cursor, "returned value has invalid type")

    def test_close(self):
        """Cursor.close"""
        cur = cursor.Cursor(self.Document(), self.collection, {'index': 1}, None)
        cur.close()
        len(cur)
        cur.close()
