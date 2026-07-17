from django.contrib.auth.models import User
from django.test import TestCase

from tracker.forms import UserRegistrationForm
from tracker.models import Transaction


class UserRegistrationFormTests(TestCase):
    """Unit tests for UserRegistrationForm (Requirements 1.1, 1.2, 1.3, 1.5)."""

    # ---------- helpers ----------

    def _valid_data(self, username='testuser', email='test@example.com'):
        return {
            'username': username,
            'email': email,
            'password1': 'Str0ng!Pass99',
            'password2': 'Str0ng!Pass99',
        }

    # ---------- field presence (Requirement 1.1) ----------

    def test_form_has_email_field(self):
        form = UserRegistrationForm()
        self.assertIn('email', form.fields)

    def test_email_field_is_required(self):
        data = self._valid_data()
        data['email'] = ''
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_fields_match_expected(self):
        form = UserRegistrationForm()
        self.assertEqual(
            list(form.fields.keys()),
            ['username', 'email', 'password1', 'password2'],
        )

    # ---------- valid submission (Requirement 1.4) ----------

    def test_valid_form_is_valid(self):
        form = UserRegistrationForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_form_saves_user(self):
        form = UserRegistrationForm(data=self._valid_data())
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')

    # ---------- duplicate username (Requirement 1.2) ----------

    def test_duplicate_username_raises_friendly_error(self):
        User.objects.create_user(username='existinguser', password='irrelevant')
        data = self._valid_data(username='existinguser')
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn(
            'A user with that username already exists.',
            form.errors['username'],
        )

    def test_duplicate_username_does_not_create_user(self):
        User.objects.create_user(username='dupeuser', password='irrelevant')
        before_count = User.objects.count()
        data = self._valid_data(username='dupeuser')
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(User.objects.count(), before_count)

    # ---------- password mismatch (Requirement 1.3) ----------

    def test_mismatched_passwords_invalid(self):
        data = self._valid_data()
        data['password2'] = 'DifferentPass!99'
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    # ---------- required fields empty (Requirement 1.5) ----------

    def test_missing_username_invalid(self):
        data = self._valid_data()
        data['username'] = ''
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_missing_password1_invalid(self):
        data = self._valid_data()
        data['password1'] = ''
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_missing_password2_invalid(self):
        data = self._valid_data()
        data['password2'] = ''
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)


class DashboardFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='irrelevant')
        self.client.force_login(self.user)

    def test_invalid_dashboard_dates_do_not_crash(self):
        response = self.client.get('/?start_date=bad&end_date=2026-01-01')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid date format. Use YYYY-MM-DD.')

    def test_reversed_dashboard_dates_fall_back_with_error(self):
        response = self.client.get('/?start_date=2026-02-01&end_date=2026-01-01')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Start date cannot be after end date.')
        self.assertEqual(Transaction.objects.count(), 0)

    def test_health_check_returns_ok(self):
        self.client.logout()
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
