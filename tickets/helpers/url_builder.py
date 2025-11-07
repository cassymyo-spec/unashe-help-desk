from tenants.models import Tenant
from django.conf import settings

def get_ticket_url(ticket):
    site_domain = Tenant.objects.get(id=ticket.tenant.id).domain
    return f"https://{site_domain}{ticket.get_absolute_url()}"
    
