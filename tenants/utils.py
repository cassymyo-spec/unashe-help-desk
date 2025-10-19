from django.shortcuts import get_object_or_404
from .models import Tenant

def get_tenant_by_slug_or_404(slug: str) -> Tenant:
    return get_object_or_404(Tenant, slug=slug)
