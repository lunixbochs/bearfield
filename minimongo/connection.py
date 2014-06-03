"""Configure active databases."""
from .errors import ConfigError
from pymongo import MongoClient
from pymongo.errors import AutoReconnect
from time import sleep

connections = {}


class Connection(object):
    """A lazy database connection."""

    def __init__(self, uri, prefix=None, retries=None, backoff=None, **options):
        """
        Initialize the connection. The URI should be a full mongodb:// URI including the datbase
        name. The prefix is optional and is a string used to prefix all collection names. The
        retries are the number of times to retry a command when pymongo raises an AutoReconnect.
        The backoff is how much time to add to the time between each successive retry. Additional
        args are passed to pymongo's MongoClient().
        """
        if retries is None or retries < 0:
            retries = 4
        if backoff is None or backoff < 0:
            backoff = 0.5
        self.uri = uri
        self.prefix = prefix or ''
        self.retries = retries
        self.backoff = backoff
        self.options = options
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
        return CollectionProxy(self, self.database[self.prefix + name])

    def autoreconnect(self, func):
        """Return the provided function decorated with autoreconnect functionality."""
        def reconnect(*args, **kwargs):
            tries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except AutoReconnect:
                    if tries >= self.retries:
                        raise
                sleep(tries * self.backoff)
                tries += 1
        return reconnect


class CollectionProxy(object):
    """Proxy method calls to collections in order to handle AutoReconnect errors."""

    def __init__(self, connection, collection):
        """Create a proxy around the provided collection."""
        self._connection = connection
        self._collection = collection

    def __getattr__(self, name):
        """Return an attribute. Methods are decorated with autoreconnect functionality."""
        value = getattr(self._collection, name)
        if hasattr(value, '__call__'):
            value = self._connection.autoreconnect(value)
        return value


def get_connection(name):
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
    for name, options in config.iteritems():
        if isinstance(options, dict):
            uri = options.pop('uri', None)
            prefix = options.pop('prefix', None)
            if uri is None:
                raise ConfigError("connection {} is missing uri".format(name))
            connection = Connection(uri, prefix, **options)
        else:
            connection = Connection(options)
        register_connection(name, connection)
