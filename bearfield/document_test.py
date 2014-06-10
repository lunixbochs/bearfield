"""Test document module."""
from bearfield import connection, document, errors, test, Field, Q
from datetime import datetime


class WithFields(document.Document):
    class Meta:
        connection = 'test'
    index = Field(int)
    name = Field(str)
    optional = Field(str, require=False)


class WithDate(document.Document):
    class Meta:
        connection = 'test'
    index = Field(int)
    timestamp = Field(datetime)


class WithCollection(document.Document):
    class Meta:
        connection = 'test'
        collection = 'other'
    index = Field(int)
    name = Field(str)


class SubDocument(document.Document):
    index = Field(int)
    name = Field(str)


class TopDocument(document.Document):
    class Meta:
        connection = 'test'
    sub = Field(SubDocument)


class Partial(document.Document):
    class Meta:
        connection = 'test'
    index = Field(int)
    name = Field(str)
    type = Field(str)


class TestDocument(test.TestCase):
    """Test Document class."""

    def validate_save(self, collection, document, raw):
        collection = self.connection[collection]
        have = collection.find_one({'_id': document._id})
        self.assertIsNotNone(have, "document was not saved")
        _id = have.pop('_id', None)
        self.assertIsNotNone(_id, "stored document has no id")
        self.assertEqual(_id, document._id, "document id is incorrect")
        self.assertEqual(have, raw, "stored document is incorrect")
        collection.remove()

    def test_save(self):
        """Document.save"""
        raw = {'index': 3, 'name': 'the third'}
        doc = WithFields(index=3, name='the third')
        doc.save()
        self.validate_save('with_fields', doc, raw)

    def test_insert(self):
        """Document.insert"""
        raw = {'index': 1, 'name': 'the first'}
        doc = WithFields(index=1, name='the first')
        doc.insert()
        self.validate_save('with_fields', doc, raw)

    def test_update(self):
        """Document.update"""
        raw = {'index': 5, 'name': 'the fifth'}
        doc = WithFields(index=5, name='the fourth', optional='yes')
        self.assertRaises(errors.OperationError, doc.update)
        doc.save()
        doc.name = 'the fifth'
        doc.optional = None
        self.assertTrue(doc.update(), "operational update did not return true")
        self.assertFalse(doc.update(), "noop update did not return false")
        self.validate_save('with_fields', doc, raw)

    def test_remove(self):
        """Document.remove"""
        doc = WithFields(index=3, name='the third')
        self.assertFalse(doc.remove(), "remove returned true before save")
        doc.save()
        _id = doc._id
        self.assertTrue(doc.remove(), "remove returned false after save")

        collection = self.connection['document']
        self.assertIsNone(collection.find_one({'_id': _id}), "document not removed")
        collection.remove()

    def test_validate(self):
        """Document._validate"""
        doc = WithDate(index=1)
        self.assertRaises(errors.ValidationError, doc.save)

        doc.timestamp = 'invalid'
        self.assertRaises(errors.EncodingError, doc.save)

        doc.timestamp = datetime.now()
        doc.save()
        doc._meta.get_collection().remove()

    def test_find(self):
        """Document.find"""
        WithFields(index=2, name='the second').save()
        WithFields(index=3, name='the third').save()
        WithFields(index=4, name='the fourth').save()

        docs = WithFields.find()
        count = len(docs)
        self.assertEqual(count, 3, "find() returned incorrect number of documents")

        docs = list(docs)
        self.assertEqual(len(docs), 3, "document list has incorrect length")

        criteria = {'index': {'$gt': 2}}
        docs = WithFields.find(criteria)
        count = len(docs)
        self.assertEqual(
            len(docs), 2, "find({}) returned incorrect number of documents")

        count = WithFields.find().remove()
        self.assertEqual(count, 3, "find().remove() returned incorrect number of documents")

    def test_find_one(self):
        """Document.find_one"""
        doc1 = WithFields(index=2, name='the second')
        doc1.save()
        doc2 = WithFields(index=3, name='the third')
        doc2.save()

        doc = WithFields.find_one()
        self.assertIn(doc._id, {doc1._id, doc2._id}, "returned incorrect document")

        q = Q({'name': 'the second'})
        doc = WithFields.find_one(q)
        self.assertEqual(doc._id, doc1._id, "returned incorrect document")
        doc._meta.get_collection().remove()

    def test_find_and_modify(self):
        """Document.find_and_modify"""
        doc1 = WithFields(index=2, name='the fourth')
        doc1.save()

        doc = WithFields.find_and_modify({'index': 2}, {'$set': {'name': 'the second'}})
        self.assertEqual(doc.name, 'the fourth', "old value not returned")
        doc = WithFields.find_one()
        self.assertEqual(doc.name, 'the second', "valid update did not occur")

        doc = WithFields.find_and_modify({'index': 3}, {'$set': {'name': 'the third'}})
        self.assertIsNone(doc, "invalid update did occur")
        doc1._meta.get_collection().remove()

    def test_subdocument(self):
        """Document.save/find with subdocument"""
        self.assertFalse(
            WithFields._meta.subdocument, "document incorrectly marked as subdocument")
        self.assertTrue(
            SubDocument._meta.subdocument, "subdocument incorrectly marked as document")
        self.assertRaises(
            errors.OperationError, SubDocument.find, "subdocument does not error on find")

        raw = {'sub': {'index': 20, 'name': 'the twentieth'}}
        sub = SubDocument(index=20, name='the twentieth')
        doc = TopDocument(sub=sub)
        doc.save()

        doc = TopDocument.find_one()
        self.assertEqual(doc._encode()['sub'], raw['sub'], "returned subdocument is incorrect")
        self.validate_save('top_document', doc, raw)

    def test_meta_get_collection(self):
        """Document._meta.get_collection"""
        collection = WithCollection._meta.get_collection()
        self.assertEqual(collection.name, 'other', "returned incorrect collection")

    def test_meta_get_connection(self):
        """Document._meta.get_connection"""
        con = WithFields._meta.get_connection('test')
        self.assertEqual(con, self.connection, "returned incorrect connection")
        con = WithFields._meta.get_connection(self.connection)
        self.assertEqual(con, self.connection, "returned incorrect connection")

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


