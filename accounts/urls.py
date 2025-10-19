from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView,
    MeView,
    UserViewSet,
    PasswordOTPRequestView,
    PasswordOTPVerifyView,
    PasswordResetView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("password/otp/request/", PasswordOTPRequestView.as_view(), name="password_otp_request"),
    path("password/otp/verify/", PasswordOTPVerifyView.as_view(), name="password_otp_verify"),
    path("password/reset/", PasswordResetView.as_view(), name="password_reset"),
]

urlpatterns += router.urls
