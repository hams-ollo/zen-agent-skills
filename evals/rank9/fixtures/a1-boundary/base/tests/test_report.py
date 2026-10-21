import os
import unittest

from report import average_sale, load_rows

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sales.csv")


class AverageSaleTest(unittest.TestCase):
    def test_average_of_fixture(self):
        rows = load_rows(FIXTURE)
        self.assertAlmostEqual(average_sale(rows), 42.5)


if __name__ == "__main__":
    unittest.main()
