import unittest

from reports.columns import FORMATTERS
from reports.layout import column_widths, render, totals_row


class FormatterTest(unittest.TestCase):
    def test_amount_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["amount"](1234.5), "1,234.50")

    def test_balance_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["balance"](1234.5), "1,234.50")

    def test_fee_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["fee"](1234.5), "1,234.50")

    def test_tax_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["tax"](1234.5), "1,234.50")

    def test_discount_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["discount"](1234.5), "1,234.50")

    def test_refund_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["refund"](1234.5), "1,234.50")

    def test_deposit_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["deposit"](1234.5), "1,234.50")

    def test_withdrawal_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["withdrawal"](1234.5), "1,234.50")

    def test_interest_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["interest"](1234.5), "1,234.50")

    def test_credit_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["credit"](1234.5), "1,234.50")

    def test_debit_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["debit"](1234.5), "1,234.50")

    def test_subtotal_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["subtotal"](1234.5), "1,234.50")

    def test_total_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["total"](1234.5), "1,234.50")

    def test_tip_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["tip"](1234.5), "1,234.50")

    def test_shipping_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["shipping"](1234.5), "1,234.50")

    def test_duty_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["duty"](1234.5), "1,234.50")

    def test_rebate_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["rebate"](1234.5), "1,234.50")

    def test_charge_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["charge"](1234.5), "1,234.50")

    def test_payment_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["payment"](1234.5), "1,234.50")

    def test_adjustment_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["adjustment"](1234.5), "1,234.50")

    def test_bonus_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["bonus"](1234.5), "1,234.50")

    def test_commission_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["commission"](1234.5), "1,234.50")

    def test_penalty_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["penalty"](1234.5), "1,234.50")

    def test_surcharge_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["surcharge"](1234.5), "1,234.50")

    def test_grant_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["grant"](1234.5), "1,234.50")

    def test_levy_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["levy"](1234.5), "1,234.50")

    def test_royalty_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["royalty"](1234.5), "1,234.50")

    def test_stipend_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["stipend"](1234.5), "1,234.50")

    def test_wage_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["wage"](1234.5), "1,234.50")

    def test_allowance_formats_two_decimals(self):
        self.assertEqual(FORMATTERS["allowance"](1234.5), "1,234.50")

    def test_missing_value_is_dash(self):
        self.assertEqual(FORMATTERS["amount"](None), "-")


class LayoutTest(unittest.TestCase):
    def test_widths_cover_header(self):
        self.assertEqual(column_widths([{"fee": 1}], ["fee"]), {"fee": 4})

    def test_totals_treat_missing_as_zero(self):
        self.assertEqual(totals_row([{"fee": 1}, {}], ["fee"]), {"fee": 1})

    def test_render_has_title(self):
        self.assertTrue(render("Fees", [{"fee": 2}], ["fee"]).startswith("Fees"))
