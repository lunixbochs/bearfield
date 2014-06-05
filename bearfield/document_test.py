"""Test document module."""
import unittest
from datetime import datetime
from bearfield import connection, document, errors, Field, Q

uri = 'mongodb://localhost/test'


class Address(document.Document):
    """An address for subdocument testing."""
    street = Field(str)
    city = Field(str)
    state = Field(str)
    zipcode = Field(int) 


class Location(document.Document):
    """A location for document testing."""
    class Meta:
        connection = 'test'

    name = Field(str)
    billing = Field(Address)
    shipping = Field(Address, require=False)


class TestDocument(unittest.TestCase):
    """Test Document class."""
    class Document(document.Document):
        class Meta:
            connection = 'test'
        index = Field(int)
        name = Field(str)
        optional = Field(str, require=False)

    class DatedDocument(document.Document): 
        class Meta:
            connection = 'test'
        index = Field(int)
        timestamp = Field(datetime)

    class OtherDocument(document.Document):
        class Meta:
            connection = 'test'
            collection = 'other'
        index = Field(int)
        name = Field(str)

    class SubDocument(document.Document):
        index = Field(int)
        name = Field(str)

    def validate_save(self, collection, document, raw):
        collection = self.con[collection]
        have = collection.find_one({'_id': document._id})
        self.assertIsNotNone(have, "document was not saved")
        _id = have.pop('_id', None)
        self.assertIsNotNone(_id, "stored document has no id")
        self.assertEqual(_id, document._id, "document id is incorrect")
        self.assertEqual(have, raw, "stored document is incorrect")
        collection.remove()

    def setUp(self):
        self.con = connection.Connection(uri)
        connection.register_connection('test', self.con)

    def tearDown(self):
        name = self.con.database.name
        self.con.client.drop_database(name)
        self.con.close()

    def test_save(self):
        """Document.save"""
        raw = {'index': 3, 'name': 'the third'}
        doc = self.Document(index=3, name='the third')
        doc.save()
        self.validate_save('document', doc, raw)

    def test_insert(self):
        """Document.insert"""
        raw = {'index': 1, 'name': 'the first'}
        doc = self.Document(index=1, name='the first')
        doc.insert()
        self.validate_save('document', doc, raw)

    def test_update(self):
        """Document.update"""
        raw = {'index': 5, 'name': 'the fifth'}
        doc = self.Document(index=5, name='the fourth', optional='yes')
        self.assertRaises(errors.OperationError, doc.update)
        doc.save()
        doc.name = 'the fifth'
        doc.optional = None
        self.assertTrue(doc.update(), "operational update did not return true")
        self.assertFalse(doc.update(), "noop update did not return false")
        self.validate_save('document', doc, raw)

    def test_remove(self):
        """Document.remove"""
        doc = self.Document(index=3, name='the third')
        self.assertFalse(doc.remove(), "remove returned true before save")
        doc.save()
        _id = doc._id
        self.assertTrue(doc.remove(), "remove returned false after save")

        collection = self.con['document']
        self.assertIsNone(collection.find_one({'_id': _id}), "document not removed")
        collection.remove()

    def test_validate(self):
        """Document._validate"""
        doc = self.DatedDocument(index=1)
        self.assertRaises(errors.ValidationError, doc.save)

        doc.timestamp = 'invalid'
        self.assertRaises(errors.EncodingError, doc.save)

        doc.timestamp = datetime.now()
        doc.save()
        doc._meta.get_collection().remove()

    def test_find(self):
        """Document.find"""
        self.Document(index=2, name='the second').save()
        self.Document(index=3, name='the third').save()
        self.Document(index=4, name='the fourth').save()

        docs = self.Document.find()
        count = len(docs)
        self.assertEqual(count, 3, "find() returned incorrect number of documents")

        docs = list(docs)
        self.assertEqual(len(docs), 3, "document list has incorrect length")

        criteria = {'index': {'$gt': 2}}
        docs = self.Document.find(criteria)
        count = len(docs)
        self.assertEqual(
            len(docs), 2, "find({}) returned incorrect number of documents")

        count = self.Document.find().remove()
        self.assertEqual(count, 3, "find().remove() returned incorrect number of documents")

    def test_find_one(self):
        """Document.find_one"""
        doc1 = self.Document(index=2, name='the second')
        doc1.save()
        doc2 = self.Document(index=3, name='the third')
        doc2.save()

        doc = self.Document.find_one()
        self.assertIn(doc._id, {doc1._id, doc2._id}, "returned incorrect document")

        q = Q({'name': 'the second'})
        doc = self.Document.find_one(q)
        self.assertEqual(doc._id, doc1._id, "returned incorrect document")

    def test_find_and_modify(self):
        """Document.find_and_modify"""
        doc1 = self.Document(index=2, name='the fourth')
        doc1.save()

        doc = self.Document.find_and_modify({'index': 2}, {'$set': {'name': 'the second'}})
        self.assertEqual(doc.name, 'the second', "valid update did not occur")

        doc = self.Document.find_and_modify({'index': 3}, {'$set': {'name': 'the third'}})
        self.assertIsNone(doc, "invalid update did occur")

    def test_subdocument(self):
        """Document.save/find with subdocument"""
        self.assertFalse(
            self.Document._meta.subdocument, "document incorrectly marked as subdocument")
        self.assertTrue(
            self.SubDocument._meta.subdocument, "subdocument incorrectly marked as document")
        self.assertRaises(
            errors.OperationError, self.SubDocument.find, "subdocument does not error on find")

        class TopDocument(document.Document):
            class Meta:
                connection = 'test'
            sub = Field(self.SubDocument)

        raw = {'sub': {'index': 20, 'name': 'the twentieth'}}
        sub = self.SubDocument(index=20, name='the twentieth')
        doc = TopDocument(sub=sub)
        doc.save()

        doc = TopDocument.find_one()
        self.assertEqual(doc._encode()['sub'], raw['sub'], "returned subdocument is incorrect")
        self.validate_save('top_document', doc, raw)

    def test_meta_get_collection(self):
        """Document._meta.get_collection"""
        collection = self.OtherDocument._meta.get_collection()
        self.assertEqual(collection.name, 'other', "returned incorrect collection")

    def test_meta_get_connection(self):
        """Document._meta.get_connection"""
        con = self.Document._meta.get_connection('test')
        self.assertEqual(con, self.con, "returned incorrect connection")
        con = self.Document._meta.get_connection(self.con)
        self.assertEqual(con, self.con, "returned incorrect connection")

    def test_defaults(self):
        """Document defaults"""
        class Defaults(document.Document):
            class Meta:
                connection = 'test'
            index = Field(int, default="12")
            name = Field(str)

        doc = Defaults()
        self.assertEqual(doc.index, 12, "attribute value is incorrect")
        self.assertIsNone(doc.name, "attribute value is incorrect")
        raw = doc._encode()
        self.assertEqual(raw.get('index'), 12, "encoded value is incorrect")
        self.assertIsNone(raw.get('name'), "encoded value is incorrect")


