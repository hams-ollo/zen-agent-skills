import unittest

from textutil.format import column, indent, truncate


class IndentTest(unittest.TestCase):
    def test_indent(self):
        self.assertEqual(indent("a\nb", 2), "  a\n  b")


class TruncateTest(unittest.TestCase):
    def test_short_text_is_unchanged(self):
        self.assertEqual(truncate("abc", 5), "abc")

    def test_long_text_is_cut_with_marker(self):
        self.assertEqual(truncate("abcdefgh", 6), "abc...")


class ColumnTest(unittest.TestCase):
    def test_right_aligns(self):
        self.assertEqual(column([1, 22], 3), ["  1", " 22"])
