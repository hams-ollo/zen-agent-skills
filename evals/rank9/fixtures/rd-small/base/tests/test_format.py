import unittest

from textutil.format import indent


class IndentTest(unittest.TestCase):
    def test_indent(self):
        self.assertEqual(indent("a\nb", 2), "  a\n  b")
