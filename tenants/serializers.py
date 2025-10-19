from rest_framework import serializers
from .models import Tenant, Site, SiteBudget

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "created_at"]


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = [
            "id",
            "tenant",
            "name",
            "slug",
            "budget",
            "created_at",
        ]
        read_only_fields = ["tenant", "created_at"]


class SiteBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteBudget
        fields = [
            "id",
            "tenant",
            "site",
            "year",
            "month",
            "amount",
            "created_at",
        ]
        read_only_fields = ["tenant", "site", "created_at"]
