from rest_framework.routers import DefaultRouter
from .views import SiteViewSet

router = DefaultRouter()
router.register(r"", SiteViewSet, basename="site")

urlpatterns = router.urls
