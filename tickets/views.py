from rest_framework import viewsets, permissions, exceptions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings
from .models import Ticket, Asset
from .serializers import TicketSerializer, AssetSerializer
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

    @action(detail=True, methods=["post"], url_path="assets")
    def add_asset(self, request, pk=None):
        ticket = self.get_object()
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        asset = Asset.objects.create(ticket=ticket, file=file_obj, name=file_obj.name)
        serializer = AssetSerializer(asset)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="job-card")
    def upload_job_card(self, request, pk=None):
        ticket = self.get_object()
        if request.user.role not in ("SITE_MANAGER", "ADMIN"):
            raise exceptions.PermissionDenied("Only site managers or admins can upload a job card")

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        if ticket.job_card:
            ticket.job_card.delete(save=False)
        ticket.job_card = file_obj
        ticket.save(update_fields=["job_card"])
        serializer = self.get_serializer(ticket)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="invoice")
    def upload_invoice(self, request, pk=None):
        ticket = self.get_object()
        if request.user.role not in ("SITE_MANAGER", "ADMIN"):
            raise exceptions.PermissionDenied("Only site managers or admins can upload an invoice")

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        if ticket.invoice:
            ticket.invoice.delete(save=False)
        ticket.invoice = file_obj
        ticket.save(update_fields=["invoice"])
        serializer = self.get_serializer(ticket)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], url_path="assets/(?P<asset_id>[^/.]+)")
    def remove_asset(self, request, pk=None, asset_id=None):
        ticket = self.get_object()
        try:
            asset = ticket.assets.get(pk=asset_id)
        except Asset.DoesNotExist:
            return Response({"error": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)
        asset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
