from rest_framework import serializers
from .models import Asset, AssetLog

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "name", "image", "quantity", "created_at", "active"]
        read_only_fields = ["created_at"]

class AssetLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetLog
        fields = ["id", "asset", "quantity", "created_at"]
        read_only_fields = ["created_at"]
   