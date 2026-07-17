from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('', views.dashboard, name='dashboard'),
    path('register/', views.user_register, name='register'),
    # Backward-compat redirect: /add/ → /transactions/add/
    # Direct route for adding transaction (no redirect)
    path('add/', views.AddTransactionView.as_view(), name='add_transaction'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Transaction management (Requirements 4.1–4.10, 5.1, 11.1)
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),

    path('transactions/<int:pk>/edit/', views.EditTransactionView.as_view(), name='edit_transaction'),
    path('transactions/<int:pk>/delete/', views.DeleteTransactionView.as_view(), name='delete_transaction'),
    path('transactions/export/', views.export_csv, name='export_csv'),

    # Category management (Requirements 2.2, 2.3, 2.4, 2.5, 2.6)
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryEditView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Profile (Requirements 15.1–15.7, 11.5)
    path('profile/', views.profile, name='profile'),

    # Group Expense Management & Smart Settlement System
    path('groups/dashboard/', views.group_dashboard, name='group_dashboard'),
    path('groups/reports/', views.group_reports, name='group_reports'),
    path('groups/', views.ExpenseGroupListView.as_view(), name='group_list'),
    path('groups/add/', views.ExpenseGroupCreateView.as_view(), name='group_create'),
    path('groups/<int:pk>/', views.ExpenseGroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:pk>/edit/', views.ExpenseGroupEditView.as_view(), name='group_edit'),
    path('groups/<int:pk>/delete/', views.ExpenseGroupDeleteView.as_view(), name='group_delete'),
    path('groups/<int:pk>/members/add/', views.group_member_add, name='group_member_add'),
    path('groups/<int:pk>/members/<int:member_pk>/remove/', views.group_member_remove, name='group_member_remove'),
    path('groups/<int:pk>/expenses/add/', views.group_expense_create, name='group_expense_create'),
    path('groups/<int:pk>/settlements/mark-paid/', views.settlement_mark_paid, name='settlement_mark_paid'),
    path('groups/expenses/<int:pk>/edit/', views.group_expense_edit, name='group_expense_edit'),
    path('groups/expenses/<int:pk>/delete/', views.GroupExpenseDeleteView.as_view(), name='group_expense_delete'),

    # People (shared across groups)
    path('people/', views.PersonListView.as_view(), name='person_list'),
    path('people/add/', views.PersonCreateView.as_view(), name='person_create'),
    path('people/<int:pk>/edit/', views.PersonEditView.as_view(), name='person_edit'),
    path('people/<int:pk>/delete/', views.PersonDeleteView.as_view(), name='person_delete'),
]
