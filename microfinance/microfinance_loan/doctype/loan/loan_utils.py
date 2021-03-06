from datetime import date
import frappe
from frappe.utils import cint
from frappe.utils.data \
    import getdate, add_months, add_days, date_diff, get_last_day


def get_interval(day_of_month, date_obj):
    '''Returns start and end date of the interval'''
    if not isinstance(date_obj, date):
        date_obj = getdate(date_obj)
    try:
        start_date = date_obj.replace(day=day_of_month)
    except ValueError:
        start_date = add_months(date_obj, -1).replace(day=day_of_month)
    if date_diff(date_obj, start_date) < 0:
        start_date = add_months(start_date, -1)
    try:
        end_date = date_obj.replace(day=day_of_month)
    except ValueError:
        end_date = get_last_day(date_obj)
    if date_diff(end_date, date_obj) <= 0:
        end_date = add_months(end_date, 1)
    end_date = add_days(end_date, -1)
    as_text = '{} - {}'.format(start_date, end_date)
    return start_date, end_date, as_text


def get_periods(day_of_month, date_obj, no_of_periods=5):
    intervals = []
    limit_start = -((cint(no_of_periods) + 1) / 2)
    limit_end = cint(no_of_periods) / 2
    for x in range(limit_start, limit_end):
        start_date, end_date, as_text = get_interval(
            day_of_month, add_months(date_obj, x)
        )
        intervals.append({
                'start_date': start_date,
                'end_date': end_date,
                'as_text': as_text,
            })
    return intervals


def paid_interest(loan, period):
    interest_receivable_account = frappe.get_value(
            'Loan',
            loan,
            'interest_receivable_account'
        )
    counterparts = map(lambda x: "'{}'".format(x.get('name')), frappe.get_all(
        'Account',
        {'account_type': ['in', 'Cash, Bank'], 'is_group': 0},
        'name'
    ))

    conds = [
        "account = '{}'".format(interest_receivable_account),
        "against in ({})".format(", ".join(counterparts)),
        "period = '{}'".format(period),
        "against_voucher_type = 'Loan'",
        "against_voucher = '{}'".format(loan),
    ]

    return frappe.db.sql("""
        SELECT sum(credit - debit) FROM `tabGL Entry` WHERE {}
    """.format(" AND ".join(conds)))[0][0] or 0


def billed_interest(loan, period):
    interest_income_account, interest_receivable_account = frappe.get_value(
            'Loan',
            loan,
            ['interest_income_account', 'interest_receivable_account']
        )

    conds = [
            "account = '{}'".format(interest_receivable_account),
            "against = '{}'".format(interest_income_account),
            "period = '{}'".format(period),
            "against_voucher_type = 'Loan'",
            "against_voucher = '{}'".format(loan),
        ]

    return frappe.db.sql("""
        SELECT sum(debit - credit) FROM `tabGL Entry` WHERE {}
    """.format(" AND ".join(conds)))[0][0] or 0


def converted_interest(loan, period):
    interest_receivable_account, loan_account = frappe.get_value(
            'Loan',
            loan,
            ['interest_receivable_account', 'loan_account']
        )

    conds = [
            "account = '{}'".format(interest_receivable_account),
            "against = '{}'".format(loan_account),
            "period = '{}'".format(period),
            "against_voucher_type = 'Loan'",
            "against_voucher = '{}'".format(loan),
        ]

    return frappe.db.sql("""
        SELECT sum(credit - debit) FROM `tabGL Entry` WHERE {}
    """.format(" AND ".join(conds)))[0][0] or 0


def get_disbursement_between(loan, period):
    start_date, end_date = period.split(' - ')
    loan_account = frappe.get_value(
            'Loan',
            loan,
            'loan_account'
        )
    conds = [
        "account = '{}'".format(loan_account),
        "voucher_type = 'Disbursement'",
        "posting_date BETWEEN '{0}' AND '{1}'".format(start_date, end_date),
        "against_voucher_type = 'Loan'",
        "against_voucher = '{}'".format(loan),
    ]
    return frappe.db.sql("""
        SELECT sum(debit - credit) FROM `tabGL Entry` WHERE {}
    """.format(" AND ".join(conds)))[0][0] or 0


def get_recovery_between(loan, period):
    start_date, end_date = period.split(' - ')
    loan_account = frappe.get_value(
            'Loan',
            loan,
            'loan_account'
        )
    counterparts = map(lambda x: "'{}'".format(x.get('name')), frappe.get_all(
        'Account',
        {'account_type': ['in', 'Cash, Bank'], 'is_group': 0},
        'name'
    ))
    conds = [
        "account = '{}'".format(loan_account),
        "against in ({})".format(", ".join(counterparts)),
        "voucher_type = 'Recovery'",
        "posting_date BETWEEN '{0}' AND '{1}'".format(start_date, end_date),
        "against_voucher_type = 'Loan'",
        "against_voucher = '{}'".format(loan),
    ]
    return frappe.db.sql("""
        SELECT sum(credit - debit) FROM `tabGL Entry` WHERE {}
    """.format(" AND ".join(conds)))[0][0] or 0
