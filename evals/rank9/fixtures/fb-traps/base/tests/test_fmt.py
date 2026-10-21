import unittest

from fmt import title_case


class TitleCaseTest(unittest.TestCase):
    def test_capitalises_words(self):
        self.assertEqual(title_case("hello world"), "Hello World")
