from django.contrib import admin
from .models import (
    BudgetAlert,
    Category,
    Transaction,
    Person,
    ExpenseGroup,
    GroupMember,
    GroupExpense,
    ExpenseSplit,
    Settlement,
)

admin.site.register(Category)
admin.site.register(Transaction)
admin.site.register(BudgetAlert)
admin.site.register(Person)
admin.site.register(ExpenseGroup)
admin.site.register(GroupMember)
admin.site.register(GroupExpense)
admin.site.register(ExpenseSplit)


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ('group', 'from_person', 'to_person', 'amount', 'status', 'created_at')
    list_filter = ('status', 'group')
