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
    job_card = models.FileField(upload_to='media/job_cards', null=True, blank=True)
    site = models.ForeignKey('tenants.Site', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    invoice = models.FileField(upload_to='media/invoices', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id}: {self.title}"


class Asset(models.Model):
    ticket = models.ForeignKey("Ticket", on_delete=models.CASCADE, related_name="assets")
    file = models.FileField(upload_to="ticket_assets/")
    name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Asset {self.id} for Ticket {self.ticket_id}"
