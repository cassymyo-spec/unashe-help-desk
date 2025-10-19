from django.db import models

class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN"
        IN_PROGRESS = "IN_PROGRESS"
        RESOLVED = "RESOLVED"
        CLOSED = "CLOSED"

    class Priority(models.TextChoices):
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"
        URGENT = "URGENT"

    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='tickets')
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='tickets_created')
    assignee = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_assigned')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id}: {self.title}"
