from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django_filters.views import FilterView

from .filters import TransactionFilterSet
from .forms import (
    CategoryForm, TransactionForm, UserRegistrationForm, UserProfileForm,
    PersonForm, ExpenseGroupForm, GroupMemberAddForm, GroupExpenseForm,
)
from .models import (
    Category, Transaction, UserProfile,
    Person, ExpenseGroup, GroupMember, GroupExpense, ExpenseSplit, Settlement,
)
from .utils import get_budget_status, get_monthly_trend, get_category_trend, check_and_send_budget_alert
from .group_services import (
    calculate_equal_shares, validate_custom_split, calculate_percentage_shares,
    calculate_group_balances, generate_settlement_plan, get_dashboard_stats,
)
from datetime import datetime

from django.utils import timezone
from django.core.validators import validate_integer


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
    today = timezone.now().date()
    default_start_date = today.replace(day=1)
    # End of month calculation
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    default_end_date = today.replace(day=last_day)

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
                start_date, end_date = default_start_date, default_end_date
        except ValueError:
            error_msg = 'Invalid date format. Use YYYY-MM-DD.'
            start_date, end_date = default_start_date, default_end_date
    else:
        start_date, end_date = default_start_date, default_end_date

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
        response = super().form_valid(form)
        if self.object.transaction_type == 'Expense' and self.object.category_id:
            check_and_send_budget_alert(self.request.user, self.object.category)
        return response

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
        response = super().form_valid(form)
        if self.object.transaction_type == 'Expense' and self.object.category_id:
            check_and_send_budget_alert(self.request.user, self.object.category)
        return response

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
from django.http import HttpResponse, JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok'})

@login_required
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


# ---------------------------------------------------------------------------
# Group Expense Management & Smart Settlement System
# ---------------------------------------------------------------------------

class PersonListView(LoginRequiredMixin, ListView):
    model = Person
    template_name = 'groups/person_list.html'
    context_object_name = 'people'

    def get_queryset(self):
        return Person.objects.filter(user=self.request.user)


class PersonCreateView(LoginRequiredMixin, CreateView):
    model = Person
    form_class = PersonForm
    template_name = 'groups/person_form.html'
    success_url = reverse_lazy('person_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Person added successfully.')
        return super().form_valid(form)


class PersonEditView(LoginRequiredMixin, UpdateView):
    model = Person
    form_class = PersonForm
    template_name = 'groups/person_form.html'
    success_url = reverse_lazy('person_list')

    def get_queryset(self):
        return Person.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Person updated successfully.')
        return super().form_valid(form)


class PersonDeleteView(LoginRequiredMixin, DeleteView):
    model = Person
    template_name = 'groups/person_confirm_delete.html'
    success_url = reverse_lazy('person_list')

    def get_queryset(self):
        return Person.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Person deleted successfully.')
        return super().delete(request, *args, **kwargs)


class ExpenseGroupListView(LoginRequiredMixin, ListView):
    model = ExpenseGroup
    template_name = 'groups/group_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        return ExpenseGroup.objects.filter(user=self.request.user).prefetch_related('members')


class ExpenseGroupCreateView(LoginRequiredMixin, CreateView):
    model = ExpenseGroup
    form_class = ExpenseGroupForm
    template_name = 'groups/group_form.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Group created successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('group_detail', kwargs={'pk': self.object.pk})


class ExpenseGroupEditView(LoginRequiredMixin, UpdateView):
    model = ExpenseGroup
    form_class = ExpenseGroupForm
    template_name = 'groups/group_form.html'

    def get_queryset(self):
        return ExpenseGroup.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Group updated successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('group_detail', kwargs={'pk': self.object.pk})


class ExpenseGroupDeleteView(LoginRequiredMixin, DeleteView):
    model = ExpenseGroup
    template_name = 'groups/group_confirm_delete.html'
    success_url = reverse_lazy('group_list')

    def get_queryset(self):
        return ExpenseGroup.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Group deleted successfully.')
        return super().delete(request, *args, **kwargs)


class ExpenseGroupDetailView(LoginRequiredMixin, DetailView):
    model = ExpenseGroup
    template_name = 'groups/group_detail.html'
    context_object_name = 'group'

    def get_queryset(self):
        return ExpenseGroup.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group = self.object
        balances = calculate_group_balances(group.id)
        ctx['group_members'] = group.group_members.select_related('person').all()
        ctx['balances'] = sorted(
            balances.items(), key=lambda item: item[1], reverse=True
        )
        ctx['settlement_plan'] = generate_settlement_plan(group.id)
        ctx['expenses'] = group.expenses.select_related('paid_by').prefetch_related('splits__person')
        ctx['member_add_form'] = GroupMemberAddForm(user=self.request.user, group=group)
        ctx['total_spent'] = group.expenses.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        return ctx


