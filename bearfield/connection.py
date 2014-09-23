"""Configure active databases."""
from .errors import ConfigError
from pymongo import MongoClient
from pymongo.errors import AutoReconnect
from time import sleep

connections = {}


class Connection(object):
    """A lazy database connection."""

    @classmethod
    def configure(cls, config):
        """
        Create a new connection using the provided configuration. The configuration may be a uri or
        a dictionary containing values for uri, prefix. retries, and backoff. Additional options
        are passed to the MongoClient init.
        """
        if not isinstance(config, dict):
            config = {'uri': config}
        uri = config.pop('uri', None)
        if not uri:
            raise ConfigError("invalid uri: {}".format(uri))
        return cls(uri, **config)

    def __init__(self, uri, prefix=None, retries=None, backoff=None, **options):
        """
        Initialize the connection. The URI should be a full mongodb:// URI including the database
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
        if not name:
            return None
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

    def close(self):
        """Close the connection."""
        if self._client:
            self._client.close()


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


def get(name):
    """Return a named connection or None if not found."""
    return connections.get(name)


def add(name, connection=None, default=False):
    """
    Add a named connection. The connection may be a Connection object or configuration for one.
    If a connection string/object is not specified, `mongodb://localhost//{{name}}` is used.

    When default is True, the global default connection is updated. This is used
    by all models which lack an explicitly-defined connection.
    """
    if connection is None:
        connection = Connection.configure('mongodb://localhost/{}'.format(name))
    if not isinstance(connection, Connection):
        connection = Connection.configure(connection)
    if default:
        connections[None] = connection
    connections[name] = connection


def configure(config):
    """
    Initialize connections from the provided configuration. The config object is a dictionary
    containing named connections. The keys of the dictionary are the names while the values are the
    configuration for each connection. The value may be a string containing the database URI or a
    dictionary with the keys 'uri' for the database URI, and 'prefix' for a string with which to
    prefix collection names. Remaining options are passed as keyword args to pymongo's
    MongoClient.
    """
    for name, options in config.iteritems():
        add(name, options)
