from django.conf import settings
from twilio.rest import Client

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client

def send_whatsapp(message: str, to: str | None = None):
    if not settings.TWILIO_WHATSAPP_NOTIFY:
        return
    to_number = to or settings.DEFAULT_NOTIFY_TO_WHATSAPP
    from_number = settings.TWILIO_WHATSAPP_FROM
    if not to_number or not from_number:
        return
    client = _get_client()
    client.messages.create(from_=from_number, to=to_number, body=message)
