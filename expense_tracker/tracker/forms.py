from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

from .models import Category, Transaction, UserProfile


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
