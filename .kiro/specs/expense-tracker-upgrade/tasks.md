# Implementation Plan: Expense Tracker Upgrade

## Overview

Incrementally extend the existing `tracker` Django app in-place. Each task builds on the previous, starting with data-model changes and migrations, then views/templates, then UI polish, and finishing with the test suite. All code is Python/Django + Bootstrap 5 + Chart.js + Vanilla JS.

## Tasks

- [x] 1. Data model changes and migrations
  - [x] 1.1 Update `Category` model and create migration
    - Add `user` ForeignKey (`settings.AUTH_USER_MODEL`, CASCADE, `related_name='categories'`) to `Category`
    - Add `budget` DecimalField (max_digits=10, decimal_places=2, null=True, blank=True) to `Category`
    - Add `Meta: unique_together = ('user', 'name')` to `Category`
    - Change `Transaction.amount` from `FloatField` to `DecimalField(max_digits=10, decimal_places=2)`
    - Add `Meta: ordering = ['-date', '-id']` to `Transaction`
    - Run `makemigrations` to generate schema migration
    - _Requirements: 2.1, 3.1, 5.4_

  - [x] 1.2 Add `UserProfile` model and auto-creation signal
    - Create `UserProfile` model with `OneToOneField(User)` and `currency` CharField (choices: USD/EUR/GBP/PKR/INR, default USD)
    - Add `post_save` signal on `User` to create `UserProfile` automatically
    - Include `CURRENCY_SYMBOLS` dict on the model
    - Run `makemigrations` for `UserProfile`
    - _Requirements: 15.6, 15.7_

  - [x] 1.3 Write data migration for existing global categories
    - Write a `RunPython` migration that assigns all existing `Category` rows without a `user` to the first superuser, or deletes them if no superuser exists
    - Run `migrate` to apply all pending migrations
    - _Requirements: 2.1_

- [x] 2. Install dependencies and configure settings
  - [x] 2.1 Install and configure `django-filter` and `pytest-django` + `hypothesis`
    - Add `django-filter` to `INSTALLED_APPS` as `'django_filters'`
    - Install `pytest-django` and `hypothesis[django]` (add to requirements or venv)
    - Create `pytest.ini` (or `setup.cfg`) pointing `DJANGO_SETTINGS_MODULE` to `expense_tracker.settings`
    - Add `django_filters` to `INSTALLED_APPS` in `settings.py`
    - _Requirements: 4.3–4.7_

- [x] 3. Forms layer
  - [x] 3.1 Create `UserRegistrationForm`
    - Extend Django's `UserCreationForm`; add `email` field
    - Override `clean_username` to produce a user-friendly duplicate-username error message
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [x] 3.2 Create `CategoryForm`
    - `ModelForm` for `Category` (fields: `name`, `budget`)
    - `clean` method validates positive budget and unique name per user (pass `user` in `__init__`)
    - _Requirements: 2.3, 3.1, 3.5_

  - [x] 3.3 Create `TransactionForm`
    - `ModelForm` for `Transaction` (fields: `category`, `amount`, `transaction_type`, `date`, `description`)
    - Filter `category` queryset to `user`-owned categories in `__init__`
    - `clean_amount` validates amount is positive decimal
    - _Requirements: 2.2, 5.2, 5.4_

  - [x] 3.4 Create `TransactionFilterSet` using `django-filter`
    - Fields: `date__gte`, `date__lte`, `category`, `transaction_type`, `description__icontains`
    - Scope `category` choices to `request.user` via `__init__`
    - _Requirements: 4.3, 4.4, 4.5, 4.6, 4.7_

  - [x] 3.5 Create `UserProfileForm`
    - `ModelForm` for `UserProfile` with `currency` field only
    - _Requirements: 15.6, 15.7_

- [x] 4. Checkpoint — ensure migrations apply cleanly and forms import without errors
  - Run `python manage.py migrate` and verify no errors
  - Run `python manage.py check` to verify settings and app config
  - Ask the user if any questions arise before proceeding.

