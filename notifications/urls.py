from django.urls import path
from .views import TwilioWebhookView

urlpatterns = [
    path("twilio/", TwilioWebhookView.as_view(), name="twilio-webhook"),
]
