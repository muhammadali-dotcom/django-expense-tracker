from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.user_register, name='register'),
    # Backward-compat redirect: /add/ → /transactions/add/
    path('add/', RedirectView.as_view(url='/transactions/add/', permanent=True)),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    # Transaction management (Requirements 4.1–4.10, 5.1, 11.1)
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/add/', views.AddTransactionView.as_view(), name='add_transaction'),
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
]
