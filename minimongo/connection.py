"""Configure active databases."""
from .errors import ConfigError
from pymongo import MongoClient

connections = {}


class Connection(object):
    """A lazy database connection."""

    def __init__(self, uri, prefix=None, options=None):
        """
        Initialize the connection. The URI should be a full mongodb:// URI including the datbase
        name. The prefix is optional and is a string used to prefix all collection names. Options
        is a dictionary of keyword args to pass to pymongo's MongoClient for finer configuration.
        """
        self.uri = uri
        self.prefix = prefix or ''
        self.options = options or {}
        self._client = None
        self._database = None

    @property
    def client(self):
        """Return the client used by this connection."""
        if self._client is None:
            self._client = MongoClient(self.uri, **self.options)
        return self._client

    @property
    def database(self):
        """Return the database used by this connection."""
        if self._database is None:
            self._database = self.client.get_default_database()
        return self._database

    def __getitem__(self, name):
        """Return a collection from the connection's database."""
        return self.database[self.prefix + name]


def find_connection(name):
    """Return a named connection or None if not found."""
    return connections.get(name)


def register_connection(name, connection):
    """Register a named connection."""
    connections[name] = connection


def initialize_connections(config):
    """
    Initialize connections from the provided configuration. The config object is a dictionary
    containing named connections. The keys of the dictionary are the names while the values are the
    configuration for each connection. The value may be a string containing the database URI or a
    dictionary with the keys 'uri' for the database URI, and 'prefix' for a string with which to
    prefix collection names. Remaining options are passed as keyworkd args to pymongo's
    MongoClient.
    """
    for name, options in configs.iteritems():
        if isinstance(options, dict):
            uri = options.pop(uri, None)
            prefix = options.pop('prefix', None)
            if uri is None:
                raise ConfigError("connection {} is missing uri".format(name))
            connection = Connection(uri, prefix, options)
        else:
            connection = Connection(options)
        register_connection(name, connection)
