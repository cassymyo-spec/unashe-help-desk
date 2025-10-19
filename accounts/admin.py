from django.contrib import admin
from .models import User
from tenants.models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at")
    search_fields = ("name", "slug")

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "role", "tenant")
    list_filter = ("role", "tenant")
    search_fields = ("username", "email")
