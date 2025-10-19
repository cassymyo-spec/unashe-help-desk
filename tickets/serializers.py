from rest_framework import serializers
from .models import Ticket

class TicketSerializer(serializers.ModelSerializer):
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["tenant", "created_by", "created_at", "updated_at"]
