from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from tracker.models import (
    Person, ExpenseGroup, GroupMember, GroupExpense, ExpenseSplit, Settlement,
)
from tracker.group_services import (
    calculate_equal_shares, validate_custom_split, calculate_percentage_shares,
    calculate_group_balances, generate_settlement_plan,
)


class GroupExpenseTestCase(TestCase):
    """Base fixture: one owner account, four people, one group."""

    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='irrelevant')
        self.ali = Person.objects.create(user=self.user, name='Ali')
        self.asim = Person.objects.create(user=self.user, name='Asim')
        self.rafay = Person.objects.create(user=self.user, name='Rafay')
        self.anas = Person.objects.create(user=self.user, name='Anas')
        self.group = ExpenseGroup.objects.create(user=self.user, name='University Friends')
        for person in (self.ali, self.asim, self.rafay, self.anas):
            GroupMember.objects.create(group=self.group, person=person)


# 1. Person creation ---------------------------------------------------------

class PersonCreationTests(TestCase):
    def test_person_created_with_owner(self):
        user = User.objects.create_user(username='owner', password='irrelevant')
        person = Person.objects.create(user=user, name='Ali', phone='0300', email='ali@example.com')
        self.assertEqual(person.name, 'Ali')
        self.assertEqual(person.user, user)
        self.assertEqual(Person.objects.count(), 1)


# 2. Group creation -----------------------------------------------------------

class GroupCreationTests(TestCase):
    def test_group_created_with_owner(self):
        user = User.objects.create_user(username='owner', password='irrelevant')
        group = ExpenseGroup.objects.create(user=user, name='University Friends', description='Uni squad')
        self.assertEqual(group.name, 'University Friends')
        self.assertEqual(group.user, user)


# 3. Adding members ------------------------------------------------------------

class GroupMemberTests(GroupExpenseTestCase):
    def test_members_added_to_group(self):
        self.assertEqual(self.group.members.count(), 4)
        self.assertIn(self.ali, self.group.members.all())
        self.assertIn(self.rafay, self.group.members.all())

    def test_duplicate_membership_rejected(self):
        with self.assertRaises(Exception):
            GroupMember.objects.create(group=self.group, person=self.ali)


# 4. Equal split calculation ---------------------------------------------------

class EqualSplitTests(TestCase):
    def test_equal_split_divides_evenly(self):
        user = User.objects.create_user(username='owner', password='irrelevant')
        people = [Person.objects.create(user=user, name=n) for n in ['A', 'B', 'C', 'D']]
        shares = calculate_equal_shares(Decimal('400.00'), people)
        self.assertEqual(sum(shares.values()), Decimal('400.00'))
        for person in people:
            self.assertEqual(shares[person], Decimal('100.00'))

    def test_equal_split_distributes_remainder_cents(self):
        user = User.objects.create_user(username='owner', password='irrelevant')
        people = [Person.objects.create(user=user, name=n) for n in ['A', 'B', 'C']]
        shares = calculate_equal_shares(Decimal('10.00'), people)
        self.assertEqual(sum(shares.values()), Decimal('10.00'))


# 5. Custom split calculation ---------------------------------------------------

class CustomSplitTests(TestCase):
    def test_valid_custom_split_passes(self):
        user = User.objects.create_user(username='owner', password='irrelevant')
        ali = Person.objects.create(user=user, name='Ali')
        asim = Person.objects.create(user=user, name='Asim')
        anas = Person.objects.create(user=user, name='Anas')
        rafay = Person.objects.create(user=user, name='Rafay')
        shares = {ali: Decimal('70'), asim: Decimal('80'), anas: Decimal('80'), rafay: Decimal('170')}
        # Should not raise
        validate_custom_split(Decimal('400'), shares)

    def test_invalid_custom_split_raises(self):
        user = User.objects.create_user(username='owner', password='irrelevant')
        ali = Person.objects.create(user=user, name='Ali')
        asim = Person.objects.create(user=user, name='Asim')
        anas = Person.objects.create(user=user, name='Anas')
        shares = {ali: Decimal('70'), asim: Decimal('80'), anas: Decimal('80')}  # sums to 230, not 400
        with self.assertRaises(ValueError):
            validate_custom_split(Decimal('400'), shares)


