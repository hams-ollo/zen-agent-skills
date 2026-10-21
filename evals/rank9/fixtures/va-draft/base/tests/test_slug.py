import unittest

from slug import slugify


class SlugifyTest(unittest.TestCase):
    def test_lowercases(self):
        self.assertEqual(slugify("Hello"), "hello")

    def test_joins_words_with_hyphen(self):
        self.assertEqual(slugify("hello world"), "hello-world")

    def test_strips_edge_hyphens(self):
        self.assertEqual(slugify("-hello-"), "hello")


if __name__ == "__main__":
    unittest.main()
