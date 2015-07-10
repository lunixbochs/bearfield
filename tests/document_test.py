"""Test document module."""
import common
from bearfield import Field, Q, Reference, document, errors, types
from datetime import datetime


def create_document(base=None, **options):
    """Return a document class with the given meta options."""
    attrs = {'Meta': type('Meta', (object,), options)}
    if not base:
        base = document.Document
        attrs.update({
            'index': Field(int),
            'name': Field(str),
        })

    return type('CreatedDocument', (base,), attrs)


class WithFields(document.Document):
    class Meta:
        connection = 'test'
    index = Field(int)
    name = Field(str)
    optional = Field(str, require=False)


class WithDate(document.Document):
    class Meta:
        connection = 'test'
    index = Field(int, require=True)
    timestamp = Field(datetime, require=True)


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


class WithReference(document.Document):
    class Meta:
        connection = 'test'
    index = Field(int)
    sub = Field(SubDocument)
    ref = Reference(SubDocument)


class TestDocument(common.TestCase):
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

        cls = create_document(WithFields, readonly=True)
        doc = cls(index=3, name='the third')
        self.assertRaises(errors.OperationError, doc.save)

        cls = create_document(WithFields, disable_save=True)
        doc = cls(index=3, name='the third')
        self.assertRaises(errors.OperationError, doc.save)

    def test_insert(self):
        """Document.insert"""
        raw = {'index': 1, 'name': 'the first'}
        doc = WithFields(index=1, name='the first')
        doc.insert()
        self.validate_save('with_fields', doc, raw)

        cls = create_document(WithFields, readonly=True)
        doc = cls(index=1, name='the first')
        self.assertRaises(errors.OperationError, doc.insert)

        cls = create_document(WithFields, disable_insert=True)
        doc = cls(index=1, name='the first')
        self.assertRaises(errors.OperationError, doc.insert)

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

        doc = WithFields(index=5, name='the fourth', optional='yes')
        doc.save()
        self.assertTrue(
            doc.update({'$set': {'name': 'the fifth'}, '$unset': {'optional': ''}}),
            "operational update did not return true")
        self.validate_save('with_fields', doc, raw)

        cls = create_document(WithFields, readonly=True)
        doc = cls(index=5, name='the fourth', optional='yes')
        self.assertRaises(errors.OperationError, doc.update)

        cls = create_document(WithFields, disable_update=True)
        doc = cls(index=5, name='the fourth', optional='yes')
        self.assertRaises(errors.OperationError, doc.update)

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

        cls = create_document(WithFields, readonly=True)
        doc = cls(index=3, name='the third')
        self.assertRaises(errors.OperationError, doc.remove)

        cls = create_document(WithFields, disable_remove=True)
        doc = cls(index=3, name='the third')
        self.assertRaises(errors.OperationError, doc.remove)

    def test_validate(self):
        """Document._validate"""
        doc = WithDate(index=1)
        self.assertRaises(errors.ValidationError, doc.save)

        doc.timestamp = 'invalid'
        self.assertRaises(errors.EncodingError, doc.save)

        doc.timestamp = datetime.now()
        doc.save()
        doc._meta.get_collection().remove()

    def test_count(self):
        """Document.count"""
        WithFields(index=2, name='the second').save()
        WithFields(index=3, name='the third').save()
        WithFields(index=4, name='the fourth').save()

        count = WithFields.count()
        self.assertEqual(count, 3, "count() returned incorrect number of documents")

        WithFields.find().remove()

    def test_find(self):
        """Document.find"""
        WithFields(index=2, name='the second').save()
        WithFields(index=3, name='the third').save()
        WithFields(index=4, name='the fourth').save()

        docs = WithFields.find()
        count = docs.count()
        self.assertEqual(count, 3, "find() returned incorrect number of documents")

        docs = list(docs)
        self.assertEqual(len(docs), 3, "document list has incorrect length")

        criteria = {'index': {'$gt': 2}}
        docs = WithFields.find(criteria)
        count = docs.count()
        self.assertEqual(
            count, 2, "find({}) returned incorrect number of documents")

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

        cls = create_document(WithFields, readonly=True)
        self.assertRaises(errors.OperationError, cls.find_and_modify,
                          {'index': 2}, {'$set': {'name': 'the second'}})
        doc = cls(index=3, name='the third')

        cls = create_document(WithFields, disable_update=True)
        self.assertRaises(errors.OperationError, cls.find_and_modify,
                          {'index': 2}, {'$set': {'name': 'the second'}})
        doc = cls(index=3, name='the third')

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
            called = Field([str], default=lambda: range(2))

        doc = Defaults()
        self.assertEqual(doc.index, 12, "attribute value is incorrect")
        self.assertIsNone(doc.name, "attribute value is incorrect")
        self.assertEqual(doc.called, ['0', '1'])
        raw = doc._encode()
        self.assertEqual(raw.get('index'), 12, "encoded value is incorrect")
        self.assertIsNone(raw.get('name'), "encoded value is incorrect")

    def test_modifier(self):
        """Field modifiers""" 
        now = datetime.now()
        class Modified(document.Document):
            class Meta:
                connection = 'test'
            index = Field(int)
            updated = Field(datetime, modifier=lambda v: v or now)

        doc = Modified(index=1)
        self.assertIsNone(doc.updated)
        doc.save()
        self.assertEquals(doc.updated, now)

        now = datetime.now().replace(microsecond=0)
        doc.updated = now
        doc.save()
        self.assertEquals(doc.updated, now)

        doc = Modified.find_one({'_id': doc._id})
        self.assertEqual(doc.updated, now)

    def test_disable_methods(self):
        """Document._meta(.readonly|.disable_.*)"""
        doc = create_document()
        self.assertFalse(doc._meta.readonly)
        self.assertFalse(doc._meta.disable_save)
        self.assertFalse(doc._meta.disable_insert)
        self.assertFalse(doc._meta.disable_update)
        self.assertFalse(doc._meta.disable_remove)

        doc = create_document(readonly=True)
        self.assertTrue(doc._meta.readonly)
        self.assertTrue(doc._meta.disable_save)
        self.assertTrue(doc._meta.disable_insert)
        self.assertTrue(doc._meta.disable_update)
        self.assertTrue(doc._meta.disable_remove)

        doc = create_document(readonly=True, disable_save=False, disable_insert=False,
                              disable_update=False, disable_remove=False)
        self.assertTrue(doc._meta.readonly)
        self.assertTrue(doc._meta.disable_save)
        self.assertTrue(doc._meta.disable_insert)
        self.assertTrue(doc._meta.disable_update)
        self.assertTrue(doc._meta.disable_remove)

        doc = create_document(disable_save=True)
        self.assertFalse(doc._meta.readonly)
        self.assertTrue(doc._meta.disable_save)
        self.assertFalse(doc._meta.disable_insert)
        self.assertFalse(doc._meta.disable_update)
        self.assertFalse(doc._meta.disable_remove)

        doc = create_document(disable_insert=True)
        self.assertFalse(doc._meta.readonly)
        self.assertFalse(doc._meta.disable_save)
        self.assertTrue(doc._meta.disable_insert)
        self.assertFalse(doc._meta.disable_update)
        self.assertFalse(doc._meta.disable_remove)

        doc = create_document(disable_update=True)
        self.assertFalse(doc._meta.readonly)
        self.assertFalse(doc._meta.disable_save)
        self.assertFalse(doc._meta.disable_insert)
        self.assertTrue(doc._meta.disable_update)
        self.assertFalse(doc._meta.disable_remove)

        doc = create_document(disable_remove=True)
        self.assertFalse(doc._meta.readonly)
        self.assertFalse(doc._meta.disable_save)
        self.assertFalse(doc._meta.disable_insert)
        self.assertFalse(doc._meta.disable_update)
        self.assertTrue(doc._meta.disable_remove)

    def test_get_field(self):
        """Document._meta.get_field"""
        def test(name, want):
            field = WithReference._meta.get_field(name)
            if want is None:
                self.assertIsNone(field)
            elif isinstance(want, Reference):
                self.assertIsInstance(field, Reference)
                self.assertEqual(field.doctype, want.doctype)
            else:
                self.assertIsInstance(field, Field)
                if hasattr(field.typ, 'builtin'):
                    self.assertEqual(field.typ.builtin, want.typ.builtin)
                elif hasattr(field.typ, 'document'):
                    self.assertEqual(field.typ.document, want.typ.document)
                else:
                    self.assertEqual(field.typ.__class__, want.typ.__class__)

        test('index', Field(int))
        test('index.none', None)
        test('sub', Field(SubDocument))
        test('sub.index', Field(int))
        test('ref', Reference(SubDocument))
        test('ref.index', None)


