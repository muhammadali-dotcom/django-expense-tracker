# Requirements Document

## Introduction

This document describes the requirements for a comprehensive upgrade of the existing Django-based expense tracker web application. The current app provides basic transaction entry and a dashboard with a pie chart. This upgrade adds full transaction management (list, edit, delete, search, export), user self-registration, per-user category ownership, budget limits with warnings, enriched analytics charts, a sidebar layout, dark mode, toast notifications, and a user profile page. All new features must integrate cleanly with the existing Bootstrap 5 UI and Django authentication system.

## Glossary

- **App**: The Django expense tracker web application being upgraded.
- **User**: An authenticated person who has registered or been granted access to the App.
- **Transaction**: A financial record belonging to a User with an amount, type (Income or Expense), category, date, and optional description.
- **Category**: A user-owned label used to group Transactions; each Category belongs to exactly one User.
- **Budget**: An optional monthly spending limit set by a User for a specific Category.
- **Dashboard**: The main summary page showing totals, net balance, charts, and date-range filters.
- **Transaction_List**: The paginated, filterable, searchable view of all Transactions for the logged-in User.
- **Registration_Form**: The page and form that allows a new visitor to create a User account.
- **Profile_Page**: A page where a User can update their password and currency preference.
- **Sidebar**: The persistent left-side navigation panel that replaces the top-navbar-only layout.
- **Toast**: A transient on-screen notification displayed after a user action completes.
- **Dark_Mode**: An alternative color scheme that uses dark backgrounds and light text throughout the App.
- **CSV_Export**: A downloadable comma-separated-values file containing a User's filtered Transactions.
- **Net_Balance**: The computed value of total Income minus total Expense for a given period.
- **Budget_Warning**: A visual indicator shown when a Category's spending reaches or exceeds its Budget limit.
- **Pagination**: The division of a long list into discrete pages, each containing a fixed number of items.

---

## Requirements

### Requirement 1: User Registration

**User Story:** As a visitor, I want to register a new account, so that I can start tracking my own expenses without requiring admin intervention.

#### Acceptance Criteria

1. THE Registration_Form SHALL include fields for username, email, password, and password confirmation.
2. WHEN a visitor submits the Registration_Form with a username that already exists, THE App SHALL display an error message identifying the conflict.
3. WHEN a visitor submits the Registration_Form with mismatched password and password confirmation values, THE App SHALL display an error message stating the passwords do not match.
4. WHEN a visitor submits the Registration_Form with all valid values, THE App SHALL create a new User account, log that User in, and redirect them to the Dashboard.
5. IF the Registration_Form is submitted with an empty required field, THEN THE App SHALL display a field-level validation error and not create an account.
6. THE Registration_Form SHALL be accessible at the `/register/` URL without authentication.
7. THE Login page SHALL include a link to the Registration_Form.

---

### Requirement 2: User-Owned Categories

**User Story:** As a User, I want to create and manage my own categories, so that my category list is personal and not shared with other users.

#### Acceptance Criteria

1. THE App SHALL associate each Category with exactly one User via a foreign key.
2. WHEN the App displays a Category selector, THE App SHALL show only the Categories belonging to the currently authenticated User.
3. WHEN a User creates a Category with a name that already exists in that User's Category list, THE App SHALL display a duplicate-name error and not create a second Category.
4. THE App SHALL provide a Category management page where a User can create, rename, and delete their own Categories.
5. WHEN a User deletes a Category that is referenced by one or more Transactions, THE App SHALL set the category field of those Transactions to null rather than deleting the Transactions.
6. IF a request is made to modify or delete a Category that does not belong to the authenticated User, THEN THE App SHALL return a 403 Forbidden response.

---

### Requirement 3: Budget Limits per Category

**User Story:** As a User, I want to set a monthly budget limit on a category, so that I receive a warning when I am approaching or exceeding my spending limit.

#### Acceptance Criteria

1. THE App SHALL allow a User to set an optional positive decimal budget amount on any Category they own.
2. WHEN the Dashboard or Transaction_List is rendered, THE App SHALL calculate the current calendar-month total expense for each Category that has a Budget.
3. WHEN a Category's current-month expense total reaches or exceeds 80% of its Budget amount, THE App SHALL display a Budget_Warning indicator next to that Category.
4. WHEN a Category's current-month expense total reaches or exceeds 100% of its Budget amount, THE App SHALL display a distinct over-budget indicator differentiating it from the 80% warning.
5. IF a User sets a budget amount that is zero or negative, THEN THE App SHALL display a validation error and not save the Budget.

---

### Requirement 4: Transaction List with Pagination, Filters, and Search

**User Story:** As a User, I want to browse, filter, and search my transactions in a list view, so that I can quickly find and review specific financial records.

#### Acceptance Criteria

