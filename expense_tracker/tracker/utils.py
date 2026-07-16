"""
Utility helpers for chart data and budget status in the tracker app.

Functions
---------
get_budget_status(user)
    Returns a list of {category, spent, pct} for the current calendar month,
    one entry per category that has a budget set.

get_monthly_trend(user, start_date, end_date)
    Returns a list of {month, income, expense} for every calendar month in
    [start_date, end_date], zero-filled for months with no transactions.

get_category_trend(user, start_date, end_date)
    Returns {labels, datasets} for a per-category monthly expense line chart,
    including only categories that have at least one expense in the period.
    All monetary values are converted to float (JSON-serialisable).
"""

from datetime import date

from django.db.models import Sum
from django.utils import timezone

from .models import Category, Transaction


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _month_range(start_date: date, end_date: date):
    """
    Yield (year, month) tuples for every calendar month that overlaps the
    closed interval [start_date, end_date], in chronological order.
    """
    year, month = start_date.year, start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        yield year, month
        month += 1
        if month > 12:
            month = 1
            year += 1


def _month_label(year: int, month: int) -> str:
    """Return 'YYYY-MM' string for a given year/month pair."""
    return f"{year:04d}-{month:02d}"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_budget_status(user):
    """
    Return a list of budget-status dicts for the current calendar month.

    Each dict contains:
        category  – Category instance
        spent     – float, total expense amount for this month
        pct       – float, percentage of budget spent (0–100+)

    Only categories that have a non-null budget are included.
    """
    now = timezone.now().date()
    categories = Category.objects.filter(user=user).exclude(budget__isnull=True)

    results = []
    for cat in categories:
        spent = (
            Transaction.objects.filter(
                user=user,
                category=cat,
                transaction_type="Expense",
                date__year=now.year,
                date__month=now.month,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        spent = float(spent)
        pct = (spent / float(cat.budget) * 100) if cat.budget else 0.0
        results.append({"category": cat, "spent": spent, "pct": pct})

    return results


def get_monthly_trend(user, start_date: date, end_date: date):
    """
    Return a list of monthly income/expense totals for [start_date, end_date].

    Each entry is a dict:
        month    – 'YYYY-MM'
        income   – float
        expense  – float

    Months with no transactions are zero-filled.
    """
    results = []

    for year, month in _month_range(start_date, end_date):
        # Determine the actual first/last day to query within the month,
        # clamped to the caller's date range.
        import calendar as _cal

        last_day = _cal.monthrange(year, month)[1]
        period_start = max(start_date, date(year, month, 1))
        period_end = min(end_date, date(year, month, last_day))

        base_qs = Transaction.objects.filter(
            user=user,
            date__gte=period_start,
            date__lte=period_end,
        )

        income = round(
            float(
                base_qs.filter(transaction_type="Income")
                .aggregate(total=Sum("amount"))["total"]
                or 0
            )
        )
        expense = round(
            float(
                base_qs.filter(transaction_type="Expense")
                .aggregate(total=Sum("amount"))["total"]
                or 0
            )
        )

        results.append(
            {
                "month": _month_label(year, month),
                "income": income,
                "expense": expense,
            }
        )

    return results


def get_category_trend(user, start_date: date, end_date: date):
    """
    Return chart data for a per-category monthly expense line chart.

    The return value is a dict:
        labels    – list of 'YYYY-MM' strings (one per month in the range)
        datasets  – list of dicts, one per category:
                        label  – category name (str)
                        data   – list of floats, one per label (zero-filled)

    Only categories with at least one Expense transaction in the period
    are included. All values are floats (JSON-serialisable).
    """
    import calendar as _cal

    months = list(_month_range(start_date, end_date))
    labels = [_month_label(y, m) for y, m in months]

    # Find categories that have at least one expense in the period.
    active_category_ids = (
        Transaction.objects.filter(
            user=user,
            transaction_type="Expense",
            date__gte=start_date,
            date__lte=end_date,
        )
        .values_list("category_id", flat=True)
        .distinct()
    )

    # Exclude null (uncategorised) entries.
    active_categories = Category.objects.filter(
        id__in=active_category_ids
    ).exclude(id__isnull=True)

    datasets = []
    for cat in active_categories:
        data = []
        for year, month in months:
            last_day = _cal.monthrange(year, month)[1]
            period_start = max(start_date, date(year, month, 1))
            period_end = min(end_date, date(year, month, last_day))

            total = round(
                float(
                    Transaction.objects.filter(
                        user=user,
                        category=cat,
                        transaction_type="Expense",
                        date__gte=period_start,
                        date__lte=period_end,
                    ).aggregate(total=Sum("amount"))["total"]
                    or 0
                )
            )
            data.append(total)

        datasets.append({"label": cat.name, "data": data})

    return {"labels": labels, "datasets": datasets}
