import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0006_alter_category_id_alter_transaction_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='people', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ExpenseGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expense_groups', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GroupMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_date', models.DateField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_members', to='tracker.expensegroup')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='tracker.person')),
            ],
            options={
                'unique_together': {('group', 'person')},
            },
        ),
        migrations.AddField(
            model_name='expensegroup',
            name='members',
            field=models.ManyToManyField(related_name='groups', through='tracker.GroupMember', to='tracker.person'),
        ),
        migrations.CreateModel(
            name='GroupExpense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('description', models.TextField(blank=True)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('category', models.CharField(choices=[('Food', 'Food'), ('Travel', 'Travel'), ('Shopping', 'Shopping'), ('Utilities', 'Utilities'), ('Entertainment', 'Entertainment'), ('Other', 'Other')], default='Other', max_length=20)),
                ('expense_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expenses', to='tracker.expensegroup')),
                ('paid_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='paid_expenses', to='tracker.person')),
            ],
            options={
                'ordering': ['-expense_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='ExpenseSplit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('share_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('expense', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='splits', to='tracker.groupexpense')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expense_splits', to='tracker.person')),
            ],
            options={
                'unique_together': {('expense', 'person')},
            },
        ),
        migrations.CreateModel(
            name='Settlement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid')], default='paid', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='settlements', to='tracker.expensegroup')),
                ('from_person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='settlements_owed', to='tracker.person')),
                ('to_person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='settlements_receivable', to='tracker.person')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