1. THE Transaction_List SHALL display the User's Transactions in reverse-chronological order by default.
2. THE Transaction_List SHALL display 20 Transactions per page and provide Pagination controls to navigate between pages.
3. WHEN a User applies a date-range filter (start date and/or end date), THE Transaction_List SHALL display only Transactions whose date falls within the specified range.
4. WHEN a User selects a Category filter, THE Transaction_List SHALL display only Transactions belonging to that Category.
5. WHEN a User selects a transaction type filter (Income or Expense), THE Transaction_List SHALL display only Transactions of that type.
6. WHEN a User enters a search term in the description search field, THE Transaction_List SHALL display only Transactions whose description contains the search term (case-insensitive).
7. WHEN multiple filters are active simultaneously, THE Transaction_List SHALL apply all active filters as AND conditions.
8. WHEN the Transaction_List contains no Transactions matching the active filters, THE App SHALL display an empty-state message with a call-to-action button to add a new Transaction.
9. WHEN the User's Transaction list is completely empty (no Transactions exist), THE App SHALL display an empty-state message with a call-to-action button to add a first Transaction.
10. THE Transaction_List SHALL color-code each row: Income rows SHALL use a green visual indicator and Expense rows SHALL use a red visual indicator.

---

### Requirement 5: Edit and Delete Transactions

**User Story:** As a User, I want to edit or delete an existing transaction, so that I can correct mistakes or remove records that are no longer relevant.

#### Acceptance Criteria

1. THE Transaction_List SHALL provide an Edit action and a Delete action for each Transaction row.
2. WHEN a User selects the Edit action on a Transaction, THE App SHALL display a pre-populated form containing the current values of that Transaction.
3. WHEN a User submits the Edit form with valid values, THE App SHALL update the Transaction and display a Toast confirming the update.
4. WHEN a User submits the Edit form with an invalid amount (non-positive or non-numeric), THE App SHALL display a validation error and not save the Transaction.
5. WHEN a User selects the Delete action on a Transaction, THE App SHALL display a confirmation prompt before deleting.
6. WHEN a User confirms deletion, THE App SHALL delete the Transaction and display a Toast confirming the deletion.
7. IF a request is made to edit or delete a Transaction that does not belong to the authenticated User, THEN THE App SHALL return a 403 Forbidden response.

---

### Requirement 6: Net Balance Card on Dashboard

**User Story:** As a User, I want to see my net balance on the dashboard, so that I can instantly understand my overall financial position.

#### Acceptance Criteria

1. THE Dashboard SHALL display a Net Balance card showing the value of total Income minus total Expense for the selected date range.
2. WHEN the Net_Balance is positive, THE Dashboard SHALL display the Net Balance card value in green.
3. WHEN the Net_Balance is zero, THE Dashboard SHALL display the Net Balance card value in a neutral color.
4. WHEN the Net_Balance is negative, THE Dashboard SHALL display the Net Balance card value in red.
5. WHEN a date-range filter is applied on the Dashboard, THE App SHALL recalculate the Net_Balance, total income, and total expense to reflect only Transactions within that range.

---

### Requirement 7: Dashboard Date-Range Filter

**User Story:** As a User, I want to filter the dashboard by a custom date range, so that I can analyze my finances for a specific period.

#### Acceptance Criteria

1. THE Dashboard SHALL provide start-date and end-date input fields for filtering all dashboard metrics and charts.
2. WHEN a User submits the date-range filter with a start date after the end date, THE App SHALL display a validation error and not apply the filter.
3. WHEN no date-range filter is active, THE Dashboard SHALL default to displaying data for the current calendar month.
4. WHEN a date-range filter is applied, THE Dashboard SHALL update all summary cards and all charts to reflect only data within the specified range.

---

### Requirement 8: Monthly Bar Chart (Income vs Expense Trend)

**User Story:** As a User, I want to see a monthly bar chart comparing income and expenses, so that I can identify financial trends over time.

#### Acceptance Criteria

1. THE Dashboard SHALL display a bar chart showing monthly totals for both Income and Expense for the 12 calendar months preceding the current month (inclusive).
2. WHEN a date-range filter is applied, THE Dashboard SHALL adjust the bar chart to cover only the months that fall within that range.
3. THE bar chart SHALL use a distinct color for Income bars and a distinct color for Expense bars, with a legend identifying each.
4. WHEN a month has no Transactions, THE bar chart SHALL render that month's bar with a value of zero.

---

### Requirement 9: Category Spending Trend Chart

**User Story:** As a User, I want to see how spending per category changes over recent months, so that I can spot categories where I am overspending.

#### Acceptance Criteria

1. THE Dashboard SHALL display a line chart showing monthly Expense totals per Category for the 6 calendar months preceding the current month (inclusive).
2. WHEN a date-range filter is applied, THE Dashboard SHALL adjust the category trend line chart to cover only the months within that range.
3. THE line chart SHALL render one line per Category that has at least one Expense Transaction in the displayed period.
4. WHEN a Category has no Expense Transactions in a given month, THE line chart SHALL plot a zero value for that month for that Category.

