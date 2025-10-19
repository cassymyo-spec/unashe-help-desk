from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.auth import TenantTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth
    path("api/auth/token/", TenantTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Public tenant management (admin-only guarded in views)
    path("api/tenants/", include("tenants.urls")),
    # Tenant-scoped routes via path prefix
    path("api/<slug:tenant_slug>/accounts/", include("accounts.urls")),
    path("api/<slug:tenant_slug>/tickets/", include("tickets.urls")),
    # Webhooks (global)
    path("api/webhooks/", include("notifications.urls")),
]
