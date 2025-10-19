from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN"
        CONTRACTOR = "CONTRACTOR"
        SITE_MANAGER = "SITE_MANAGER"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SITE_MANAGER)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name="users", null=True, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["username", "tenant"], name="uniq_username_tenant"),
            models.UniqueConstraint(fields=["email", "tenant"], name="uniq_email_tenant"),
        ]
