import os
from twilio.rest import Client

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
    return _client

def send_whatsapp(message: str, to: str | None = None):
    if not os.getenv("TWILIO_WHATSAPP_NOTIFY", False):
        print("WhatsApp notifications are disabled.")
        return

    to_number = to or "whatsapp:+263778587612"
    from_number = "whatsapp:+14155238886"

    if not to_number or not from_number:
        print("Missing WhatsApp numbers.")
        return

    client = _get_client()

    try:
        msg = client.messages.create(
            from_=from_number,
            to=to_number,
            body=message
        )
        print(f"✅ Message sent to {to_number}")
        print(f"SID: {msg.sid}")
        print(f"Initial Status: {msg.status}")  
        return msg.sid

    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {e}")
        return None