@login_required
def group_member_add(request, pk):
    group = get_object_or_404(ExpenseGroup, pk=pk, user=request.user)
    if request.method == 'POST':
        form = GroupMemberAddForm(request.POST, user=request.user, group=group)
        if form.is_valid():
            GroupMember.objects.create(group=group, person=form.cleaned_data['person'])
            messages.success(request, 'Member added to group.')
        else:
            messages.error(request, 'Could not add member — please select a valid person.')
    return redirect('group_detail', pk=pk)


@login_required
@require_POST
def group_member_remove(request, pk, member_pk):
    group = get_object_or_404(ExpenseGroup, pk=pk, user=request.user)
    member = get_object_or_404(GroupMember, pk=member_pk, group=group)
    member.delete()
    messages.success(request, 'Member removed from group.')
    return redirect('group_detail', pk=pk)


def _parse_decimal(raw_value):
    raw_value = (raw_value or '0').strip() or '0'
    return Decimal(raw_value)


def _parse_date_filter(raw_value):
    if not raw_value:
        return None
    try:
        return datetime.strptime(raw_value, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('Invalid date format. Use YYYY-MM-DD.') from exc


@login_required
def group_expense_create(request, pk):
    group = get_object_or_404(ExpenseGroup, pk=pk, user=request.user)
    members = list(group.members.all())

    if request.method == 'POST':
        form = GroupExpenseForm(request.POST, group=group)
        if form.is_valid():
            split_type = form.cleaned_data['split_type']
            total_amount = form.cleaned_data['total_amount']
            try:
                if split_type == 'equal':
                    shares = calculate_equal_shares(total_amount, members)
                elif split_type == 'custom':
                    shares = {m: _parse_decimal(request.POST.get(f'share_{m.id}')) for m in members}
                    validate_custom_split(total_amount, shares)
                else:  # percentage
                    percentages = {m: _parse_decimal(request.POST.get(f'percent_{m.id}')) for m in members}
                    shares = calculate_percentage_shares(total_amount, percentages)

                expense = form.save(commit=False)
                expense.group = group
                expense.save()
                for person, amount in shares.items():
                    ExpenseSplit.objects.create(expense=expense, person=person, share_amount=amount)

                messages.success(request, 'Expense added and split successfully.')
                return redirect('group_detail', pk=group.pk)
            except (ValueError, InvalidOperation) as exc:
                form.add_error(None, str(exc) or 'Invalid split values.')
    else:
        form = GroupExpenseForm(group=group, initial={'expense_date': timezone.now().date()})

    return render(request, 'groups/group_expense_form.html', {
        'form': form,
        'group': group,
        'members': members,
    })


@login_required
def group_expense_edit(request, pk):
    expense = get_object_or_404(GroupExpense, pk=pk, group__user=request.user)
    group = expense.group
    members = list(group.members.all())
    existing_shares = {split.person_id: split.share_amount for split in expense.splits.all()}

    if request.method == 'POST':
        form = GroupExpenseForm(request.POST, instance=expense, group=group)
        if form.is_valid():
            split_type = form.cleaned_data['split_type']
            total_amount = form.cleaned_data['total_amount']
            try:
                if split_type == 'equal':
                    shares = calculate_equal_shares(total_amount, members)
                elif split_type == 'custom':
                    shares = {m: _parse_decimal(request.POST.get(f'share_{m.id}')) for m in members}
                    validate_custom_split(total_amount, shares)
                else:  # percentage
                    percentages = {m: _parse_decimal(request.POST.get(f'percent_{m.id}')) for m in members}
                    shares = calculate_percentage_shares(total_amount, percentages)

                expense = form.save()
                expense.splits.all().delete()
                for person, amount in shares.items():
                    ExpenseSplit.objects.create(expense=expense, person=person, share_amount=amount)

                messages.success(request, 'Expense updated successfully.')
                return redirect('group_detail', pk=group.pk)
            except (ValueError, InvalidOperation) as exc:
                form.add_error(None, str(exc) or 'Invalid split values.')
    else:
        form = GroupExpenseForm(instance=expense, group=group, initial={'split_type': 'custom'})

    return render(request, 'groups/group_expense_form.html', {
        'form': form,
        'group': group,
        'members': members,
        'existing_shares': existing_shares,
        'is_edit': True,
    })


class GroupExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = GroupExpense
    template_name = 'groups/group_expense_confirm_delete.html'

    def get_queryset(self):
        return GroupExpense.objects.filter(group__user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('group_detail', kwargs={'pk': self.object.group_id})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Expense deleted successfully.')
        return super().delete(request, *args, **kwargs)


@login_required
@require_POST
def settlement_mark_paid(request, pk):
    group = get_object_or_404(ExpenseGroup, pk=pk, user=request.user)
    from_person = get_object_or_404(Person, pk=request.POST.get('from_person'), user=request.user, groups=group)
    to_person = get_object_or_404(Person, pk=request.POST.get('to_person'), user=request.user, groups=group)
    try:
        amount = Decimal(request.POST.get('amount', '0'))
    except InvalidOperation:
        messages.error(request, 'Invalid settlement amount.')
        return redirect('group_detail', pk=pk)

    if amount <= 0:
        messages.error(request, 'Settlement amount must be positive.')
        return redirect('group_detail', pk=pk)

    settlement_plan = generate_settlement_plan(group.id)
    matching_entry = next(
        (
            entry for entry in settlement_plan
            if entry['from'].pk == from_person.pk and entry['to'].pk == to_person.pk
        ),
        None,
    )
    if matching_entry is None:
        messages.error(request, 'That settlement is not currently owed for this group.')
        return redirect('group_detail', pk=pk)
    if amount > matching_entry['amount']:
        messages.error(request, 'Settlement amount cannot exceed the outstanding balance.')
        return redirect('group_detail', pk=pk)

    Settlement.objects.create(
        group=group, from_person=from_person, to_person=to_person,
        amount=amount, status='paid',
    )
    messages.success(request, f'Marked {from_person.name} → {to_person.name} ({amount}) as paid.')
    return redirect('group_detail', pk=pk)


@login_required
def group_dashboard(request):
    """
    Optional GET filters (start_date, end_date, group) narrow the recent
    expenses list and which group's settlements are shown; with no params
    (the default) behavior is unchanged from before these were added.
    """
    stats = get_dashboard_stats(request.user)
    groups = ExpenseGroup.objects.filter(user=request.user).prefetch_related('members')

    start_date = request.GET.get('start_date') or ''
    end_date = request.GET.get('end_date') or ''
    selected_group_id = request.GET.get('group') or ''
    error_msg = None

    filtered_expenses = GroupExpense.objects.filter(group__user=request.user)
    try:
        parsed_start_date = _parse_date_filter(start_date)
        parsed_end_date = _parse_date_filter(end_date)
        if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
            raise ValueError('Start date cannot be after end date.')
    except ValueError as exc:
        error_msg = str(exc) if str(exc) else 'Invalid date format. Use YYYY-MM-DD.'
        start_date = end_date = ''
        parsed_start_date = parsed_end_date = None

    if parsed_start_date:
        filtered_expenses = filtered_expenses.filter(expense_date__gte=parsed_start_date)
    if parsed_end_date:
        filtered_expenses = filtered_expenses.filter(expense_date__lte=parsed_end_date)
    if selected_group_id:
        try:
            validate_integer(selected_group_id)
        except ValidationError:
            selected_group_id = ''
            error_msg = error_msg or 'Invalid group filter.'
        else:
            if not groups.filter(pk=selected_group_id).exists():
                selected_group_id = ''
                error_msg = error_msg or 'Invalid group filter.'

    if selected_group_id:
        filtered_expenses = filtered_expenses.filter(group_id=selected_group_id)

    recent_expenses = filtered_expenses.select_related('group', 'paid_by')[:10]

    monthly = {}
    for expense in filtered_expenses:
        label = expense.expense_date.strftime('%Y-%m')
        monthly[label] = monthly.get(label, Decimal('0.00')) + expense.total_amount
    monthly_expenses = [{'month': m, 'total': round(float(monthly[m]))} for m in sorted(monthly)]

    category_totals = list(
        filtered_expenses.values('category')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')
    )
    for row in category_totals:
        row['total'] = round(float(row['total']))

    settlement_groups = groups.filter(pk=selected_group_id) if selected_group_id else groups
    pending_settlements = []
    for group in settlement_groups:
        for entry in generate_settlement_plan(group.id):
            pending_settlements.append({'group': group, **entry})

    return render(request, 'groups/group_dashboard.html', {
        'stats': stats,
        'groups': groups,
        'recent_expenses': recent_expenses,
        'pending_settlements': pending_settlements,
        'monthly_expenses': monthly_expenses,
        'category_totals': category_totals,
        'start_date': start_date,
        'end_date': end_date,
        'selected_group_id': selected_group_id,
        'error_msg': error_msg,
    })


@login_required
def group_reports(request):
    expenses = GroupExpense.objects.filter(group__user=request.user)

    monthly = {}
    for expense in expenses:
        label = expense.expense_date.strftime('%Y-%m')
        monthly[label] = monthly.get(label, Decimal('0.00')) + expense.total_amount
    monthly_expenses = [{'month': m, 'total': monthly[m]} for m in sorted(monthly)]

    category_totals = (
        expenses.values('category')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')
    )

    return render(request, 'groups/group_reports.html', {
        'monthly_expenses': monthly_expenses,
        'category_totals': category_totals,
    })
