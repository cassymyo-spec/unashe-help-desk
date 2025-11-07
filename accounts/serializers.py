from rest_framework import serializers
from django.contrib.auth import get_user_model
from tenants.models import Tenant
from .models import PasswordResetOTP

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "tenant", "site", "phone_number", "company_name", "address", "is_active_contractor", "first_name", "last_name"]
        read_only_fields = ["id", "role", "tenant"]

class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        tenant = self.context.get("tenant")
        site = self.context.get("site")
        if tenant is None:
            raise serializers.ValidationError({"tenant": "Tenant is r`equired"})
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.tenant = tenant
        user.set_password(password)
        user.save()
        return user


class PasswordOTPRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    channel = serializers.ChoiceField(choices=PasswordResetOTP.Channel.choices)
    destination = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        tenant = self.context.get("tenant")
        identifier = attrs.get("identifier")
        try:
            user = User.objects.get(tenant=tenant, email=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(tenant=tenant, username=identifier)
            except User.DoesNotExist:
                raise serializers.ValidationError({"identifier": "User not found"})
        attrs["user"] = user
        return attrs


class PasswordOTPVerifySerializer(serializers.Serializer):
    identifier = serializers.CharField()
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        tenant = self.context.get("tenant")
        identifier = attrs.get("identifier")
        code = attrs.get("code")
        try:
            user = User.objects.get(tenant=tenant, email=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(tenant=tenant, username=identifier)
            except User.DoesNotExist:
                raise serializers.ValidationError({"identifier": "User not found"})
        otp = (
            PasswordResetOTP.objects.filter(user=user, tenant=tenant, code=code, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if not otp:
            raise serializers.ValidationError({"code": "Invalid code"})
        if otp.has_expired():
            raise serializers.ValidationError({"code": "Code expired"})
        attrs["user"] = user
        attrs["otp"] = otp
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        tenant = self.context.get("tenant")
        identifier = attrs.get("identifier")
        code = attrs.get("code")
        try:
            user = User.objects.get(tenant=tenant, email=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(tenant=tenant, username=identifier)
            except User.DoesNotExist:
                raise serializers.ValidationError({"identifier": "User not found"})
        otp = (
            PasswordResetOTP.objects.filter(user=user, tenant=tenant, code=code, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if not otp:
            raise serializers.ValidationError({"code": "Invalid code"})
        if otp.has_expired():
            raise serializers.ValidationError({"code": "Code expired"})
        attrs["user"] = user
        attrs["otp"] = otp
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        otp = self.validated_data["otp"]
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save()
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.Role.choices)
    tenant_slug = serializers.SlugField(required=False)
    site = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField()

    def create(self, validated_data):
        tenant = self.context.get("tenant")
        if tenant is None and "tenant_slug" in validated_data:
            tenant = Tenant.objects.get(slug=validated_data["tenant_slug"])
        if tenant is None:
            raise serializers.ValidationError({"tenant": "Tenant is required"})
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            role=validated_data["role"],
            tenant=tenant,
            phone=validated_data["phone"],
            first_name=validated_data['firstName'],
            last_name=validated_data['lastName'],
            site_id=validated_data["siteId"]
        )
        return user
