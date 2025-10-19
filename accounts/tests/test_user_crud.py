from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from tenants.models import Tenant

User = get_user_model()

class UserCrudTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name="Acme", slug="acme")
        self.other_tenant = Tenant.objects.create(name="Beta", slug="beta")
        self.admin = User.objects.create_user(username="admin", email="admin@acme.com", password="admin123", role="ADMIN", tenant=self.tenant)
        self.manager = User.objects.create_user(username="manager", email="mgr@acme.com", password="manager123", role="SITE_MANAGER", tenant=self.tenant)
        self.alien_admin = User.objects.create_user(username="alien", email="alien@beta.com", password="alien123", role="ADMIN", tenant=self.other_tenant)

    def test_list_users_in_tenant(self):
        self.client.force_authenticate(user=self.admin)
        url = f"/api/{self.tenant.slug}/accounts/users/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()), 2)

    def test_admin_can_create_user_in_tenant(self):
        self.client.force_authenticate(user=self.admin)
        url = f"/api/{self.tenant.slug}/accounts/users/"
        payload = {
            "username": "contractor1",
            "email": "c1@acme.com",
            "role": "CONTRACTOR",
            "password": "pass12345",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(User.objects.filter(username="contractor1", tenant=self.tenant).exists())

    def test_non_admin_cannot_create_user(self):
        self.client.force_authenticate(user=self.manager)
        url = f"/api/{self.tenant.slug}/accounts/users/"
        payload = {
            "username": "blocked",
            "email": "b@acme.com",
            "role": "CONTRACTOR",
            "password": "pass12345",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, 403)

    def test_tenant_mismatch_forbidden(self):
        self.client.force_authenticate(user=self.alien_admin)
        url = f"/api/{self.tenant.slug}/accounts/users/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 403)

    def test_update_user(self):
        self.client.force_authenticate(user=self.admin)
        url = f"/api/{self.tenant.slug}/accounts/users/{self.manager.id}/"
        res = self.client.patch(url, {"email": "new@acme.com"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.email, "new@acme.com")

    def test_delete_user(self):
        self.client.force_authenticate(user=self.admin)
        to_delete = User.objects.create_user(username="temp", email="temp@acme.com", password="tmp12345", role="CONTRACTOR", tenant=self.tenant)
        url = f"/api/{self.tenant.slug}/accounts/users/{to_delete.id}/"
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204)
        self.assertFalse(User.objects.filter(id=to_delete.id).exists())
