# Design Document: Expense Tracker Upgrade

## Overview

This document describes the technical design for a comprehensive upgrade of the existing Django expense tracker application. The upgrade adds 15 new feature areas on top of the current foundation: a Django 4.x app using SQLite, Bootstrap 5, and a `tracker` app with `Category` and `Transaction` models.

The primary goals are:
- Extend the data model to support per-user categories, budget limits, and user profile preferences
- Add full transaction management (list, filter, search, edit, delete, CSV export)
- Enrich the dashboard with net balance, date-range filtering, and two new Chart.js charts
- Modernize the UI with a sidebar layout, toast notifications, and dark mode
- Add user self-registration and a profile page

All changes remain within the existing Django + Bootstrap 5 stack. No new backend frameworks are introduced. The existing `tracker` app is extended in-place.

---

## Architecture

The application follows Django's standard MVT (Model-View-Template) pattern. The upgrade extends each layer:

```
┌──────────────────────────────────────────────────────────────┐
│                        Browser                               │
│  Bootstrap 5 + Chart.js + Vanilla JS (dark mode, toasts)     │
└──────────────────┬───────────────────────────────────────────┘
                   │ HTTP
┌──────────────────▼───────────────────────────────────────────┐
│                    Django (tracker app)                       │
│                                                              │
│  URLs ──► Views ──► Forms ──► Models ──► SQLite              │
│                │                                             │
│             Templates (Jinja2/DTL + Bootstrap 5)             │
└──────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

1. **No new apps**: All new functionality is added inside the existing `tracker` app to minimise structural churn.
2. **Django messages framework**: Used for all toast notifications. The `base.html` template renders queued messages as Bootstrap toasts.
3. **UserProfile via OneToOneField**: Currency preference is stored in a `UserProfile` model linked to Django's built-in `User`.
4. **Client-side dark mode**: The dark/light theme is toggled by adding a `data-bs-theme` attribute to `<html>` via JavaScript and persisted in `localStorage`. No server round-trip required.
5. **Django's built-in `PasswordChangeForm`**: Used for password changes to leverage existing validation and session handling.
6. **Class-based views (CBVs) for list/detail/edit/delete**: `ListView`, `CreateView`, `UpdateView`, `DeleteView` reduce boilerplate for CRUD operations. Existing function-based views are kept where refactoring would add risk.
7. **`django-filter` library**: Provides clean filter form integration for the transaction list without hand-rolling queryset logic.

---

## Components and Interfaces

### URL Structure (updated)

```
/                          → dashboard (existing, extended)
/register/                 → user_register (new)
/login/                    → login_user (existing)
/logout/                   → logout_user (existing)
/transactions/             → transaction_list (new)
/transactions/add/         → add_transaction (replaces /add/)
/transactions/<pk>/edit/   → edit_transaction (new)
/transactions/<pk>/delete/ → delete_transaction (new)
/transactions/export/      → export_csv (new)
/categories/               → category_list (new)
/categories/add/           → category_create (new)
/categories/<pk>/edit/     → category_edit (new)
/categories/<pk>/delete/   → category_delete (new)
/profile/                  → profile (new)
```

### Views

| View | Type | Auth | Description |
|---|---|---|---|
| `dashboard` | FBV | ✓ | Extended with date-range filter, net balance, and chart data |
| `user_register` | FBV | ✗ | Registration form processing |
| `transaction_list` | CBV `FilterView` | ✓ | Paginated, filtered transaction list with CSV export link |
| `add_transaction` | CBV `CreateView` | ✓ | Create transaction (moved from `/add/`) |
| `edit_transaction` | CBV `UpdateView` | ✓ | Edit existing transaction with ownership check |
| `delete_transaction` | CBV `DeleteView` | ✓ | Delete with confirmation; ownership enforced |
| `export_csv` | FBV | ✓ | Streams CSV with current filter state |
| `category_list` | CBV `ListView` | ✓ | Category management page with budget display |
| `category_create` | CBV `CreateView` | ✓ | Create user-owned category |
| `category_edit` | CBV `UpdateView` | ✓ | Edit name/budget with ownership check |
| `category_delete` | CBV `DeleteView` | ✓ | Delete with 403 guard |
| `profile` | FBV | ✓ | Password change + currency preference |

### Forms

| Form | Base | Purpose |
|---|---|---|
| `UserRegistrationForm` | `UserCreationForm` | Adds email field; custom clean validates uniqueness |
| `TransactionForm` | `ModelForm` | Amount, type, category (user-scoped), date, description; validates positive amount |
| `TransactionFilterForm` | `django-filter` `FilterSet` | Date range, category, type, description search |
| `CategoryForm` | `ModelForm` | Name + optional budget; validates duplicate name per user, positive budget |
| `PasswordChangeForm` | Django built-in | Current/new/confirm password |
| `UserProfileForm` | `ModelForm` | Currency preference selector |

### Templates

All templates extend a new `base.html` that introduces the sidebar layout:

```
base.html
├── sidebar (partial: _sidebar.html)
├── topbar (partial: _topbar.html — brand + dark-mode toggle)
├── toast container (renders Django messages)
└── {% block content %}

