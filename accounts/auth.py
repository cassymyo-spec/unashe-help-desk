from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from tenants.models import Tenant

User = get_user_model()

class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Make serializer expect 'email' instead of SimpleJWT's default username field
    username_field = 'email'
    tenant_slug = serializers.SlugField(write_only=True)
    email = serializers.EmailField(write_only=True, required=False)

    def validate(self, attrs):
        tenant_slug = attrs.pop("tenant_slug", None)
        if not tenant_slug:
            raise serializers.ValidationError({"tenant_slug": "This field is required."})
        try:
            tenant = Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            raise serializers.ValidationError({"tenant_slug": "Invalid tenant."})

        identifier = (
            attrs.get("email")
            or attrs.get(self.username_field)
            or self.initial_data.get("email")
            or self.initial_data.get(self.username_field)
            or self.initial_data.get("username")
        )
        password = attrs.get("password") or self.initial_data.get("password")
        if not identifier or not password:
            raise serializers.ValidationError({"detail": "Missing credentials"})

        # Find user within the tenant by email first, then username
        user = None
        try:
            user = User.objects.get(tenant=tenant, email=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(tenant=tenant, username=identifier)
            except User.DoesNotExist:
                pass

        if not user or not user.is_active or not user.check_password(password):
            raise serializers.ValidationError({"detail": "No active account found with the given credentials"})

        # Build tokens directly (do not call super().validate which relies on USERNAME_FIELD)
        refresh = self.get_token(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "tenant": tenant.slug,
            "role": user.role,
        }
        self.user = user
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

class TenantTokenObtainPairView(TokenObtainPairView):
    serializer_class = TenantTokenObtainPairSerializer
