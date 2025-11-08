from rest_framework import viewsets, permissions, exceptions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
from django.db.models import Q
from .models import Ticket
from assets.models import Asset
from tickets.serializers import *
from assets.serializers import AssetSerializer
from notifications.twilio_service import send_whatsapp
from django.db.models import Count
from loguru import logger
import os
from .helpers.url_builder import get_ticket_url

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'priority', 'status']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
        
    def get_queryset(self):
        user = self.request.user
        if not user.tenant_id:
            return Ticket.objects.none()
            
        if user.role == 'CONTRACTOR':
            queryset = Ticket.objects.filter(tenant_id=user.tenant_id, assignee=user)
        elif user.role == 'SITE_MANAGER':
            queryset = Ticket.objects.filter(tenant_id=user.tenant_id, site=user.site)
        else:
            queryset = Ticket.objects.filter(tenant_id=user.tenant_id)
        
        status = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        search = self.request.query_params.get('search')
        
        if status:
            queryset = queryset.filter(status=status)
            
        if priority:
            queryset = queryset.filter(priority=priority)
            
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
            
        return queryset
        
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        logger.info(f"Page: {page}")
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(tenant=user.tenant, created_by=user)
        if getattr(settings, "TWILIO_WHATSAPP_NOTIFY", False):
            send_whatsapp(f"New ticket: {serializer.instance.title} ({serializer.instance.id})")

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None, tenant_slug=None): 
        ticket = self.get_object()
        assignee_id = request.data.get("assignee_id")
        asset_id = request.data.get("asset_id")

        if assignee_id:
            ticket.assignee_id = assignee_id
            ticket.save(update_fields=["assignee"])

        if asset_id:
            ticket.assets.add(asset_id)
            ticket.save(update_fields=["assets"])

        if os.getenv("TWILIO_WHATSAPP_NOTIFY", False):
            message = (
                f"📋 *Ticket Update*\n\n"
                f"Status: {ticket.status}\n"
                f"Title: {ticket.title}\n"
                f"Assigned to: {ticket.assignee.username}\n\n"
                f"{ticket.description}\n\n"
                f"🔗 View Ticket: {get_ticket_url(ticket)}"
            )
            send_whatsapp(message)
            logger.info("Ticket updated: {} (assigned to {})".format(ticket.title, ticket.assignee.username))
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
        image_obj = request.FILES.get("image") or request.FILES.get("file")
        if not image_obj:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
        asset = Asset.objects.create(
            ticket=ticket,
            tenant=ticket.tenant,
            image=image_obj,
            name=getattr(image_obj, "name", "") or "",
        )
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
    def upload_invoice(self, request, pk=None, tenant_slug=None):
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