dashboard.html         — extends base.html
transaction_list.html  — extends base.html
add_transaction.html   — extends base.html  (updated path)
edit_transaction.html  — extends base.html
category_list.html     — extends base.html
profile.html           — extends base.html
register.html          — standalone (no sidebar; extends base.html)
login.html             — standalone (updated with register link)
```

---

## Data Models

### Updated `Category` model

```python
class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories'
    )
    name = models.CharField(max_length=100)
    budget = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name
```

Migration strategy: The existing global `Category` rows (if any) will be assigned to a default admin user or deleted during a data migration. A `RunPython` migration step handles this.

### Updated `Transaction` model

```python
class Transaction(models.Model):
    TRANSACTION_TYPE = (
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE)
    date = models.DateField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"
```

Note: `amount` is changed from `FloatField` to `DecimalField` to avoid floating-point precision issues with financial data.

### New `UserProfile` model

```python
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
        related_name='profile'
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD'
    )

    def __str__(self):
        return f"{self.user.username} profile"
```

A `post_save` signal on `User` creates a `UserProfile` automatically.

### Entity-Relationship Diagram

```
User (Django built-in)
 ├── UserProfile (1:1)
 ├── Category (1:N)  ← has optional budget
 └── Transaction (1:N) → Category (N:1, nullable)
```

### Budget Warning Computation

Computed in the view (not stored) to avoid stale data:

```python
from django.utils import timezone
from django.db.models import Sum

def get_budget_status(user):
    now = timezone.now().date()
    categories = Category.objects.filter(user=user).exclude(budget__isnull=True)
    results = []
    for cat in categories:
        spent = Transaction.objects.filter(
            user=user,
            category=cat,
            transaction_type='Expense',
            date__year=now.year,
            date__month=now.month,
        ).aggregate(total=Sum('amount'))['total'] or 0
        pct = (spent / cat.budget * 100) if cat.budget else 0
        results.append({'category': cat, 'spent': spent, 'pct': pct})
    return results
```

### Chart Data Computation

**Monthly bar chart** (12 months, income vs expense):

```python
def get_monthly_trend(user, start_date, end_date):
    # Returns list of {'month': 'YYYY-MM', 'income': D, 'expense': D}
    # for each month in the range, with zero-filling for empty months
```

**Category spending trend** (6 months per-category):

```python
def get_category_trend(user, start_date, end_date):
    # Returns {'labels': [...months], 'datasets': [{'label': cat_name, 'data': [...]}]}
    # Only includes categories with at least one expense in the period
```

Both helpers live in a new `tracker/utils.py` module and accept a date range, making them pure functions suitable for testing.

### Currency Display

A custom template filter renders amounts with the user's currency symbol:

```python
# tracker/templatetags/currency_tags.py
@register.filter
def currency_format(amount, user):
    symbol = user.profile.currency_symbol
    return f"{symbol}{amount:,.2f}"
