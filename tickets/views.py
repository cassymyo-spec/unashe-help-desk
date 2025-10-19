from rest_framework import viewsets, permissions, exceptions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings
from .models import Ticket
from .serializers import TicketSerializer
from notifications.twilio_service import send_whatsapp
from django.db.models import Count

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant_slug = self.kwargs.get("tenant_slug")
        if tenant_slug and (not user.tenant or user.tenant.slug != tenant_slug):
            raise exceptions.PermissionDenied("Tenant mismatch")
        if not user.tenant_id:
            return Ticket.objects.none()
        return Ticket.objects.filter(tenant_id=user.tenant_id).order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(tenant=user.tenant, created_by=user)
        if getattr(settings, "TWILIO_WHATSAPP_NOTIFY", False):
            send_whatsapp(f"New ticket: {serializer.instance.title} ({serializer.instance.id})")

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        ticket = self.get_object()
        assignee_id = request.data.get("assignee_id")
        if assignee_id:
            ticket.assignee_id = assignee_id
            ticket.save(update_fields=["assignee"])
        if getattr(settings, "TWILIO_WHATSAPP_NOTIFY", False):
            send_whatsapp(f"Ticket updated: {ticket.title} (assigned to {ticket.assignee_id})")
        return Response(TicketSerializer(ticket).data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request, tenant_slug=None):
        user = request.user
        if tenant_slug and (not user.tenant or user.tenant.slug != tenant_slug):
            raise exceptions.PermissionDenied("Tenant mismatch")
        if not user.tenant_id:
            return Response({})
        qs = Ticket.objects.filter(tenant_id=user.tenant_id)
        agg = qs.values("status").annotate(c=Count("id"))
        data = {k: 0 for k, _ in Ticket.Status.choices}
        for row in agg:
            data[row["status"]] = row["c"]
        return Response(data)
