from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from tenants.models import Tenant

User = get_user_model()

class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    tenant_slug = serializers.SlugField(write_only=True)

    def validate(self, attrs):
        tenant_slug = attrs.pop("tenant_slug", None)
        if not tenant_slug:
            raise serializers.ValidationError({"tenant_slug": "This field is required."})
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            raise serializers.ValidationError({"tenant_slug": "Invalid tenant."})

        username_field = User.USERNAME_FIELD
        credentials = {
            username_field: attrs.get(self.username_field),
            "password": attrs.get("password"),
        }
        user = authenticate(**credentials)
        if not user or not user.is_active:
            raise serializers.ValidationError({"detail": "No active account found with the given credentials"})
        if not user.tenant_id or user.tenant_id != tenant.id:
            raise serializers.ValidationError({"detail": "User does not belong to this tenant"})

        data = super().validate({self.username_field: getattr(user, self.username_field), "password": attrs.get("password")})
        # include tenant info and role in token (custom claims)
        self.user = user
        data["tenant"] = tenant.slug
        data["role"] = user.role
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["tenant_id"] = user.tenant_id
        return token

class TenantTokenObtainPairView(TokenObtainPairView):
    serializer_class = TenantTokenObtainPairSerializer