```

A context processor injects `currency_symbol` into every template context so the symbol is available globally without repetitive view code.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

#### Redundancy Analysis

Before listing properties, redundancy is eliminated:

- 3.3 (80% warning) and 3.4 (100% warning) both concern budget thresholds. Combined into one threshold property.
- 6.1 (net balance computation) and 6.5 (net balance after date filter) are the same computation parameterized by range. Combined.
- 4.3, 4.4, 4.5, 4.6 are all individual filter correctness properties. Combined into a single "filter correctness" property covering all filter types, including their AND combination (4.7).
- 8.4 (zero value for empty month) and 9.4 (zero value for category/month with no expenses) are both zero-fill invariants on chart data. Combined.
- 14.2 and 14.3 both concern CSV output correctness. Combined into one CSV output property.
- 15.3 and 15.4 are both password form rejection properties. Combined.

---

### Property 1: User Registration Rejects Invalid Inputs

*For any* registration submission where either (a) the username already exists, (b) the passwords do not match, or (c) a required field is empty, the system SHALL reject the submission, return a form with errors, and leave the user count unchanged.

**Validates: Requirements 1.2, 1.3, 1.5**

---

### Property 2: Successful Registration Creates and Authenticates User

*For any* registration submission with a unique username, valid email, and matching non-empty passwords, the system SHALL create exactly one new `User` record, authenticate that user, and redirect to the dashboard.

**Validates: Requirements 1.4**

---

### Property 3: Category Isolation Between Users

*For any* two users A and B with their own categories, the category selector shown to user A SHALL contain only user A's categories, and the selector shown to user B SHALL contain only user B's categories — with no cross-user visibility.

**Validates: Requirements 2.2**

---

### Property 4: Category Ownership Enforcement (403)

*For any* category owned by user A, a modification or deletion request made by user B SHALL return a 403 Forbidden response and leave the category unchanged.

**Validates: Requirements 2.6**

---

### Property 5: Category Deletion Nullifies Transaction References

*For any* category C and any set of transactions referencing C, deleting C SHALL set the `category` field of all those transactions to `null` and SHALL NOT delete those transactions.

**Validates: Requirements 2.5**

---

### Property 6: Budget Threshold Indicators

*For any* category with a positive budget amount B and a current-month expense total S:
- When S/B ≥ 1.0, the over-budget indicator SHALL be displayed.
- When 0.8 ≤ S/B < 1.0, the warning indicator SHALL be displayed.
- When S/B < 0.8, no budget indicator SHALL be displayed.

**Validates: Requirements 3.3, 3.4**

---

### Property 7: Transaction Filter Correctness

*For any* combination of active filters (date range, category, type, description search term), every transaction returned by the transaction list SHALL satisfy ALL active filter conditions simultaneously, and no transaction failing any active condition SHALL appear in the results.

**Validates: Requirements 4.3, 4.4, 4.5, 4.6, 4.7**

---

### Property 8: Pagination Invariant

*For any* set of N transactions where N > 20, each page of the transaction list SHALL contain at most 20 transactions, and the union of all pages SHALL equal the complete filtered set.

**Validates: Requirements 4.2**

---

### Property 9: Transaction List Ordering

*For any* set of transactions, the transaction list SHALL return them in reverse-chronological order (newest date first; ties broken by descending `id`).

**Validates: Requirements 4.1**

---

### Property 10: Transaction Edit Pre-Population and Save

*For any* transaction T, the edit form SHALL be pre-populated with T's current field values, and submitting the form with valid new values SHALL update T's stored values to match the submitted values exactly.

**Validates: Requirements 5.2, 5.3**

---

### Property 11: Transaction Edit Rejects Non-Positive Amounts

*For any* submitted edit form where the amount field is zero, negative, or non-numeric, the system SHALL return a validation error and leave the transaction's stored amount unchanged.

**Validates: Requirements 5.4**

---

### Property 12: Transaction Deletion Removes Record

*For any* transaction T owned by the authenticated user, confirming deletion SHALL result in T no longer being retrievable from the database for that user.

**Validates: Requirements 5.6**

---

### Property 13: Transaction Ownership Enforcement (403)

*For any* transaction T owned by user A, an edit or delete request made by user B SHALL return a 403 Forbidden response and leave T unchanged.

**Validates: Requirements 5.7**

---

### Property 14: Net Balance Computation Correctness

*For any* date range [start, end] and any set of transactions within that range, the displayed net balance SHALL equal (sum of Income transaction amounts) − (sum of Expense transaction amounts) for transactions in that range, and the color indicator SHALL be green for positive values, neutral for zero, and red for negative values.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

---

### Property 15: Date-Range Filter Consistency

*For any* date range where start ≤ end, all dashboard metrics (income total, expense total, net balance, bar chart data, category trend data) SHALL be computed exclusively from transactions whose date falls within [start, end].

**Validates: Requirements 7.4, 8.2, 9.2**

---

### Property 16: Chart Zero-Fill for Empty Periods

*For any* month or (category, month) pair that has no transactions in the dataset, the corresponding chart value SHALL be exactly 0.

**Validates: Requirements 8.4, 9.4**

---

### Property 17: CSV Output Correctness and User Isolation

*For any* authenticated user and any active filter state, the exported CSV SHALL (a) contain a header row with exactly the columns Date, Type, Category, Amount, Description; (b) include only that user's transactions matching the active filters; and (c) have a filename matching `transactions_YYYY-MM-DD.csv` with the current date.

**Validates: Requirements 14.2, 14.3, 14.5**

---

### Property 18: Password Change Form Correctness

*For any* password-change form submission where either (a) the current password is incorrect or (b) the new password and confirmation do not match, the system SHALL reject the submission with an error and leave the user's password unchanged.

*For any* valid submission (correct current password, matching new passwords), the system SHALL update the password and keep the user authenticated.

**Validates: Requirements 15.3, 15.4, 15.5**

---

### Property 19: Currency Symbol Consistency

*For any* saved currency preference C, every monetary amount rendered in the application (dashboard cards, transaction list, CSV) SHALL be prefixed with the symbol corresponding to C.

**Validates: Requirements 15.7**

---

### Property 20: Success Actions Produce Toast Messages

*For any* successful create, update, or delete operation on a Transaction or Category, and any successful password change or currency preference save, the subsequent page render SHALL contain a Django success message that is rendered as a toast.

**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**

---

## Error Handling

### HTTP 403 — Ownership Violations
All CBVs that operate on user-owned objects (transactions, categories) override `get_queryset()` to filter by `user=request.user`. A request for an object belonging to another user raises `Http404` (object not in queryset). For explicit cross-user attempts detected at the view level, `PermissionDenied` is raised, which Django renders as 403.

```python
class EditTransactionView(LoginRequiredMixin, UpdateView):
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
```

### Form Validation Errors
All forms use Django's built-in form validation. Errors are rendered inline next to fields using Bootstrap's `is-invalid` / `invalid-feedback` classes. No custom error pages are needed for form validation.

### Authentication
`LoginRequiredMixin` (CBVs) and `@login_required` (FBVs) are applied to all views requiring authentication. Unauthenticated requests redirect to `/login/`.

### Date Range Validation
In the dashboard view, if `start_date > end_date`, the filter is not applied and an error message is added to the context for template rendering. The default date range (current month) is used instead.

### Category Deletion with Transactions
Handled by the `ON DELETE SET NULL` constraint on `Transaction.category`, which Django executes automatically at the database level. No extra application-level code required.

### Empty CSV Export
When no transactions match the active filters, the CSV writer writes only the header row and returns a 200 response. This is valid CSV.

### Password Change Session Continuity
After `PasswordChangeForm` saves successfully, `update_session_auth_hash(request, user)` is called to prevent the user being logged out when their password changes.

---

## Testing Strategy

### Overview

The testing approach uses Django's built-in `TestCase` with `pytest-django` as the test runner, plus `hypothesis` for property-based tests. Tests live in `tracker/tests/` split by concern.

```
tracker/tests/
├── __init__.py
├── test_models.py        — model constraints, budget computation helpers
├── test_views_auth.py    — registration, login, 403 enforcement
├── test_views_transactions.py — filter, pagination, edit/delete
├── test_views_categories.py   — CRUD, ownership
├── test_views_dashboard.py    — net balance, chart data helpers
├── test_views_profile.py      — password change, currency preference
├── test_csv_export.py         — CSV output correctness
├── test_properties.py         — all property-based tests (Hypothesis)
└── test_utils.py              — chart data helper functions
```

### Unit Tests

Unit tests cover:
- Model `__str__` methods and `Meta.ordering`
- `CategoryForm` duplicate-name validation per user
- `TransactionForm` positive-amount validation
- `UserRegistrationForm` field presence and password-match validation
- Dashboard view default date range (current month)
- Empty-state rendering in transaction list

### Property-Based Tests (Hypothesis)

**Library**: [`hypothesis`](https://hypothesis.readthedocs.io/) with `hypothesis[django]`  
**Minimum iterations**: 100 per property (Hypothesis default `max_examples=100`)  
**Tag format in comments**: `# Feature: expense-tracker-upgrade, Property N: <property_text>`