# 6. Percentage split calculation -----------------------------------------------

class PercentageSplitTests(TestCase):
    def test_percentage_split_sums_to_total(self):
        user = User.objects.create_user(username='owner', password='irrelevant')
        people = [Person.objects.create(user=user, name=n) for n in ['Ali', 'Asim', 'Rafay', 'Anas']]
        percentages = {p: Decimal('25') for p in people}
        shares = calculate_percentage_shares(Decimal('400.00'), percentages)
        self.assertEqual(sum(shares.values()), Decimal('400.00'))
        for person in people:
            self.assertEqual(shares[person], Decimal('100.00'))

    def test_percentage_split_must_total_100(self):
        user = User.objects.create_user(username='owner', password='irrelevant')
        ali = Person.objects.create(user=user, name='Ali')
        asim = Person.objects.create(user=user, name='Asim')
        percentages = {ali: Decimal('50'), asim: Decimal('40')}  # only 90%
        with self.assertRaises(ValueError):
            calculate_percentage_shares(Decimal('400'), percentages)


# 7. Balance calculation ---------------------------------------------------------

class BalanceCalculationTests(GroupExpenseTestCase):
    """
    Rafay pays 400 for lunch. Splits: Ali 70, Asim 80, Anas 80, Rafay 70.
    Expected balances: Ali -70, Asim -80, Anas -80, Rafay +330.
    """

    def setUp(self):
        super().setUp()
        self.expense = GroupExpense.objects.create(
            group=self.group, title='Lunch', total_amount=Decimal('400.00'),
            paid_by=self.rafay, expense_date='2026-07-01',
        )
        ExpenseSplit.objects.create(expense=self.expense, person=self.ali, share_amount=Decimal('70.00'))
        ExpenseSplit.objects.create(expense=self.expense, person=self.asim, share_amount=Decimal('80.00'))
        ExpenseSplit.objects.create(expense=self.expense, person=self.anas, share_amount=Decimal('80.00'))
        ExpenseSplit.objects.create(expense=self.expense, person=self.rafay, share_amount=Decimal('70.00'))

    def test_balances_match_expected(self):
        balances = calculate_group_balances(self.group.id)
        self.assertEqual(balances[self.ali], Decimal('-70.00'))
        self.assertEqual(balances[self.asim], Decimal('-80.00'))
        self.assertEqual(balances[self.anas], Decimal('-80.00'))
        self.assertEqual(balances[self.rafay], Decimal('330.00'))

    def test_paid_settlement_nets_out_balance(self):
        Settlement.objects.create(
            group=self.group, from_person=self.ali, to_person=self.rafay,
            amount=Decimal('70.00'), status='paid',
        )
        balances = calculate_group_balances(self.group.id)
        self.assertEqual(balances[self.ali], Decimal('0.00'))
        self.assertEqual(balances[self.rafay], Decimal('260.00'))

    def test_settlement_defaults_to_pending_not_paid(self):
        """
        Regression test: Settlement.status must default to 'pending'. If it
        ever defaults to 'paid', calculate_group_balances() (which only nets
        out status='paid' settlements) will silently zero out a person's
        real outstanding debt the moment a Settlement row is created without
        an explicit status - e.g. via the admin, a fixture, or a future code
        path that forgets to pass status= explicitly.
        """
        settlement = Settlement.objects.create(
            group=self.group, from_person=self.ali, to_person=self.rafay,
            amount=Decimal('70.00'),
        )
        self.assertEqual(settlement.status, 'pending')

        # A pending settlement must NOT affect balances - Ali still owes.
        balances = calculate_group_balances(self.group.id)
        self.assertEqual(balances[self.ali], Decimal('-70.00'))
        self.assertEqual(balances[self.rafay], Decimal('330.00'))

    def test_unrelated_group_member_not_marked_settled(self):
        """
        A member who wasn't part of this expense at all must not appear
        with a balance of 0 ("Settled") - they should have no balance entry.
        """
        balances = calculate_group_balances(self.group.id)
        outsider = Person.objects.create(user=self.user, name='Outsider')
        self.assertNotIn(outsider, balances)


