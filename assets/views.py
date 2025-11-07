from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, exceptions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Asset, AssetLog
from .serializers import AssetSerializer, AssetLogSerializer
from django.db.models import Count
from loguru import logger

class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        user = self.request.user
        tenant_slug = self.kwargs.get("tenant_slug")
        if tenant_slug and (not user.tenant or user.tenant.slug != tenant_slug):
            raise exceptions.PermissionDenied("Tenant mismatch")
        if not user.tenant_id:
            return Asset.objects.none()
        return Asset.objects.filter(tenant_id=user.tenant_id).order_by("-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validate(serializer.validated_data)

        if data.get("name") is None:
            raise exceptions.ValidationError("Name is required ")

        if Asset.objects.filter(name=data.get("name")).exists():
            raise exceptions.ValidationError("Asset with this name already exists")

        if data.get("quantity") is None:
            raise exceptions.ValidationError("Quantity is required")

        if data.get("quantity") < 1:
            raise exceptions.ValidationError("Quantity must be greater than 0")

        serializer.save(tenant=user.tenant, created_by=user)
        logger.success(f"Asset {serializer.instance.id} created by {user}")

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        
        # Handle file upload if present
        if 'image' in self.request.FILES:
            instance.image = self.request.FILES['image']
            instance.save(update_fields=['image'])
        
        # Update other fields
        serializer.save(updated_by=user)
        logger.success(f"Asset {instance.id} updated by {user}")
        
        # If quantity changed, the signal will handle the log creation


    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.disable = True
        instance.save()
        logger.success(f"Asset {instance.id} disabled by {request.user}")
        return Response(status=status.HTTP_204_NO_CONTENT)

class AssetLogViewSet(viewsets.ModelViewSet):
    serializer_class = AssetLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        asset_id = self.kwargs.get("asset_id")
        logger.info(f"Asset {asset_id} logs")
        if not asset_id:
            return AssetLog.objects.none()
            
        try:
            asset = Asset.objects.get(id=asset_id, tenant=user.tenant)
            return AssetLog.objects.filter(asset=asset).order_by("-created_at") or []
        except Asset.DoesNotExist:
            logger.warning(f"Asset {asset_id} not found or access denied for user {user.id}")
            return AssetLog.objects.none()    
        
