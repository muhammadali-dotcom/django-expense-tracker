from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    TRANSACTION_TYPE = (
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    amount = models.FloatField()
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    date = models.DateField()
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"
