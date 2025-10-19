from rest_framework import serializers
from django.contrib.auth import get_user_model
from tenants.models import Tenant

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "tenant"]
        read_only_fields = ["id", "role", "tenant"]

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.Role.choices)
    tenant_slug = serializers.SlugField(required=False)

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
        )
        return user
