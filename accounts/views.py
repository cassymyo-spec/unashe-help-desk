from rest_framework import generics, permissions, exceptions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from tenants.utils import get_tenant_by_slug_or_404
from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        tenant_slug = self.kwargs.get("tenant_slug")
        if tenant_slug:
            ctx["tenant"] = get_tenant_by_slug_or_404(tenant_slug)
        return ctx

class MeView(generics.GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant_slug = self.kwargs.get("tenant_slug")
        if tenant_slug and (not request.user.tenant or request.user.tenant.slug != tenant_slug):
            raise exceptions.PermissionDenied("Tenant mismatch")
        return Response(UserSerializer(request.user).data)
