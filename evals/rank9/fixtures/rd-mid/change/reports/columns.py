"""Column formatters for plain-text reports: one function per money column."""


def format_amount(value):
    """Format a amount value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_balance(value):
    """Format a balance value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_fee(value):
    """Format a fee value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_tax(value):
    """Format a tax value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_discount(value):
    """Format a discount value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_refund(value):
    """Format a refund value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_deposit(value):
    """Format a deposit value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_withdrawal(value):
    """Format a withdrawal value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_interest(value):
    """Format a interest value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_credit(value):
    """Format a credit value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_debit(value):
    """Format a debit value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_subtotal(value):
    """Format a subtotal value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_total(value):
    """Format a total value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_tip(value):
    """Format a tip value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_shipping(value):
    """Format a shipping value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_duty(value):
    """Format a duty value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_rebate(value):
    """Format a rebate value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_charge(value):
    """Format a charge value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_payment(value):
    """Format a payment value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_adjustment(value):
    """Format a adjustment value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_bonus(value):
    """Format a bonus value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_commission(value):
    """Format a commission value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_penalty(value):
    """Format a penalty value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_surcharge(value):
    """Format a surcharge value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_grant(value):
    """Format a grant value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_levy(value):
    """Format a levy value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_royalty(value):
    """Format a royalty value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_stipend(value):
    """Format a stipend value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_wage(value):
    """Format a wage value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


def format_allowance(value):
    """Format a allowance value with two decimals and a thousands separator."""
    if value is None:
        return "-"
    return f"{value:,.2f}"


FORMATTERS = {
    "amount": format_amount,
    "balance": format_balance,
    "fee": format_fee,
    "tax": format_tax,
    "discount": format_discount,
    "refund": format_refund,
    "deposit": format_deposit,
    "withdrawal": format_withdrawal,
    "interest": format_interest,
    "credit": format_credit,
    "debit": format_debit,
    "subtotal": format_subtotal,
    "total": format_total,
    "tip": format_tip,
    "shipping": format_shipping,
    "duty": format_duty,
    "rebate": format_rebate,
    "charge": format_charge,
    "payment": format_payment,
    "adjustment": format_adjustment,
    "bonus": format_bonus,
    "commission": format_commission,
    "penalty": format_penalty,
    "surcharge": format_surcharge,
    "grant": format_grant,
    "levy": format_levy,
    "royalty": format_royalty,
    "stipend": format_stipend,
    "wage": format_wage,
    "allowance": format_allowance,
}
