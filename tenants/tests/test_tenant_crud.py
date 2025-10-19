from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from tenants.models import Tenant

User = get_user_model()

class TenantCrudTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@root.com",
            password="admin123",
            role="ADMIN",
        )
        self.manager = User.objects.create_user(
            username="manager",
            email="mgr@root.com",
            password="manager123",
            role="SITE_MANAGER",
        )

    def test_admin_can_create_tenant(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            "/api/tenants/",
            {"name": "Acme Inc", "slug": "acme"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Tenant.objects.filter(slug="acme").exists())

    def test_non_admin_cannot_create_tenant(self):
        self.client.force_authenticate(user=self.manager)
        res = self.client.post(
            "/api/tenants/",
            {"name": "Blocked", "slug": "blocked"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_can_list_tenants(self):
        Tenant.objects.create(name="A", slug="a")
        Tenant.objects.create(name="B", slug="b")
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/tenants/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()), 2)

    def test_non_admin_cannot_list_tenants(self):
        self.client.force_authenticate(user=self.manager)
        res = self.client.get("/api/tenants/")
        self.assertEqual(res.status_code, 403)