class TestPartialDocument(common.TestCase):
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

    def test_get_field(self):
        """Document._meta.get_field"""
        field = TopDocument._meta.get_field('sub')
        self.assertIsNotNone(field)
        self.assertIsInstance(field.typ, types.DocumentType)

        field = TopDocument._meta.get_field('sub.name')
        self.assertIsNotNone(field)
        self.assertIsInstance(field.typ, types.BuiltinType)

        field = TopDocument._meta.get_field('sub.name.nope')
        self.assertIsNone(field)


class TestInheritedDocument(common.TestCase):
    """Test inherited Document objects."""

    def test_fields(self):
        """Inherited Document fields"""
        class Parent1(document.Document):
            class Meta:
                connection = 'test'
            index = Field(int)

        class Parent2(document.Document):
            class Meta:
                connection = 'test'
            type = Field(str)

        class SingleChild(Parent1):
            class Meta:
                connection = 'test'
            name = Field(str)

        class MultiChild(Parent1, Parent2):
            class MetA:
                connection = 'test'
            name = Field(str)

        self.assertEqual(set(Parent1._meta.fields.keys()), {'_id', 'index'})
        self.assertEqual(set(Parent2._meta.fields.keys()), {'_id', 'type'})
        self.assertEqual(set(SingleChild._meta.fields.keys()), {'_id', 'index', 'name'})
        self.assertEqual(set(MultiChild._meta.fields.keys()), {'_id', 'index', 'name', 'type'})