class TestPartialDocument(test.TestCase):
    """Test partial Document objects."""
    def test_save(self):
        """Document.save (partial)"""
        raw = {'index': 1, 'name': 'the first'}
        doc = Partial._decode(raw, raw.keys())
        self.assertRaises(errors.OperationError, doc.save)

    def test_insert(self):
        """Document.insert (partial)"""
        raw = {'index': 1, 'name': 'the first'}
        doc = Partial._decode(raw, raw.keys())
        doc.insert()
        _id = doc._id

        want = {'_id': _id}
        want.update(raw)
        doc = Partial.find_one({'_id': _id})
        self.assertEqual(doc._encode(), want, "stored document is invalid")
        self.remove(Partial)

    def test_update(self):
        """Document.update (partial)"""
        raw = {'index': 1, 'name': 'the last'}
        doc = Partial._decode(raw, raw.keys())
        doc.insert()
        doc.name = 'the first'
        doc.update()

        doc = Partial.find_one({'_id': doc._id})
        self.assertEqual(doc.name, 'the first', "document not updated")
        self.remove(Partial)

    def test_find(self):
        """Document.find (partial)"""
        Partial(index=1, name='the first', type='the best kind').save()
        docs = Partial.find({'index': 1}, ['type'])
        want = {'_id': docs[0]._id, 'type': 'the best kind'}
        have = docs[0]._encode()
        self.assertEquals(have, want, "found document is incorrect")
        self.remove(Partial)

    def test_find_one(self):
        """Document.find_one (partial)"""
        Partial(index=1, name='the first', type='the best kind').save()
        doc = Partial.find_one({'index': 1}, ['type'])
        want = {'_id': doc._id, 'type': 'the best kind'}
        have = doc._encode()
        self.assertEquals(have, want, "found document is incorrect")
        self.remove(Partial)

    def test_find_and_modify(self):
        """Document.find_and_modify (partial)"""
        Partial(index=1, name='the first', type='the worst kind').save()
        doc = Partial.find_and_modify(
            {'index': 1}, {'$set': {'type': 'the best kind'}}, ['type'])
        want = {'_id': doc._id, 'type': 'the worst kind'}
        have = doc._encode()
        self.assertEquals(have, want, "found document is incorrect")
        self.remove(Partial)
