from .meta import DocumentBuilder
from .value import Value


class Document(object):
    """
    A document or subdocument. Document properties are defined in an optional Meta subclass. In
    order for a document to be saved to a database it must associate itself with a named connection
    by setting the 'connection' meta attribute to that connection name. The collection name is the
    connection prefix plus the snake cased class name of the document. This may be overridden by
    setting the 'collection' property to the desired named of the colleciton. The connection's
    prefix will still be prepended to the name.

    Fields are defined on the document by assigning Field objects to class attributes. See the
    Field class for details on field parameters. 

    A document may be provided as the type to a Field. This will cause that field to be treated as
    a subdocument.
    """
    __metaclass__ = DocumentBuilder

    @classmethod
    def find(self, criteria=None, connection=None, **options):
        """
        Query the database for documents. Return a cursor for further refining or iterating over
        the results. Additional args are passed to pymongo's find().
        """

    @classmethod
    def find_one(self, criteria=None, connection=None, **options):
        """
        Query the database for a single document. Additional args are passed to pymongo's find().
        """

    @classmethod
    def find_and_modify(cls, criteria=None, update, **options):
        """
        Query the database for a document, update it, then return the new document. Additional args
        are passed to pymongo's find_and_modify().
        """

    def save(self, connection=None, **options):
        """
        Save the model to the database. Effectively performs an insert if the _id field is None and
        a full document update otherwise. Additional args are passed to pymongo's save().
        """

    def insert(self, connection=None, **options):
        """
        Insert the document. This ignores the state of the _id field and forces an insert. This may
        necessitate setting _id to None prior to calling insert. Though this could be used to
        insert the same document into multiple databases. Additional args are passed to pymongo's
        insert().
        """

    def update(self, update=None, connection=None, **options):
        """
        Update the document in the database using the provided update statement. If update is None
        (the default) an update statement is created to set all of the dirty fields in the
        document. This uses the _id field to find the document to update and will raise an error if
        no _id is set. Additional args are passed to pymongo's update().
        """
