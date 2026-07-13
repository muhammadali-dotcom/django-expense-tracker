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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,  # Temporary; task 1.3 data migration will back-fill existing rows
    )
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
