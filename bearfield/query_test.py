"""Test the query module."""
import unittest
from collections import OrderedDict
from datetime import time
from bearfield import query, Document, Field


class TestQuery(unittest.TestCase):
    """Test the Query class."""

    def test_copy(self):
        """Query.copy"""
        criteria = {'a': 'aye'}
        q1 = query.Query(criteria)
        q2 = q1.copy()
        q2.criteria['b'] = 'bee'
        self.assertNotIn('b', q1.criteria, "query does not copy criteria")

    def test_encode(self):
        """Query.encode"""
        class Doc(Document):
            index = Field(int)
            name = Field(str)

        # test regular query
        raw = {'index': "12", 'name': time(12, 37)}
        want = {'index': 12, 'name': '12:37:00'}
        self.assertEqual(query.Query(raw).encode(Doc), want, "encoded query is incorrect")

        # test scalar operator
        raw = {'index': {'$gt': "5"}, 'name': 'the best'}
        want = {'index': {'$gt': 5}, 'name': 'the best'}
        self.assertEqual(query.Query(raw).encode(Doc), want, "encoded query is incorrect")

        # test list operator
        raw = {'index': {'$in': [1, "12", 15]}}
        want = {'index': {'$in': [1, 12, 15]}}
        self.assertEqual(query.Query(raw).encode(Doc), want, "encoded query is incorrect")

        # test dicts and lists
        raw = {'$or': [{'index': "12"}, {'index': 15}]}
        want = {'$or': [{'index': 12}, {'index': 15}]}
        self.assertEqual(query.Query(raw).encode(Doc), want, "encoded query is incorrect")

    def test_op(self):
        """Query._op"""
        def test(op, c1, c2, want):
            have = query.Query(c1)._op(op, query.Query(c2))
            self.assertEqual(have.criteria, want, "failed to combine queries")

        def group(op):
            c1 = OrderedDict([])
            c2 = OrderedDict([('b', 'bee')])
            test(op, c1, c2, c2)

            c1 = OrderedDict([('a', 'aye')])
            c2 = OrderedDict([])
            test(op, c1, c2, c1)

            c1 = OrderedDict([('a', 'aye')])
            c2 = OrderedDict([('b', 'bee')])
            cr = OrderedDict([(op, [c1, c2])])
            test(op, c1, c2, cr)

            c1a = OrderedDict([('a', 'aye')])
            c1b = OrderedDict([('b', 'bee')])
            c1 = OrderedDict([(op, [c1a, c1b])])
            c2 = OrderedDict([('c', 'see')])
            cr = OrderedDict([(op, [c1a, c1b, c2])])
            test(op, c1, c2, cr)

        group('$and')
        group('$or')
        group('$nor')

    def test_and(self):
        """Query.__and__"""
        q1 = query.Query([('a', 'aye')])
        q2 = query.Query([('b', 'bee')])
        c1 = (q1 & q2).criteria
        c2 = q1._op('$and', q2).criteria
        self.assertEqual(c1, c2, "failed to combind queries")

    def test_or(self):
        """Query.__or__"""
        q1 = query.Query([('a', 'aye')])
        q2 = query.Query([('b', 'bee')])
        c1 = (q1 | q2).criteria
        c2 = q1._op('$or', q2).criteria
        self.assertEqual(c1, c2, "failed to combind queries")

    def test_nor(self):
        """Query.nor"""
        q1 = query.Query([('a', 'aye')])
        q2 = query.Query([('b', 'bee')])
        c1 = q1.nor(q2).criteria
        c2 = q1._op('$nor', q2).criteria
        self.assertEqual(c1, c2, "failed to combind queries")

    def test_negate(self):
        """Query.negate"""
        c1 = OrderedDict([('a', 'aye')])
        c2 = OrderedDict([('$not', c1)])
        self.assertEqual(query.Query(c1).negate().criteria, c2, "negated query is incorrect")
        self.assertEqual(query.Query(c2).negate().criteria, c1, "negated query is incorrect")

    def test_q(self):
        """Q == Query."""
        self.assertEqual(query.Q, query.Query, "shorthand query is incorrectly set")