# 8. Settlement generation ---------------------------------------------------------

class SettlementPlanTests(GroupExpenseTestCase):
    def test_generates_expected_settlements_for_single_payer(self):
        expense = GroupExpense.objects.create(
            group=self.group, title='Lunch', total_amount=Decimal('400.00'),
            paid_by=self.rafay, expense_date='2026-07-01',
        )
        ExpenseSplit.objects.create(expense=expense, person=self.ali, share_amount=Decimal('70.00'))
        ExpenseSplit.objects.create(expense=expense, person=self.asim, share_amount=Decimal('80.00'))
        ExpenseSplit.objects.create(expense=expense, person=self.anas, share_amount=Decimal('80.00'))
        ExpenseSplit.objects.create(expense=expense, person=self.rafay, share_amount=Decimal('70.00'))

        plan = generate_settlement_plan(self.group.id)
        owed = {(entry['from'], entry['to']): entry['amount'] for entry in plan}

        self.assertEqual(owed[(self.ali, self.rafay)], Decimal('70.00'))
        self.assertEqual(owed[(self.asim, self.rafay)], Decimal('80.00'))
        self.assertEqual(owed[(self.anas, self.rafay)], Decimal('80.00'))
        self.assertEqual(len(plan), 3)

    def test_minimizes_transactions_across_chained_debts(self):
        """
        Ali paid 100 for something only Ali+Rafay shared (Rafay owes Ali 100... but
        spec example is: Ali owes Rafay 100, Rafay owes Anas 100 -> should collapse
        to Ali owes Anas 100. We construct that via two expenses producing that
        net balance rather than modeling pairwise debts directly.
        """
        # Expense 1: Rafay pays 200, split Ali 100 / Rafay 100 -> Ali owes Rafay 100
        e1 = GroupExpense.objects.create(
            group=self.group, title='E1', total_amount=Decimal('200.00'),
            paid_by=self.rafay, expense_date='2026-07-01',
        )
        ExpenseSplit.objects.create(expense=e1, person=self.ali, share_amount=Decimal('100.00'))
        ExpenseSplit.objects.create(expense=e1, person=self.rafay, share_amount=Decimal('100.00'))

        # Expense 2: Anas pays 200, split Rafay 100 / Anas 100 -> Rafay owes Anas 100
        e2 = GroupExpense.objects.create(
            group=self.group, title='E2', total_amount=Decimal('200.00'),
            paid_by=self.anas, expense_date='2026-07-02',
        )
        ExpenseSplit.objects.create(expense=e2, person=self.rafay, share_amount=Decimal('100.00'))
        ExpenseSplit.objects.create(expense=e2, person=self.anas, share_amount=Decimal('100.00'))

        balances = calculate_group_balances(self.group.id)
        self.assertEqual(balances[self.rafay], Decimal('0.00'))
        self.assertEqual(balances[self.ali], Decimal('-100.00'))
        self.assertEqual(balances[self.anas], Decimal('100.00'))

        plan = generate_settlement_plan(self.group.id)
        # Rafay's net balance is zero, so only one transaction should remain: Ali -> Anas
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['from'], self.ali)
        self.assertEqual(plan[0]['to'], self.anas)
        self.assertEqual(plan[0]['amount'], Decimal('100.00'))


# View / template smoke tests -----------------------------------------------

