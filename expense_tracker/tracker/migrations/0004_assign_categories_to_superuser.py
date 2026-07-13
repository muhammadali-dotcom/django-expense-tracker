from django.db import migrations


def assign_categories_to_superuser(apps, schema_editor):
    Category = apps.get_model('tracker', 'Category')
    User = apps.get_model('auth', 'User')

    null_categories = Category.objects.filter(user_id__isnull=True)
    if not null_categories.exists():
        return

    superuser = User.objects.filter(is_superuser=True).order_by('id').first()
    if superuser:
        null_categories.update(user=superuser)
    else:
        null_categories.delete()


def reverse_assign_categories(apps, schema_editor):
    # Noop: reversing a data migration of this nature is not safely deterministic
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_add_userprofile'),
    ]

    operations = [
        migrations.RunPython(
            assign_categories_to_superuser,
            reverse_code=reverse_assign_categories,
        ),
    ]