---

### Requirement 10: Sidebar Navigation

**User Story:** As a User, I want a sidebar navigation panel, so that I can easily move between sections of the App on both desktop and mobile.

#### Acceptance Criteria

1. THE Sidebar SHALL be present on all authenticated pages and contain links to: Dashboard, Transaction List, Add Transaction, Categories, Profile, and Logout.
2. THE Sidebar SHALL highlight the currently active navigation link.
3. WHEN the viewport width is below 768 pixels, THE Sidebar SHALL collapse into a toggleable off-canvas or hamburger-menu panel.
4. WHEN the Sidebar is collapsed on a small viewport, THE App SHALL display a toggle button that opens and closes the Sidebar.
5. THE App SHALL remove the existing top-navbar Add-Transaction and Logout buttons when the Sidebar is present, retaining the top bar only for the App name/brand and the dark-mode toggle.

---

### Requirement 11: Toast Notifications

**User Story:** As a User, I want to see brief on-screen notifications after I perform actions, so that I receive immediate feedback confirming what happened.

#### Acceptance Criteria

1. THE App SHALL display a Toast after a Transaction is successfully created.
2. THE App SHALL display a Toast after a Transaction is successfully updated.
3. THE App SHALL display a Toast after a Transaction is successfully deleted.
4. THE App SHALL display a Toast after a Category is successfully created, renamed, or deleted.
5. THE App SHALL display a Toast after a User successfully updates their password or currency preference.
6. THE Toast SHALL be auto-dismissed after 4 seconds without requiring user interaction.
7. THE Toast SHALL include a close button allowing the User to dismiss it manually before the 4-second timeout.

---

### Requirement 12: Dark Mode Toggle

**User Story:** As a User, I want to switch between light and dark mode, so that I can use the App comfortably in different lighting conditions.

#### Acceptance Criteria

1. THE App SHALL provide a dark-mode toggle control visible in the top navigation bar on all pages.
2. WHEN a User activates dark mode, THE App SHALL apply a dark color scheme to all page elements including the Sidebar, cards, forms, and charts.
3. WHEN a User deactivates dark mode, THE App SHALL restore the light color scheme.
4. THE App SHALL persist the User's dark-mode preference in the browser's localStorage so that the preference is retained across page loads and sessions on the same device.
5. WHILE dark mode is active, THE App SHALL update chart colors to maintain legibility against dark backgrounds.

---

### Requirement 13: Mobile-Responsive Layout

**User Story:** As a User, I want the App to be usable on a mobile device, so that I can manage my finances on the go.

#### Acceptance Criteria

1. THE App SHALL render all pages without horizontal scrolling on viewports as narrow as 320 pixels.
2. THE App SHALL use Bootstrap 5 responsive grid classes so that summary cards stack vertically on viewports below 768 pixels wide.
3. THE App SHALL ensure all form inputs and buttons meet a minimum tap target size of 44 × 44 pixels on touch viewports.
4. THE Transaction_List SHALL display a condensed column set (date, amount, type) on viewports below 576 pixels, hiding the description and category columns.

---

### Requirement 14: CSV Export

**User Story:** As a User, I want to export my transactions as a CSV file, so that I can analyze my data in a spreadsheet application.

#### Acceptance Criteria

1. THE Transaction_List SHALL provide a CSV_Export button that downloads the User's currently filtered set of Transactions.
2. WHEN the CSV_Export is triggered, THE App SHALL generate a CSV file with columns: Date, Type, Category, Amount, Description.
3. THE CSV file SHALL include only Transactions belonging to the authenticated User.
4. WHEN no Transactions match the active filters, THE App SHALL still produce a valid CSV file containing only the header row.
5. THE CSV file name SHALL follow the pattern `transactions_YYYY-MM-DD.csv` where the date is the export date.

---

### Requirement 15: User Profile Page

**User Story:** As a User, I want a profile page where I can change my password and set my currency preference, so that I can personalize my account.

#### Acceptance Criteria

1. THE Profile_Page SHALL be accessible to authenticated Users at the `/profile/` URL.
2. THE Profile_Page SHALL provide a password-change form with fields for current password, new password, and new password confirmation.
3. WHEN a User submits the password-change form with an incorrect current password, THE App SHALL display an error and not update the password.
4. WHEN a User submits the password-change form with a new password and confirmation that do not match, THE App SHALL display an error and not update the password.
5. WHEN a User successfully changes their password, THE App SHALL update the password, keep the User logged in, and display a Toast confirming the change.
6. THE Profile_Page SHALL provide a currency preference selector with at least the following options: USD, EUR, GBP, PKR, INR.
7. WHEN a User saves a currency preference, THE App SHALL store the preference and display all monetary amounts using the selected currency symbol throughout the App.