Each property in the Correctness Properties section maps to one `@given`-decorated test function in `test_properties.py`. Strategies generate:
- `st.text(min_size=1)` for usernames, descriptions, category names
- `st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'))` for amounts
- `st.dates()` for transaction dates, date range start/end pairs
- `st.sampled_from(['Income', 'Expense'])` for transaction types
- `st.sampled_from(['USD', 'EUR', 'GBP', 'PKR', 'INR'])` for currency codes

Properties involving views are tested against the Django test client using `hypothesis` with `django_db` markers (via `pytest-django`).

Properties involving pure helper functions (chart data, budget computation) are tested directly without database access where possible, using in-memory model instances.

### Integration / Smoke Tests

- Smoke: GET `/register/` returns 200 unauthenticated
- Smoke: GET `/profile/` returns 200 for authenticated user  
- Integration: Full registration → login → add transaction → dashboard flow
- Integration: Delete category → assert linked transactions have null category
- Integration: CSV export with active filters → assert only matching rows appear

### Client-Side Behavior (Not Unit Tested)

The following behaviors are client-side JavaScript and are not covered by server-side unit or property tests. They should be verified manually or with browser automation (e.g., Playwright) if desired:

- Dark mode toggle and `localStorage` persistence (Requirement 12.2–12.4)
- Toast auto-dismiss after 4 seconds (Requirement 11.6)
- Sidebar collapse on mobile viewports (Requirement 10.3–10.4)
- Responsive column hiding in transaction list on narrow viewports (Requirement 13.4)
- Minimum tap target sizes (Requirement 13.3)
