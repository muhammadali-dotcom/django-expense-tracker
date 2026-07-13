import django_filters
from django import forms

from .models import Category, Transaction


class TransactionFilterSet(django_filters.FilterSet):
    date__gte = django_filters.DateFilter(
        field_name='date',
        lookup_expr='gte',
        label='From date',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'},
        ),
    )
    date__lte = django_filters.DateFilter(
        field_name='date',
        lookup_expr='lte',
        label='To date',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'},
        ),
    )
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.none(),
        label='Category',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    transaction_type = django_filters.ChoiceFilter(
        choices=Transaction.TRANSACTION_TYPE,
        label='Type',
        empty_label='All types',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    description = django_filters.CharFilter(
        field_name='description',
        lookup_expr='icontains',
        label='Search description',
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Search…'},
        ),
    )

    class Meta:
        model = Transaction
        fields = ['date', 'category', 'transaction_type', 'description']

    def __init__(self, *args, **kwargs):
        # Accept an explicit `user` kwarg, or fall back to request.user.
        user = kwargs.pop('user', None)
        request = kwargs.get('request')
        if user is None and request is not None:
            user = request.user
        super().__init__(*args, **kwargs)
        if user is not None and user.is_authenticated:
            self.filters['category'].queryset = Category.objects.filter(user=user)
