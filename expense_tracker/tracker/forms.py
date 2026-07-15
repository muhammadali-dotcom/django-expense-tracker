from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

from .models import Category, Transaction, UserProfile, Person, ExpenseGroup, GroupExpense


class UserRegistrationForm(UserCreationForm):
    """
    Extends Django's UserCreationForm to add a required email field and a
    user-friendly duplicate-username validation error message.
    """

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "A user with that username already exists."
            )
        return username


class CategoryForm(forms.ModelForm):
    """
    ModelForm for Category. Accepts a `user` kwarg so it can validate
    name uniqueness per user and enforce a positive budget.

    Requirements: 2.3, 3.1, 3.5
    """

    class Meta:
        model = Category
        fields = ['name', 'budget']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        budget = cleaned_data.get('budget')
        name = cleaned_data.get('name')

        # Requirement 3.1 / 3.5 — budget must be positive if provided
        if budget is not None and budget <= 0:
            self.add_error('budget', forms.ValidationError(
                "Budget must be a positive number."
            ))

        # Requirement 2.3 — name must be unique per user
        if name:
            qs = Category.objects.filter(user=self.user, name=name)
            # Exclude the current instance when editing
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('name', forms.ValidationError(
                    "You already have a category with this name."
                ))

        return cleaned_data


class TransactionForm(forms.ModelForm):
    """
    ModelForm for Transaction. Filters the category queryset to only show
    categories owned by the current user, and validates that the amount is
    a positive decimal value.

    Requirements: 2.2, 5.2, 5.4
    """

    class Meta:
        model = Transaction
        fields = ['category', 'amount', 'transaction_type', 'date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user is not None:
            self.fields['category'].queryset = Category.objects.filter(user=self.user)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be a positive value.')
        return amount


# ---------------------------------------------------------------------------
# Group Expense Management & Smart Settlement System
# ---------------------------------------------------------------------------

class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['name', 'phone', 'email']


class ExpenseGroupForm(forms.ModelForm):
    class Meta:
        model = ExpenseGroup
        fields = ['name', 'description']


class GroupMemberAddForm(forms.Form):
    """Adds an existing Person (owned by the current user) to a group."""

    person = forms.ModelChoiceField(queryset=Person.objects.none(), label='Person')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.group = kwargs.pop('group')
        super().__init__(*args, **kwargs)
        already_in_group = self.group.members.values_list('pk', flat=True)
        self.fields['person'].queryset = Person.objects.filter(user=self.user).exclude(pk__in=already_in_group)


class GroupExpenseForm(forms.ModelForm):
    """
    Base fields for a group expense. Split-related fields (split_type and
    the per-person amounts/percentages) are handled directly in the view
    since they're dynamic per group membership, not static model fields.
    """

    SPLIT_CHOICES = [
        ('equal', 'Equal Split'),
        ('custom', 'Custom Split'),
        ('percentage', 'Percentage Split'),
    ]

    split_type = forms.ChoiceField(choices=SPLIT_CHOICES, initial='equal')

    class Meta:
        model = GroupExpense
        fields = ['title', 'description', 'total_amount', 'paid_by', 'category', 'expense_date']
        widgets = {
            'expense_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group')
        super().__init__(*args, **kwargs)
        self.fields['paid_by'].queryset = self.group.members.all()

    def clean_total_amount(self):
        amount = self.cleaned_data.get('total_amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be a positive value.')
        return amount


class UserProfileForm(forms.ModelForm):
    """
    ModelForm for UserProfile. Allows the user to update their preferred
    currency.

    Requirements: 15.6, 15.7
    """

    class Meta:
        model = UserProfile
        fields = ['currency']
        widgets = {
            'currency': forms.Select(attrs={'class': 'form-select'}),
        }
