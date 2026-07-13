from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django_filters.views import FilterView

from .filters import TransactionFilterSet
from .forms import CategoryForm, TransactionForm, UserRegistrationForm, UserProfileForm
from .models import Category, Transaction, UserProfile
from .utils import get_budget_status, get_monthly_trend, get_category_trend
from django.utils import timezone
from datetime import datetime


# ---------------------------------------------------------------------------
# Transaction list view  (Requirements 4.1–4.10)
# ---------------------------------------------------------------------------

class TransactionListView(LoginRequiredMixin, FilterView):
    """
    Paginated, filtered transaction list scoped to the authenticated user.

    Uses django-filter's FilterView so the filter form is wired automatically.
    The queryset is restricted to the current user's transactions, and the
    filterset receives the request so TransactionFilterSet can scope its
    category queryset to the same user.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10
    """

    model = Transaction
    filterset_class = TransactionFilterSet
    template_name = 'transaction_list.html'
    paginate_by = 20
    context_object_name = 'transactions'

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        # Pass the request so TransactionFilterSet can scope categories by user
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx['currency_symbol'] = self.request.user.profile.currency_symbol
        except UserProfile.DoesNotExist:
            ctx['currency_symbol'] = '$'
        return ctx


@login_required
def dashboard(request):
    """Dashboard view with optional date-range filter and chart data."""
    # Parse dates from GET parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    error_msg = None
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if start_date > end_date:
                error_msg = 'Start date cannot be after end date.'
        except ValueError:
            error_msg = 'Invalid date format. Use YYYY-MM-DD.'
    else:
        # Default to current month
        today = timezone.now().date()
        start_date = today.replace(day=1)
        # End of month calculation
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)

    # Base queryset filtered by user and date range
    base_qs = Transaction.objects.filter(user=request.user, date__gte=start_date, date__lte=end_date)

    income = base_qs.filter(transaction_type='Income').aggregate(Sum('amount'))['amount__sum'] or 0
    expense = base_qs.filter(transaction_type='Expense').aggregate(Sum('amount'))['amount__sum'] or 0
    net_balance = income - expense

    # Chart helpers
    monthly_trend = get_monthly_trend(request.user, start_date, end_date)
    category_trend = get_category_trend(request.user, start_date, end_date)
    budget_status = get_budget_status(request.user)

    # Currency symbol for display
    try:
        currency_symbol = request.user.profile.currency_symbol
    except UserProfile.DoesNotExist:
        currency_symbol = '$'

    context = {
        'income': income,
        'expense': expense,
        'net_balance': net_balance,
        'monthly_trend': monthly_trend,
        'category_trend': category_trend,
        'budget_status': budget_status,
        'currency_symbol': currency_symbol,
        'error_msg': error_msg,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'dashboard.html', context)


# ---------------------------------------------------------------------------
# Transaction views  (Requirements 5.1, 11.1)
# ---------------------------------------------------------------------------

class AddTransactionView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'add_transaction.html'
    success_url = reverse_lazy('transaction_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Transaction added successfully.')
        return super().form_valid(form)

class EditTransactionView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'edit_transaction.html'
    success_url = reverse_lazy('transaction_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Transaction updated successfully.')
        return super().form_valid(form)

class DeleteTransactionView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = 'delete_transaction.html'
    success_url = reverse_lazy('transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Transaction deleted successfully.')
        return super().delete(request, *args, **kwargs)

import csv
from django.http import HttpResponse

def export_csv(request):
    """Export CSV of filtered transactions for the current user."""
    # Reuse the same filterset to respect active filters
    filterset = TransactionFilterSet(request.GET, queryset=Transaction.objects.filter(user=request.user))
    qs = filterset.qs
    response = HttpResponse(content_type='text/csv')
    filename = f"transactions_{timezone.now().date()}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Description'])
    for tx in qs:
        writer.writerow([
            tx.date,
            tx.transaction_type,
            tx.category.name if tx.category else '' ,
            float(tx.amount),
            tx.description,
        ])
    return response


def user_register(request):
    """
    Registration view. Redirects already-authenticated users to the dashboard.
    On valid POST: creates the user, logs them in, and redirects to dashboard.
    No @login_required — must be publicly accessible.
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = UserRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('dashboard')

    return render(request, 'register.html', {'form': form})


def login_user(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user:
            login(request, user)
            return redirect('dashboard')

    return render(request, 'login.html')


def logout_user(request):
    logout(request)
    return redirect('login')


# ---------------------------------------------------------------------------
# Category views  (Requirements 2.2, 2.3, 2.4, 2.5, 2.6, 11.4)
# ---------------------------------------------------------------------------

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['budget_status'] = get_budget_status(self.request.user)
        return ctx


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'category_form.html'
    success_url = reverse_lazy('category_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Category created successfully.')
        return super().form_valid(form)


class CategoryEditView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'category_form.html'
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully.')
        return super().form_valid(form)


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'category_confirm_delete.html'
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Raise 403 if the object does not belong to the requesting user
        if obj.user != self.request.user:
            raise PermissionDenied
        return obj

    def form_valid(self, form):
        messages.success(self.request, 'Category deleted successfully.')
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Profile view  (Requirements 15.1–15.7, 11.5)
# ---------------------------------------------------------------------------

@login_required
def profile(request):
    """
    Handles the user profile page with two independent forms:
    - PasswordChangeForm: lets the user change their password
    - UserProfileForm: lets the user update their currency preference

    The active form is identified by a hidden ``form_type`` input whose value
    is either ``'password'`` or ``'currency'``.

    Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 11.5
    """
    # Ensure a UserProfile exists for this user (graceful recovery)
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    password_form = PasswordChangeForm(request.user)
    currency_form = UserProfileForm(instance=user_profile)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Keep the user logged in after password change
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was updated successfully.')
                return redirect('profile')
            # Falls through to render with password errors shown

        elif form_type == 'currency':
            currency_form = UserProfileForm(request.POST, instance=user_profile)
            if currency_form.is_valid():
                currency_form.save()
                messages.success(request, 'Your currency preference was saved.')
                return redirect('profile')
            # Falls through to render with currency errors shown

    return render(request, 'profile.html', {
        'password_form': password_form,
        'currency_form': currency_form,
    })
