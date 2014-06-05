"""Tests for the cursor module."""
import unittest
from minimongo import cursor, Connection

uri = 'mongodb://localhost/test'


class TestCursor(unittest.TestCase):
    """Test the Cursor class."""

    class DocumentMock(object):
        def __init__(self, *args, **kwargs):
            self._decoded = None

        def _decode(self, item):
            item['decoded'] = True
            return item

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
        cur = cursor.Cursor(self.DocumentMock(), self.collection, None)
        self.assertEqual(cur.connection, self.con, "cursor connection is incorrect")

    def test_find(self):
        """Cursor.find"""
        criteria1 = {'index': 1}
        criteria2 = {'name': 'first'}
        criteria3 = {'$and': [criteria1, criteria2]}
        criteria4 = {'index': {'$lt': 2}}
        criteria5 = {'$and': [criteria1, criteria2, criteria4]}

        cur = cursor.Cursor(self.DocumentMock(), self.collection, criteria1)
        self.assertEqual(
            cur.criteria, criteria1,
            "first cursor has invalid criteria {} != {}".format(cur.criteria, criteria1))
        cur = cur.find(criteria2)
        self.assertEqual(
            cur.criteria, criteria3,
            "second cursor has invalid criteria {} != {}".format(cur.criteria, criteria3))
        cur = cur.find(criteria4)
        self.assertEqual(
            cur.criteria, criteria5,
            "third cursor has invalid criteria {} != {}".format(cur.criteria, criteria3))

    def test_getitem(self):
        """Cursor.__getitem___"""
        cur = cursor.Cursor(self.DocumentMock(), self.collection, {'index': 1} )
        doc = cur[0]
        self.assertEqual(doc, self.docs[0], "returned document is incorrect")

    def test_iter(self):
        """Cursor.__iter__"""
        cur = cursor.Cursor(self.DocumentMock(), self.collection, {'index': 1})
        it = cur.__iter__()
        self.assertIsInstance(it, cursor.Cursor, "returned value has invalid type")

    def test_close(self):
        """Cursor.close"""
        cur = cursor.Cursor(self.DocumentMock(), self.collection, {'index': 1})
        cur.close()
        len(cur)
        cur.close()
