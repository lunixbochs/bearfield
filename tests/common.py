"""Common test utilities."""
from __future__ import absolute_import
import unittest
from bearfield import connection, document
from pymongo.collection import Collection
import six


class TestCase(unittest.TestCase):
    """TestCase class with database functionality."""
    config = {'test': 'mongodb://localhost/test'}

    def setUp(self):
        """Create database connections."""
        connection.configure(self.config)
        self.con = list(connection.connections.values())[0]

    @property
    def connection(self):
        """Return the first (by name) configured connection."""
        keys = sorted(connection.connections.keys())
        if not keys:
            return None
        return connection.connections[keys[0]]

    @property
    def connections(self):
        """Return a dictionary of configured connections."""
        return list(connection.connections.items())

    def tearDown(self):
        """Delete databases and close connections."""
        for con in connection.connections.values():
            con.client.drop_database(con.database.name)
            con.close()

    def remove(self, collection):
        """Remove collection contents."""
        if isinstance(collection, document.Document):
            collection = document.Document._meta.collection
        if isinstance(collection, six.string_types):
            for con in connection.connections.values():
                con.database[collection].remove()
        elif isinstance(collection, Collection):
            collection.remove()
