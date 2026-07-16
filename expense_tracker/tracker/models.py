from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    CURRENCY_CHOICES = [
        ('USD', '$ USD'),
        ('EUR', '€ EUR'),
        ('GBP', '£ GBP'),
        ('PKR', '₨ PKR'),
        ('INR', '₹ INR'),
    ]
    CURRENCY_SYMBOLS = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'PKR': '₨', 'INR': '₹'
    }

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
    )

    def __str__(self):
        return f"{self.user.username} profile"

    @property
    def currency_symbol(self):
        return self.CURRENCY_SYMBOLS.get(self.currency, '$')


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories', null=True)
    name = models.CharField(max_length=100)
    budget = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
    )

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name


class Transaction(models.Model):
    TRANSACTION_TYPE = (
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    date = models.DateField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"


# ---------------------------------------------------------------------------
# Group Expense Management & Smart Settlement System
#
# Scoped the same way as Category/Transaction: every top-level object
# (Person, ExpenseGroup) carries a direct `user` FK to the owning account.
# Nested objects (GroupMember, GroupExpense, ExpenseSplit, Settlement) are
# scoped indirectly through their group/person FK chain.
# ---------------------------------------------------------------------------

class Person(models.Model):
    """A person who can participate in group expenses (not a login account)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='people')
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ExpenseGroup(models.Model):
    """A group of people who share expenses, e.g. 'University Friends'."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expense_groups')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(Person, through='GroupMember', related_name='groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    """Membership of a Person in an ExpenseGroup."""

    group = models.ForeignKey(ExpenseGroup, on_delete=models.CASCADE, related_name='group_members')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='memberships')
    joined_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'person')

    def __str__(self):
        return f"{self.person.name} in {self.group.name}"


class GroupExpense(models.Model):
    """A single expense within a group, paid by one member and split among others."""

    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Travel', 'Travel'),
        ('Shopping', 'Shopping'),
        ('Utilities', 'Utilities'),
        ('Entertainment', 'Entertainment'),
        ('Other', 'Other'),
    ]

    group = models.ForeignKey(ExpenseGroup, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.ForeignKey(Person, on_delete=models.PROTECT, related_name='paid_expenses')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Other')
    expense_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-expense_date', '-id']

    def __str__(self):
        return f"{self.title} ({self.total_amount})"


class ExpenseSplit(models.Model):
    """One person's share of a GroupExpense."""

    expense = models.ForeignKey(GroupExpense, on_delete=models.CASCADE, related_name='splits')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='expense_splits')
    share_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('expense', 'person')

    def __str__(self):
        return f"{self.person.name}: {self.share_amount}"


class Settlement(models.Model):
    """A record of a debt being paid off between two people in a group."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]

    group = models.ForeignKey(ExpenseGroup, on_delete=models.CASCADE, related_name='settlements')
    from_person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='settlements_owed')
    to_person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='settlements_receivable')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.from_person.name} -> {self.to_person.name}: {self.amount} ({self.status})"
