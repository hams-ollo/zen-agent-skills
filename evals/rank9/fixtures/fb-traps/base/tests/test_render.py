import unittest

from render import pad


class PadTest(unittest.TestCase):
    def test_pads_to_width(self):
        self.assertEqual(len(pad("qty", 3)), 5)
