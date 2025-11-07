from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.auth import TenantTokenObtainPairView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", TenantTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/tenants/", include("tenants.urls")),
    path("api/<slug:tenant_slug>/sites/", include("tenants.sites_urls")),
    path("api/<slug:tenant_slug>/accounts/", include("accounts.urls")),
    path("api/<slug:tenant_slug>/tickets/", include("tickets.urls")),
    path("api/<slug:tenant_slug>/assets/", include("assets.urls")),

    path("api/webhooks/", include("notifications.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
