from rest_framework import generics, permissions, exceptions, viewsets
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from tenants.utils import get_tenant_by_slug_or_404
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    UserWriteSerializer,
    PasswordOTPRequestSerializer,
    PasswordOTPVerifySerializer,
    PasswordResetSerializer,
)
from .models import PasswordResetOTP
from django.core.mail import send_mail
from django.conf import settings

try:
    from twilio.rest import Client as TwilioClient  # type: ignore
except Exception:  # pragma: no cover
    TwilioClient = None  # type: ignore

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


class PasswordOTPRequestView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordOTPRequestSerializer

    def post(self, request, tenant_slug: str):
        tenant = get_tenant_by_slug_or_404(tenant_slug)
        serializer = self.get_serializer(data=request.data, context={"tenant": tenant})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        channel = serializer.validated_data["channel"]
        destination = serializer.validated_data.get("destination") or ""
        if channel == PasswordResetOTP.Channel.WHATSAPP and not destination:
            raise exceptions.ValidationError({"destination": "WhatsApp destination is required"})

        otp = PasswordResetOTP.create_for(user=user, channel=channel, destination=destination or None)

        if channel == PasswordResetOTP.Channel.EMAIL:
            try:
                send_mail(
                    subject="Your UnashDesk OTP Code",
                    message=f"Your password reset code is: {otp.code}",
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                pass
        else:
            try:
                if TwilioClient and getattr(settings, "TWILIO_ACCOUNT_SID", None) and getattr(settings, "TWILIO_AUTH_TOKEN", None):
                    client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    from_whatsapp = getattr(settings, "TWILIO_WHATSAPP_FROM", None)
                    if from_whatsapp:
                        client.messages.create(
                            body=f"Your UnashDesk OTP code is {otp.code}",
                            from_=from_whatsapp,
                            to=destination,
                        )
            except Exception:
                pass

        return Response({"detail": "OTP sent"})


class PasswordOTPVerifyView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordOTPVerifySerializer

    def post(self, request, tenant_slug: str):
        tenant = get_tenant_by_slug_or_404(tenant_slug)
        serializer = self.get_serializer(data=request.data, context={"tenant": tenant})
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data["otp"]
        return Response({"detail": "OTP valid"})


class PasswordResetView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetSerializer

    def post(self, request, tenant_slug: str):
        tenant = get_tenant_by_slug_or_404(tenant_slug)
        serializer = self.get_serializer(data=request.data, context={"tenant": tenant})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password has been reset"})

class MeView(generics.GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant_slug = self.kwargs.get("tenant_slug")
        if tenant_slug and (not request.user.tenant or request.user.tenant.slug != tenant_slug):
            raise exceptions.PermissionDenied("Tenant mismatch")
        return Response(UserSerializer(request.user).data)


class IsTenantAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == "ADMIN"
        )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsTenantAdmin()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return UserWriteSerializer
        return UserSerializer

    def get_queryset(self):
        user = self.request.user
        tenant_slug = self.kwargs.get("tenant_slug")
        if tenant_slug and (not user.tenant or user.tenant.slug != tenant_slug):
            raise exceptions.PermissionDenied("Tenant mismatch")
        if not user.tenant_id:
            return User.objects.none()
        return User.objects.filter(tenant_id=user.tenant_id).order_by("id")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        tenant_slug = self.kwargs.get("tenant_slug")
        if tenant_slug:
            ctx["tenant"] = get_tenant_by_slug_or_404(tenant_slug)
        return ctx