- [x] 5. Authentication views
  - [x] 5.1 Implement `user_register` view and `register.html` template
    - FBV at `/register/`: render `UserRegistrationForm`; on valid POST create user, log them in, redirect to dashboard
    - Template extends `base.html`; shows field-level errors inline with Bootstrap `is-invalid`
    - Add link to `/register/` on the existing `login.html`
    - Wire URL `path('register/', views.user_register, name='register')` in `tracker/urls.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]* 5.2 Write property test for user registration (Properties 1 & 2)
    - **Property 1: User Registration Rejects Invalid Inputs**
    - **Property 2: Successful Registration Creates and Authenticates User**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5**

- [ ] 6. User-owned category CRUD views
  - [x] 6.1 Implement `category_list`, `category_create`, `category_edit`, `category_delete` views
    - `category_list`: CBV `ListView` filtered to `user=request.user`; includes budget-status computation (`get_budget_status` helper in `tracker/utils.py`)
    - `category_create`: CBV `CreateView`; pass `user` to `CategoryForm`; set `instance.user = request.user` in `form_valid`
    - `category_edit`: CBV `UpdateView`; `get_queryset` filters by `user`; pass `user` to form
    - `category_delete`: CBV `DeleteView`; `get_queryset` filters by `user`; raises 403 if object not in queryset
    - Add success messages (Django messages framework) for create, rename, delete actions
    - Wire URLs: `/categories/`, `/categories/add/`, `/categories/<pk>/edit/`, `/categories/<pk>/delete/`
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 11.4_

  - [-] 6.2 Create `category_list.html` template
    - Extends `base.html`; lists categories with name, budget, current-month spending, and budget-status badge
    - Show 80% warning badge and over-budget badge based on `pct` from context
    - Include Create / Rename / Delete buttons; Delete shows an inline confirmation modal
    - _Requirements: 2.4, 3.2, 3.3, 3.4_

  - [ ]* 6.3 Write property tests for category ownership (Properties 3, 4, 5)
    - **Property 3: Category Isolation Between Users**
    - **Property 4: Category Ownership Enforcement (403)**
    - **Property 5: Category Deletion Nullifies Transaction References**
    - **Validates: Requirements 2.2, 2.5, 2.6**

  - [ ]* 6.4 Write property test for budget threshold indicators (Property 6)
    - **Property 6: Budget Threshold Indicators**
    - **Validates: Requirements 3.3, 3.4**

- [ ] 7. Transaction List, Edit, Delete, and CSV Export views
  - [-] 7.1 Implement `transaction_list` view using `FilterView`
    - CBV `FilterView` with `filterset_class=TransactionFilterSet`, `paginate_by=20`
    - Scope queryset to `user=request.user`
    - Pass `currency_symbol` from `UserProfile` in `get_context_data`
    - Wire URL `/transactions/`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_

  - [ ] 7.2 Create `transaction_list.html` template
    - Extends `base.html`; renders filter form, table rows color-coded by type, pagination controls, CSV export button
    - Show empty-state message + CTA when queryset is empty
    - Hide description and category columns with `d-none d-sm-table-cell` on narrow viewports
    - _Requirements: 4.1, 4.2, 4.8, 4.9, 4.10, 13.4_

  - [-] 7.3 Implement `add_transaction` CBV `CreateView` at `/transactions/add/`
    - Replace existing FBV; use `TransactionForm`; set `instance.user = request.user` in `form_valid`
    - Add success message; redirect to transaction list
    - Update URL wiring; keep old `/add/` as redirect for backward compatibility
    - _Requirements: 5.1, 11.1_

  - [ ] 7.4 Implement `edit_transaction` CBV `UpdateView` at `/transactions/<pk>/edit/`
    - `get_queryset` filters by `user`; use `TransactionForm`
    - Pre-populates form with existing values; adds success message on save
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7, 11.2_

  - [ ] 7.5 Create `edit_transaction.html` template
    - Extends `base.html`; renders pre-populated `TransactionForm` with inline validation errors
    - _Requirements: 5.2, 5.3, 5.4_

  - [ ] 7.6 Implement `delete_transaction` CBV `DeleteView` at `/transactions/<pk>/delete/`
    - `get_queryset` filters by `user`; adds success message in `delete` method
    - Template shows confirmation prompt before deletion
    - _Requirements: 5.1, 5.5, 5.6, 5.7, 11.3_

  - [ ] 7.7 Implement `export_csv` FBV at `/transactions/export/`
    - Accepts same filter parameters as `transaction_list`; reuses `TransactionFilterSet` to scope queryset
    - Streams `HttpResponse` with `Content-Type: text/csv`
    - Header row: Date, Type, Category, Amount, Description
    - Filename: `transactions_YYYY-MM-DD.csv` using today's date
    - Returns valid CSV with header-only when no transactions match filters
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ]* 7.8 Write property tests for transaction filters and pagination (Properties 7, 8, 9)
    - **Property 7: Transaction Filter Correctness**
    - **Property 8: Pagination Invariant**
    - **Property 9: Transaction List Ordering**
    - **Validates: Requirements 4.1, 4.2, 4.3–4.7**

  - [ ]* 7.9 Write property tests for transaction edit/delete ownership (Properties 10–13)
    - **Property 10: Transaction Edit Pre-Population and Save**
    - **Property 11: Transaction Edit Rejects Non-Positive Amounts**
    - **Property 12: Transaction Deletion Removes Record**
    - **Property 13: Transaction Ownership Enforcement (403)**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.6, 5.7**

  - [ ]* 7.10 Write property test for CSV output correctness (Property 17)
    - **Property 17: CSV Output Correctness and User Isolation**
    - **Validates: Requirements 14.2, 14.3, 14.5**

- [ ] 8. Checkpoint — ensure transaction views return correct status codes and data
  - Run `pytest tracker/tests/test_views_transactions.py` (or equivalent) with no failures
  - Ask the user if any questions arise before proceeding.

- [ ] 9. Dashboard enhancements
  - [x] 9.1 Create `tracker/utils.py` with chart and budget helper functions
    - Implement `get_budget_status(user)` — returns list of `{category, spent, pct}` for categories with a budget
    - Implement `get_monthly_trend(user, start_date, end_date)` — returns `[{month, income, expense}]` with zero-fill for empty months
    - Implement `get_category_trend(user, start_date, end_date)` — returns `{labels, datasets}` for per-category monthly expense, filtered to categories with at least one expense
    - _Requirements: 3.2, 8.1, 8.4, 9.1, 9.4_

  - [ ] 9.2 Extend `dashboard` FBV with date-range filter, net balance, and chart data
    - Accept GET params `start_date` and `end_date`; default to current calendar month if absent
    - Validate that `start_date <= end_date`; add error to context if invalid
    - Compute income total, expense total, net balance for the filtered range
    - Call `get_monthly_trend` and `get_category_trend` helpers; pass results as JSON-safe context vars
    - Pass `currency_symbol` from `UserProfile`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 9.1, 9.2_

  - [ ] 9.3 Update `dashboard.html` template
    - Add Net Balance card with conditional color classes (`text-success`, `text-danger`, `text-secondary`)
    - Add date-range filter form (start/end date inputs + submit button)
    - Replace existing pie chart with: (a) monthly bar chart (Chart.js, income vs expense, 12 months) and (b) category spending trend line chart (Chart.js, 6 months, one line per category)
    - Render budget-warning badges for each category with a budget
    - _Requirements: 3.2, 3.3, 3.4, 6.1–6.5, 7.1–7.4, 8.1–8.4, 9.1–9.4_

  - [ ]* 9.4 Write property tests for dashboard computations (Properties 14, 15, 16)
    - **Property 14: Net Balance Computation Correctness**
    - **Property 15: Date-Range Filter Consistency**
    - **Property 16: Chart Zero-Fill for Empty Periods**
    - **Validates: Requirements 6.1–6.5, 7.4, 8.2, 8.4, 9.2, 9.4**

- [ ] 10. User Profile page
  - [ ] 10.1 Implement `profile` FBV at `/profile/`
    - Handle two forms on same page: Django built-in `PasswordChangeForm` and `UserProfileForm`
    - Call `update_session_auth_hash` after password change to keep user logged in
    - Add success messages for password change and currency preference save
    - Wire URL `path('profile/', views.profile, name='profile')`
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 11.5_

  - [ ] 10.2 Create `profile.html` template
    - Extends `base.html`; two Bootstrap cards side-by-side: password form and currency preference form
    - Render inline errors with `is-invalid` / `invalid-feedback` classes
    - _Requirements: 15.1, 15.2, 15.6_

  - [ ] 10.3 Create `currency_tags` template tag and context processor
    - Create `tracker/templatetags/currency_tags.py` with `currency_format` filter
    - Create a context processor that injects `currency_symbol` into all template contexts
    - Register the context processor in `settings.py`
    - Apply `currency_format` filter to all monetary amounts in dashboard, transaction list, and categories templates
    - _Requirements: 15.7_

  - [ ]* 10.4 Write property tests for profile page (Properties 18 & 19)
    - **Property 18: Password Change Form Correctness**
    - **Property 19: Currency Symbol Consistency**
    - **Validates: Requirements 15.3, 15.4, 15.5, 15.7**

- [ ] 11. Sidebar navigation and base.html refactor
  - [ ] 11.1 Refactor `base.html` with sidebar layout and toast container
    - Replace top-navbar Add-Transaction and Logout buttons with a sidebar (`_sidebar.html` partial)
    - Keep top bar only for brand name and dark-mode toggle button
    - Add Bootstrap toast container that iterates Django messages and renders each as a Bootstrap toast
    - Wire dark-mode toggle: add `data-bs-theme` attribute to `<html>`; JS reads/writes `localStorage` key `theme`
    - `_sidebar.html`: links to Dashboard, Transaction List, Add Transaction, Categories, Profile, Logout; mark active link using `request.resolver_match.url_name`
    - _Requirements: 10.1, 10.2, 10.5, 11.1–11.7, 12.1_

  - [ ] 11.2 Implement mobile sidebar collapse
    - Wrap sidebar in Bootstrap off-canvas component for viewports < 768 px
    - Add hamburger toggle button in topbar that shows on small screens
    - Ensure main content area adjusts margin when sidebar is visible on desktop
    - _Requirements: 10.3, 10.4, 13.1, 13.2, 13.3_

  - [ ]* 11.3 Write property test for toast message presence (Property 20)
    - **Property 20: Success Actions Produce Toast Messages**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**

- [ ] 12. Mobile-responsive layout polish
  - [ ] 12.1 Apply Bootstrap 5 responsive grid to summary cards and transaction table
    - Wrap dashboard summary cards in `col-12 col-md-6 col-lg-3` columns so they stack on mobile
    - Add `d-none d-sm-table-cell` to description and category `<th>` and `<td>` in transaction list
    - Ensure all form inputs and buttons carry `min-height: 44px; min-width: 44px` via a utility CSS rule in `base.html`
    - Verify no horizontal scrollbar appears at 320 px viewport by using `overflow-x: hidden` on `<body>` where needed
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [ ] 13. Checkpoint — manual smoke test of all views
  - Verify sidebar renders and collapses on mobile
  - Verify toasts appear after create/update/delete actions and auto-dismiss after 4 s
  - Verify dark mode toggle persists across page reloads
  - Ask the user if any questions arise before proceeding.

- [ ] 14. Tests suite wiring and remaining unit tests
  - [ ] 14.1 Create `tracker/tests/` package and unit test files
    - Create `tracker/tests/__init__.py`
    - Create `test_models.py`: test `Category.__str__`, `Transaction.__str__`, `Meta.ordering`, `UserProfile` auto-creation signal
    - Create `test_views_auth.py`: GET `/register/` returns 200 unauthenticated; POST with invalid data returns form errors; POST with valid data creates user and redirects
    - Create `test_views_categories.py`: create/rename/delete happy paths; duplicate name error; 403 on cross-user access; transaction null-on-delete
    - Create `test_views_transactions.py`: add/edit/delete happy paths; 403 cross-user; invalid amount error; pagination returns ≤ 20 rows per page; filter and search
    - Create `test_views_dashboard.py`: default date range is current month; invalid date range does not apply filter
    - Create `test_views_profile.py`: password change happy path; wrong current password; currency preference save
    - Create `test_csv_export.py`: columns match spec; empty result produces header-only CSV; filename format
    - Create `test_utils.py`: `get_monthly_trend` zero-fills empty months; `get_category_trend` excludes categories with no expenses
    - _Requirements: all_

  - [ ] 14.2 Create `test_properties.py` with all Hypothesis property-based tests
    - Import all properties (1–20) and implement as `@given`-decorated test functions
    - Use `@pytest.mark.django_db` for database tests
    - Each test function references its property number in a comment: `# Property N: <text>`
    - _Requirements: all (via design Correctness Properties 1–20)_