class GroupViewSmokeTests(GroupExpenseTestCase):
    """Exercises the full request/response cycle for every new view."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_group_dashboard_renders(self):
        response = self.client.get('/groups/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_group_list_and_detail_render(self):
        response = self.client.get('/groups/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f'/groups/{self.group.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_group_reports_render(self):
        response = self.client.get('/groups/reports/')
        self.assertEqual(response.status_code, 200)

    def test_person_list_and_form_render(self):
        response = self.client.get('/people/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/people/add/')
        self.assertEqual(response.status_code, 200)

    def test_create_expense_with_equal_split(self):
        response = self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Lunch', 'description': '', 'total_amount': '400.00',
            'paid_by': self.rafay.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'equal',
        })
        self.assertEqual(response.status_code, 302)
        expense = GroupExpense.objects.get(title='Lunch')
        self.assertEqual(expense.splits.count(), 4)
        self.assertEqual(sum(s.share_amount for s in expense.splits.all()), Decimal('400.00'))

    def test_create_expense_with_custom_split(self):
        response = self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Lunch', 'description': '', 'total_amount': '400.00',
            'paid_by': self.rafay.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'custom',
            f'share_{self.ali.pk}': '70', f'share_{self.asim.pk}': '80',
            f'share_{self.anas.pk}': '80', f'share_{self.rafay.pk}': '170',
        })
        self.assertEqual(response.status_code, 302)
        expense = GroupExpense.objects.get(title='Lunch')
        self.assertEqual(expense.splits.get(person=self.ali).share_amount, Decimal('70.00'))

    def test_create_expense_with_bad_custom_split_shows_error(self):
        response = self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Lunch', 'description': '', 'total_amount': '400.00',
            'paid_by': self.rafay.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'custom',
            f'share_{self.ali.pk}': '70', f'share_{self.asim.pk}': '80',
            f'share_{self.anas.pk}': '80', f'share_{self.rafay.pk}': '100',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(GroupExpense.objects.filter(title='Lunch').exists())

    def test_create_expense_with_percentage_split(self):
        response = self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Dinner', 'description': '', 'total_amount': '400.00',
            'paid_by': self.ali.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'percentage',
            f'percent_{self.ali.pk}': '25', f'percent_{self.asim.pk}': '25',
            f'percent_{self.anas.pk}': '25', f'percent_{self.rafay.pk}': '25',
        })
        self.assertEqual(response.status_code, 302)
        expense = GroupExpense.objects.get(title='Dinner')
        self.assertEqual(sum(s.share_amount for s in expense.splits.all()), Decimal('400.00'))

    def test_edit_expense_form_renders_with_existing_shares(self):
        expense = GroupExpense.objects.create(
            group=self.group, title='Lunch', total_amount=Decimal('400.00'),
            paid_by=self.rafay, expense_date='2026-07-01',
        )
        ExpenseSplit.objects.create(expense=expense, person=self.ali, share_amount=Decimal('70.00'))
        response = self.client.get(f'/groups/expenses/{expense.pk}/edit/')
        self.assertEqual(response.status_code, 200)

    def test_mark_settlement_paid(self):
        self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Trip', 'description': '', 'total_amount': '280.00',
            'paid_by': self.rafay.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'custom',
            f'share_{self.ali.pk}': '70', f'share_{self.asim.pk}': '70',
            f'share_{self.anas.pk}': '70', f'share_{self.rafay.pk}': '70',
        })

        response = self.client.post(f'/groups/{self.group.pk}/settlements/mark-paid/', {
            'from_person': self.ali.pk, 'to_person': self.rafay.pk, 'amount': '70.00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Settlement.objects.filter(from_person=self.ali, to_person=self.rafay, status='paid').exists())

    def test_add_and_remove_member(self):
        extra = Person.objects.create(user=self.user, name='Extra')
        response = self.client.post(f'/groups/{self.group.pk}/members/add/', {'person': extra.pk})
        self.assertEqual(response.status_code, 302)
        self.assertIn(extra, self.group.members.all())

        gm = GroupMember.objects.get(group=self.group, person=extra)
        response = self.client.post(f'/groups/{self.group.pk}/members/{gm.pk}/remove/')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(extra, self.group.members.all())

    def test_other_users_group_returns_404(self):
        other_user = User.objects.create_user(username='intruder', password='irrelevant')
        self.client.force_login(other_user)
        response = self.client.get(f'/groups/{self.group.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_equal_split_shows_correct_balances_right_after_saving(self):
        """
        End-to-end: create an equal-split expense via the real view, then
        check nobody but the payer shows a zero/"Settled" balance - only
        an actual paid Settlement should ever zero someone out.
        """
        response = self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Trip', 'description': '', 'total_amount': '400.00',
            'paid_by': self.rafay.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'equal',
        })
        self.assertEqual(response.status_code, 302)

        balances = calculate_group_balances(self.group.id)
        # Rafay paid 400 and owes himself 100 -> net +300, not settled.
        self.assertEqual(balances[self.rafay], Decimal('300.00'))
        # Everyone else owes their 100 share - none of them are settled.
        for person in (self.ali, self.asim, self.anas):
            self.assertEqual(balances[person], Decimal('-100.00'))
            self.assertNotEqual(balances[person], Decimal('0.00'))

        # No Settlement has been recorded, so none of the debts are paid.
        self.assertFalse(Settlement.objects.filter(group=self.group, status='paid').exists())

    def test_custom_split_shows_correct_balances_right_after_saving(self):
        response = self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Groceries', 'description': '', 'total_amount': '400.00',
            'paid_by': self.rafay.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'custom',
            f'share_{self.ali.pk}': '70', f'share_{self.asim.pk}': '80',
            f'share_{self.anas.pk}': '80', f'share_{self.rafay.pk}': '170',
        })
        self.assertEqual(response.status_code, 302)

        balances = calculate_group_balances(self.group.id)
        self.assertEqual(balances[self.ali], Decimal('-70.00'))
        self.assertEqual(balances[self.asim], Decimal('-80.00'))
        self.assertEqual(balances[self.anas], Decimal('-80.00'))
        self.assertEqual(balances[self.rafay], Decimal('230.00'))
        self.assertFalse(Settlement.objects.filter(group=self.group, status='paid').exists())

    def test_settlement_only_marked_paid_via_explicit_action(self):
        """
        Creating an expense must never itself create a Settlement row.
        Only the explicit "mark as paid" action should ever do that, and
        only for the amount actually confirmed.
        """
        self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Trip', 'description': '', 'total_amount': '400.00',
            'paid_by': self.rafay.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'equal',
        })
        self.assertEqual(Settlement.objects.count(), 0)

        self.client.post(f'/groups/{self.group.pk}/settlements/mark-paid/', {
            'from_person': self.ali.pk, 'to_person': self.rafay.pk, 'amount': '100.00',
        })
        balances = calculate_group_balances(self.group.id)
        self.assertEqual(balances[self.ali], Decimal('0.00'))
        # Asim and Anas are unaffected - still owe their share.
        self.assertEqual(balances[self.asim], Decimal('-100.00'))
        self.assertEqual(balances[self.anas], Decimal('-100.00'))

    def test_settlement_cannot_exceed_outstanding_balance(self):
        self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Trip', 'description': '', 'total_amount': '400.00',
            'paid_by': self.rafay.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'equal',
        })

        response = self.client.post(f'/groups/{self.group.pk}/settlements/mark-paid/', {
            'from_person': self.ali.pk, 'to_person': self.rafay.pk, 'amount': '101.00',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Settlement.objects.filter(group=self.group, status='paid').exists())

    def test_settlement_people_must_be_group_members(self):
        self.client.post(f'/groups/{self.group.pk}/expenses/add/', {
            'title': 'Trip', 'description': '', 'total_amount': '400.00',
            'paid_by': self.rafay.pk, 'category': 'Food',
            'expense_date': '2026-07-10', 'split_type': 'equal',
        })
        outsider = Person.objects.create(user=self.user, name='Outsider')

        response = self.client.post(f'/groups/{self.group.pk}/settlements/mark-paid/', {
            'from_person': outsider.pk, 'to_person': self.rafay.pk, 'amount': '100.00',
        })

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Settlement.objects.filter(from_person=outsider).exists())

    def test_group_dashboard_invalid_filters_do_not_crash(self):
        response = self.client.get('/groups/dashboard/?start_date=bad&end_date=2026-01-01&group=abc')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid date format. Use YYYY-MM-DD.')
