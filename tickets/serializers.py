from rest_framework import serializers
from .models import Ticket, Asset


class TicketSerializer(serializers.ModelSerializer):
    assets = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "tenant",
            "created_by",
            "assignee",
            "site",
            "job_card",
            "invoice",
            "assets",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["tenant", "created_by", "created_at", "updated_at", "job_card", "invoice"]

    def get_assets(self, obj):
        return AssetSerializer(obj.assets.all(), many=True).data


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "name", "file", "created_at"]
        read_only_fields = ["created_at"]
