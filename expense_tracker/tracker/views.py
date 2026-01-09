from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum
from .models import Transaction, Category


@login_required
def dashboard(request):
    transactions = Transaction.objects.filter(user=request.user)

    income = transactions.filter(
        transaction_type='Income'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    expense = transactions.filter(
        transaction_type='Expense'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    categories = Category.objects.all()

    labels = []
    data = []

    for category in categories:
        total = transactions.filter(
            category=category,
            transaction_type='Expense'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        labels.append(category.name)
        data.append(float(total))

    context = {
        'income': income,
        'expense': expense,
        'labels': labels,
        'data': data,
    }

    return render(request, 'dashboard.html', context)


@login_required
def add_transaction(request):
    if request.method == 'POST':
        Transaction.objects.create(
            user=request.user,
            category=Category.objects.get(id=request.POST['category']),
            amount=request.POST['amount'],
            transaction_type=request.POST['type'],
            date=request.POST['date'],
            description=request.POST.get('description', '')
        )
        return redirect('dashboard')

    categories = Category.objects.all()
    return render(request, 'add_transaction.html', {'categories': categories})


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
