from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AdminAccessTests(TestCase):
    def setUp(self):
        self.app_user = User.objects.create_user("mario", password="secret")
        self.staff = User.objects.create_user(
            "alessio", password="secret", is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            "simon", password="secret"
        )

    def test_app_user_login_goes_to_app_without_staff(self):
        self.assertFalse(self.app_user.is_staff)
        response = self.client.post(
            reverse("admin:login"),
            {"username": "mario", "password": "secret", "next": "/admin/"},
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_app_user_cannot_open_admin(self):
        self.client.force_login(self.app_user)
        response = self.client.get("/admin/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_staff_login_goes_to_admin(self):
        response = self.client.post(
            reverse("admin:login"),
            {"username": "alessio", "password": "secret", "next": "/"},
        )
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)

    def test_staff_can_open_admin(self):
        self.client.force_login(self.staff)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_open_admin(self):
        self.client.force_login(self.superuser)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