- [ ] 15. Final checkpoint — full test suite must pass
  - Run `pytest --tb=short` and confirm zero failures
  - Run `python manage.py check` for no deployment warnings
  - Ask the user if any questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP delivery.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation and provide natural break points.
- Property tests validate universal correctness guarantees; unit tests validate specific examples and edge cases.
- All client-side behaviors (dark-mode persistence, toast auto-dismiss, sidebar collapse animation) are verified manually or with browser automation — they are not covered by server-side tests.
- The old `/add/` URL should be kept as a redirect to `/transactions/add/` to avoid breaking bookmarks.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["1.3", "2.1"] },
    { "id": 3, "tasks": ["3.1", "3.2", "3.3", "3.4", "3.5"] },
    { "id": 4, "tasks": ["5.1", "6.1", "9.1"] },
    { "id": 5, "tasks": ["5.2", "6.2", "6.3", "6.4", "7.1", "7.3", "10.1"] },
    { "id": 6, "tasks": ["7.2", "7.4", "7.6", "7.7", "9.2", "10.2", "10.3"] },
    { "id": 7, "tasks": ["7.5", "7.8", "7.9", "7.10", "9.3", "10.4"] },
    { "id": 8, "tasks": ["9.4", "11.1"] },
    { "id": 9, "tasks": ["11.2", "11.3", "12.1"] },
    { "id": 10, "tasks": ["14.1"] },
    { "id": 11, "tasks": ["14.2"] }
  ]
}
```
