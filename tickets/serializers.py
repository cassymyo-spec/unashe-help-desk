from rest_framework import serializers
from tickets.models import Ticket
from assets.models import Asset, AssetLog
from assets.serializers import AssetSerializer

class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    phone_number = serializers.CharField(required=False, allow_blank=True)
    company_name = serializers.CharField(source='profile.company_name', required=False, allow_blank=True)
    
    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email

class TicketSerializer(serializers.ModelSerializer):
    assets = serializers.SerializerMethodField()
    assignee = UserSerializer(read_only=True)
    job_card = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()
    
    def get_job_card(self, obj):
        if obj.job_card:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.job_card.url)
            return obj.job_card.url
        return None
        
    def get_invoice(self, obj):
        if obj.invoice:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.invoice.url)
            return obj.invoice.url
        return None

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