class TestPartialDocument(unittest.TestCase):
    """Test partial Document objects."""
    class Document(document.Document):
        class Meta:
            connection = 'test'
        index = Field(int)
        name = Field(str)
        type = Field(str)

    def test_save(self):
        """Document.save (partial)"""
        raw = {'index': 1, 'name': 'the first'}
        doc = self.Document._decode(raw, raw.keys())
        self.assertRaises(errors.OperationError, doc.save)

    def test_insert(self):
        """Document.insert (partial)"""
        raw = {'index': 1, 'name': 'the first'}
        doc = self.Document._decode(raw, raw.keys())
        doc.insert()
        _id = doc._id

        want = {'_id': _id}
        want.update(raw)
        doc = self.Document.find_one({'_id': _id})
        self.assertEqual(doc._encode(), want, "stored document is invalid")
        self.Document.find().remove()

    def test_update(self):
        """Document.update (partial)"""
        raw = {'index': 1, 'name': 'the last'}
        doc = self.Document._decode(raw, raw.keys())
        doc.insert()
        doc.name = 'the first'
        doc.update()

        doc = self.Document.find_one({'_id': doc._id})
        self.assertEqual(doc.name, 'the first', "document not updated")
        self.Document.find().remove()

    def test_find(self):
        """Document.find (partial)"""
        self.Document(index=1, name='the first', type='the best kind').save()
        docs = self.Document.find({'index': 1}, ['type'])
        want = {'_id': docs[0]._id, 'type': 'the best kind'}
        have = docs[0]._encode()
        self.assertEquals(have, want, "found document is incorrect") 

    def test_find_one(self):
        """Document.find_one (partial)"""
        self.Document(index=1, name='the first', type='the best kind').save()
        doc = self.Document.find_one({'index': 1}, ['type'])
        want = {'_id': doc._id, 'type': 'the best kind'}
        have = doc._encode()
        self.assertEquals(have, want, "found document is incorrect") 

    def test_find_and_modify(self):
        """Document.find_and_modify (partial)"""
        self.Document(index=1, name='the first', type='the worst kind').save()
        doc = self.Document.find_and_modify({'index': 1}, {'$set': {'type': 'the best kind'}}, ['type'])
        want = {'_id': doc._id, 'type': 'the best kind'}
        have = doc._encode()
        self.assertEquals(have, want, "found document is incorrect") 
