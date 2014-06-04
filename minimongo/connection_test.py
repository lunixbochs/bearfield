"""Tests for the connection module."""
import unittest
from minimongo import connection, errors
from pymongo import MongoClient
from pymongo.errors import AutoReconnect

uri = 'mongodb://localhost/test'


class TestConnection(unittest.TestCase):
    """Test the Connection class."""

    def test_client(self):
        """Connection.client"""
        con = connection.Connection(uri)
        self.assertIsNone(con._client, "client is not None prior to use")
        self.assertIsInstance(con.client, MongoClient, "client is not a MongoClient")
        self.assertTrue(con.client.alive(), "open client is not alive")
        con.close()
        self.assertFalse(con.client.alive(), "closed client is alive")

    def test_database(self):
        """Connection.database"""
        con = connection.Connection(uri)
        try:
            self.assertEqual(con.database.name, 'test', "incorrect database returned")
        finally:
            con.close()

    def test_collection(self):  
        """Connection.__getitem__"""
        prefix = 'units_'
        name = 'test'
        con = connection.Connection(uri, prefix=prefix)
        try:
            collection = con[name]
            self.assertIsInstance(collection, connection.CollectionProxy, "collection proxy not returned")
            self.assertEqual(collection.name, prefix + name, "incorrect collection returned")

            collection = con[None]
            self.assertIsNone(
                collection, "connection did not return None for empty collection name")
        finally:
            con.close()

    def test_autoreconnect(self):
        """Connection.autoreconnect"""

        def func(*args, **kwargs):
            if self.tries > 0:
                self.tries -= 1
                raise AutoReconnect("tries == {}".format(self.tries))
            return True

        self.tries = 1
        con = connection.Connection(uri)
        try:
            reconnect_func = con.autoreconnect(func)
            self.assertTrue(reconnect_func(), "autoreconnect func returned incorrect value")
        finally:
            con.close()

        self.tries = 5
        con = connection.Connection(uri, retries=1)
        try:
            reconnect_func = con.autoreconnect(func)
            self.assertRaises(AutoReconnect, reconnect_func)
        finally:
            con.close()


class TestConnectionProxy(unittest.TestCase):
    """Test ConnectionProxy class."""

    def setUp(self):
        self.prefix = 'units_'
        self.name = 'test'
        self.con = connection.Connection(uri, prefix=self.prefix)

    def tearDown(self):
        name = self.con.database.name
        self.con.client.drop_database(name)
        self.con.close()

    def test_attribute(self):
        """ConnectionProxy.__getitem__(`attribute`)"""
        collection = self.con[self.name]
        self.assertEqual(
            collection.name, self.prefix + self.name, "incorrect value for collection.name")

    def test_method(self):
        """ConnectionProxy.__getitem__(`method`)"""
        collection = self.con[self.name]
        want_doc = {'a': 'aye', 'b': 'bee'}
        want_doc['_id'] = collection.insert(want_doc, manipulate=True)
        have_doc = collection.find_one({'_id': want_doc['_id']})
        self.assertEqual(have_doc, want_doc, "collection proxy methods are not sane")


class TestFunctions(unittest.TestCase):
    """Test module functions."""

    def test_get(self):
        """connection.get_connection"""
        con = connection.Connection(uri)
        try:
            name = 'test'
            connection.connections[name] = con
            self.assertEqual(
                connection.get_connection(name), con, "returned connection is incorrect")
        finally:
            con.close()
            connection.connections = {}
        
    def test_register(self):
        """connection.register_connection"""
        con = connection.Connection(uri)
        try:
            name = 'test'
            connection.register_connection(name, con)
            self.assertEquals(
                connection.connections[name], con, "registered connection is incorrect")
        finally:
            con.close()
            connection.connections = {}

    def test_initialize(self):
        """Connection.initialize_connections"""
        test1 = 'mongodb://localhost/test1'
        test2 = 'mongodb://localhost/test2'
        prefix2 = 'units_'
        config = {
            'test1': test1,
            'test2': {
                'uri': test2,
                'prefix': prefix2,
            },
        }

        try:
            connection.initialize_connections(config)
            con1 = connection.get_connection('test1')
            self.assertTrue(con1.client.alive(), "con1 is not alive")
            self.assertEqual(con1.prefix, "", "con1 prefix is incorrect")
            self.assertEqual(con1.database.name, "test1", "con1 database is incorrect")

            con2 = connection.get_connection('test2')
            self.assertTrue(con2.client.alive(), "con2 is not alive")
            self.assertEqual(con2.prefix, prefix2, "con2 prefix is incorrect")
            self.assertEqual(con2.database.name, "test2", "con2 database is incorrect")

            self.assertRaises(
                errors.ConfigError, connection.initialize_connections, {'broken': ''})
            self.assertRaises(
                errors.ConfigError, connection.initialize_connections, {'broken': {'uri': ''}})
        finally:
            for name, con in connection.connections.iteritems():
                con.close()
