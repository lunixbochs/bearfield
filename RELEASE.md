## v1.9.1
* Support pymongo 3.0.x.

## v1.9 - Set Bugs
* Fix bug causing set fields to be treated as single values.

## v1.8 - Query Bugs
* Fix bug causing queries with references to break.
* Fix internal storage bug which prevented updates from saving changes.

## v1.7 - Type Bugs
* Allow use of `new` parameter in `find_and_modify`.
* Fix some bugs related to field processing.

## v1.6 - Sort Bugs
* Correctly encode sorts as a list of tuples.

## v1.5 - Inheritance
+ Support document inheritance.

## v1.4 - Callable Defaults
+ Support callables as default field values.
+ Support modifying field values before encoding.

## v1.3 - Readonly and Reasonableness
+ Add readonly, disable_save, disable_insert, disable_update, and
  disable_remove options to document Meta.
* Fields now default to require=False.

## v1.2 - setuptools
* Make setup.py work properly when installing from source.
* Minor docstring updates.

## v1.1 - References
+ Add support for Reference fields.
+ Extend test coverage to 100%.
+ Encode sort specs.
* Rebuild update and query encoders.

## v1.0 - Initial Release
+ Support field types: Document, date, time, datetime, list, set, dict, and all basic builtins.
+ Easy configuration of multiple connections.
+ Lazy decoding of field values.
+ Query building.
