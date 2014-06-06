BearField
=========
A small, efficient, easy to use [MongoDB][1] object layer built on top of [PyMongo][2].

[![Build Status](https://travis-ci.org/WiFast/bearfield.svg?branch=master)](https://travis-ci.org/WiFast/bearfield)

Features
--------
BearField has some fun features:

- Lazy field decoding. Grabbing documents is fast because BearField doesn't do anything with them
  until you do.
- Simple field declarations. It's super simple: `value = Field(str)`
- Subdocuments are easy, too: `subdoc = Field(MyDocument)`
- Query chaining: `Q({'value': 'first'}) | Q({'value': 'third'})`
- Multiple connections and databases.
- And more, I'm sure!

License
-------
Copyright (c) 2014 WiFast, Inc. This project and all of its contents is licensed under the
BSD-derived license as found in the included [LICENSE][3] file.

[1]: http://www.mongodb.org/ "MongoDB"
[2]: http://api.mongodb.org/python/current/ "PyMongo"
[3]: https://github.com/WiFast/bearfield/blob/master/LICENSE "LICENSE"
