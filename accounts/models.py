from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN"
        CONTRACTOR = "CONTRACTOR"
        SITE_MANAGER = "SITE_MANAGER"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SITE_MANAGER)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name="users", null=True, blank=True)
    site = models.ForeignKey('tenants.Site', on_delete=models.SET_NULL, related_name="users", null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="Phone Number")

    company_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Company Name")
    address = models.TextField(null=True, blank=True, verbose_name="Company Address")
    is_active_contractor = models.BooleanField(default=True, verbose_name="Active Contractor")
    
    email = models.EmailField(unique=False, blank=True, null=True)  
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["username", "tenant"], name="uniq_username_tenant"),
            models.UniqueConstraint(fields=["email", "tenant"], name="uniq_email_tenant"),
        ]


class PasswordResetOTP(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_otps")
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name="password_otps")
    code = models.CharField(max_length=6)
    channel = models.CharField(max_length=16, choices=Channel.choices)
    destination = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    def has_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @classmethod
    def create_for(cls, user, channel: str, destination: str | None = None, ttl_minutes: int = 10):
        from random import randint
        code = f"{randint(0, 999999):06d}"
        return cls.objects.create(
            user=user,
            tenant=user.tenant,
            code=code,
            channel=channel,
            destination=destination or "",
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )
