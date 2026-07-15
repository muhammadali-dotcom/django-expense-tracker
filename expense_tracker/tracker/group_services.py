"""
Business logic for the Group Expense Management & Smart Settlement System.

Kept separate from views.py so views stay thin. Functions here operate on
plain Decimal amounts and Person/ExpenseGroup model instances.

Split helpers
-------------
calculate_equal_shares(total_amount, people)
    Split an amount evenly across a list of Person objects, distributing
    any leftover cents to the first few people so the shares always sum
    exactly to total_amount.

validate_custom_split(total_amount, shares)
    Raise ValueError if a dict of {person: amount} doesn't sum to
    total_amount.

calculate_percentage_shares(total_amount, percentages)
    Convert a dict of {person: percentage} (must sum to 100) into a dict
    of {person: amount}, again guaranteed to sum exactly to total_amount.

Balance & settlement engine
----------------------------
calculate_group_balances(group_id)
    Returns {person: Decimal} — positive means the person should receive
    money, negative means they owe money. Already-paid Settlement records
    are netted out.

generate_settlement_plan(group_id)
    Returns a list of {'from': person, 'to': person, 'amount': Decimal}
    using a greedy debtor/creditor matching algorithm that minimizes the
    number of transactions needed to settle the group.
"""

from collections import defaultdict
from decimal import Decimal, ROUND_DOWN

from django.db.models import Sum

from .models import ExpenseGroup, GroupExpense, Person, Settlement

CENT = Decimal('0.01')


def calculate_equal_shares(total_amount, people):
    """Split total_amount evenly across `people` (list of Person). Returns {person: Decimal}."""
    n = len(people)
    if n == 0:
        return {}
    base = (total_amount / n).quantize(CENT, rounding=ROUND_DOWN)
    shares = {person: base for person in people}
    remainder_cents = int((total_amount - base * n) / CENT)
    for person in people[:remainder_cents]:
        shares[person] += CENT
    return shares


def validate_custom_split(total_amount, shares):
    """shares: {person: Decimal}. Raises ValueError if they don't sum to total_amount."""
    total = sum(shares.values(), Decimal('0.00'))
    if total != total_amount:
        raise ValueError(
            f"Split amounts total {total} but the expense amount is {total_amount}."
        )


def calculate_percentage_shares(total_amount, percentages):
    """percentages: {person: Decimal}, must sum to 100. Returns {person: Decimal} summing to total_amount."""
    total_pct = sum(percentages.values(), Decimal('0'))
    if total_pct != Decimal('100'):
        raise ValueError(f"Percentages total {total_pct}%, but must total 100%.")

    people = list(percentages.keys())
    shares = {}
    allocated = Decimal('0.00')
    for person in people[:-1]:
        amount = (total_amount * percentages[person] / Decimal('100')).quantize(CENT, rounding=ROUND_DOWN)
        shares[person] = amount
        allocated += amount
    # Give the last person the remainder so shares always sum exactly.
    shares[people[-1]] = total_amount - allocated
    return shares


def calculate_group_balances(group_id):
    """
    Returns {Person: Decimal} for every person who has paid or been split
    an expense in the group. Positive = should receive money, negative =
    owes money. Already-`paid` Settlements are netted out.
    """
    balances = defaultdict(lambda: Decimal('0.00'))

    expenses = GroupExpense.objects.filter(group_id=group_id).prefetch_related('splits__person').select_related('paid_by')
    for expense in expenses:
        balances[expense.paid_by] += expense.total_amount
        for split in expense.splits.all():
            balances[split.person] -= split.share_amount

    paid_settlements = Settlement.objects.filter(group_id=group_id, status='paid').select_related('from_person', 'to_person')
    for settlement in paid_settlements:
        balances[settlement.from_person] += settlement.amount
        balances[settlement.to_person] -= settlement.amount

    return dict(balances)


def generate_settlement_plan(group_id):
    """
    Returns [{'from': Person, 'to': Person, 'amount': Decimal}, ...] — the
    minimal set of transactions needed to settle all outstanding balances
    in the group, computed with a greedy debtor/creditor match.
    """
    balances = calculate_group_balances(group_id)

    debtors = sorted(
        [[person, -balance] for person, balance in balances.items() if balance < 0],
        key=lambda item: item[1],
        reverse=True,
    )
    creditors = sorted(
        [[person, balance] for person, balance in balances.items() if balance > 0],
        key=lambda item: item[1],
        reverse=True,
    )

    plan = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor, owed = debtors[i]
        creditor, receivable = creditors[j]
        pay = min(owed, receivable)

        plan.append({'from': debtor, 'to': creditor, 'amount': pay})

        debtors[i][1] -= pay
        creditors[j][1] -= pay
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1

    return plan


def get_dashboard_stats(user):
    """Aggregate stats for the group-expense dashboard, scoped to `user`."""
    groups = ExpenseGroup.objects.filter(user=user)
    total_expenses = Decimal('0.00')
    receive_total = Decimal('0.00')
    pay_total = Decimal('0.00')

    for group in groups:
        total_expenses += GroupExpense.objects.filter(group=group).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        for balance in calculate_group_balances(group.id).values():
            if balance > 0:
                receive_total += balance
            elif balance < 0:
                pay_total += -balance

    return {
        'total_expenses': total_expenses,
        'total_groups': groups.count(),
        'total_people': Person.objects.filter(user=user).count(),
        'receive_total': receive_total,
        'pay_total': pay_total,
    }
