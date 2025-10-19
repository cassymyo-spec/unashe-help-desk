from rest_framework.views import APIView
from rest_framework.response import Response

class TwilioWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        from_number = request.data.get("From")
        body = request.data.get("Body", "")
        print("Inbound WhatsApp", {"from": from_number, "body": body})
        return Response({}, content_type="text/xml")
