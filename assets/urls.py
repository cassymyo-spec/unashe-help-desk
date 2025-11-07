from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, AssetLogViewSet

router = DefaultRouter()
router.register(r"", AssetViewSet, basename="asset")

asset_logs = AssetLogViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

urlpatterns = [
    path('<int:asset_id>/asset-logs/', asset_logs, name='asset-logs'),
] + router.urls
