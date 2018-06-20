BearField
=========
A small, efficient, easy to use [MongoDB][1] object layer built on top of [PyMongo][2].

[![Build Status](https://travis-ci.org/zenreach/bearfield.svg?branch=master)](https://travis-ci.org/zenreach/bearfield)

Features
--------
BearField has some fun features:

- Lazy field decoding. Grabbing documents is fast because BearField doesn't do anything with them
  until you do.
- Simple field declarations: `value = Field(str)`
- Subdocuments are easy, too: `subdoc = Field(MyDocument)`
- All the field types: Document, date, time, datetime, list, set, dict, and all the builtins
- Query chaining: `Q({'type': 'grizzly'}) | Q({'type': 'kodiak'})`
- Multiple connections and databases.

Examples
--------
Add a new connection:

    from bearfield import connection
    connection.add('example', 'mongodb://localhost/example')

Now create a document type associated with our example connection:

    from bearfield import Document, Field

    class Bear(Document):
        class Meta:
            connection = 'example'

        name = Field(str)
        type = Field(str)
        height = Field(float)

You'll notice we use a `Meta` class for document metadata. Relevant options are `connection`, which
defines which named connection we're storing documents in, and `collection` which defaults to the
snake cased document class name if it is not provided. Additional options are ignored for forward
compaitibility.

Working with objects of that type is easy. Let's make a 9.8ft grizzly bear:

    bear = Bear(name='timmy', type='grizzly', height='9.8')
    bear.save()

Easy. This will set the `_id` field on our `bear` object. Now lets go searching for bears:

    bears = Bear.find({'type': 'grizzly'})
    for bear in bears:
        print("This grizzly is {}ft tall!".format(bear.height))

Or you can get just one bear:

    bear = Bear.find_one({'_id': bear_identifier})
    print("My bear is {}ft tall!".format(bear.height))

The `find_one` method does not raise an exception if it can't find your bear. Instead it will
return `None`. This is good because bears do not like exceptions.

The `update` method will only update fields that have changed on a document. This is more performant
than save which updates the entire document at once. So this is what happens when our bear grows
up:

    bear = Bear.find_one({'_id': bear_identifier})
    bear.height = 10.3
    bear.update()

The `update` method will raise an exception if the bear object has no `_id` field.

You can perform the same operation without first retrieving the object from the database:

    old_bear = Bear.find_and_modify({'_id': bear_identifier}, {'height': 10.3})
    print("My bear used to be {}ft tall! But he's bigger now!".format(old_bear.height))

Notice that `find_and_modify` returns the old value of the object. This is important since you did
not have a bear to play with before calling `find_and_modify`.

What about subdocuments? Let's define a `BearType` and redefine our `Bear` document to use it:

    class BearType(Document):
        name = Field(str)
        avg_height = Field(int)
        colors = Field({str})

    class Bear(Document):
        class Meta:
            connection = 'example'

        name = Field(str)
        type = Field(BearType)
        height = Field(float)

We've changed the type of our `type` field to `BearType`. The `BearType` does not require a `Meta`
class because it is not associated with a collection. Using it is still easy:

    grizzly = BearType(name='grizzly', avg_height=9.3, colors={'brown'})
    bear = Bear(name='timmy', type=grizzly, height=10.3)

On the other hand it might make more sense to keep our BearTypes in their own collection. We can
use references to make accessing the associated type easy. References are associated with a
document model and may store an ObjectId or Query. We'll redefine our documents like this:

    from bearfield import Reference

    class BearType(Document):
        class Meta:
            connection = 'test'

        name = Field(str)
        avg_height = Field(int)
        colors = Field({str})

    class Bear(Document):
        class Meta:
            connection = 'example'

        name = Field(str)
        type = Reference(BearType)
        height = Field(float)

Creating the bear is similar. The only difference is that the grizzly type needs to be saved in the
database before setting it on the bear document:

    grizzly = BearType(name='grizzly', avg_height=9.3, colors={'brown'})
    grizzly.save()
    bear = Bear(name='timmy', type=grizzly, height=10.3)

References use find and find_one methods to retrieve the object. References are designed this way
so that you, the user, don't anger any bears by executing queries you don't know about.

    type = bear.type.find_one()

Remember that we can also set References to query values. We can query by name to accomplish the
same as above:

    bear.type = {'name': 'grizzly'}
    type = bear.type.find_one()

See, bears like it when things are easy.

License
-------
Copyright (c) 2014 WiFast, Inc. This project and all of its contents is licensed under the
BSD-derived license as found in the included [LICENSE][3] file.

[1]: http://www.mongodb.org/ "MongoDB"
[2]: http://api.mongodb.org/python/current/ "PyMongo"
[3]: https://github.com/zenreach/bearfield/blob/master/LICENSE "LICENSE"
