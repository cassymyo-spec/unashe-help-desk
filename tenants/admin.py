from django.contrib import admin
from .models import Tenant, Site, SiteBudget

# admin.site.register(Tenant)
admin.site.register(Site)
admin.site.register(SiteBudget)
