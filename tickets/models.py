from django.db import models
from django.urls import reverse


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN"  # Ticket created, not yet assigned
        ASSIGNED = "ASSIGNED"  # Assigned to contractor, waiting confirmation
        IN_PROGRESS = "IN_PROGRESS"  # Work in progress
        RESOLVED = "RESOLVED"  # Work completed, waiting for review
        CLOSED = "CLOSED"  # Ticket closed

    class Priority(models.TextChoices):
        LOW = "LOW"  # Routine maintenance
        MEDIUM = "MEDIUM"  # Standard issue
        HIGH = "HIGH"  # Urgent issue
        URGENT = "URGENT"  # Critical issue

    # Core ticket information
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    
    # Relationships
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='tickets')
    created_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE, 
        related_name='tickets_created',
        help_text="Site Manager who created the ticket"
    )
    assignee = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='tickets_assigned',
        limit_choices_to={'role': 'CONTRACTOR', 'is_active_contractor': True},
        help_text="Contractor assigned to this ticket"
    )
    
    # Location and assets
    site = models.ForeignKey(
        'tenants.Site', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='tickets',
        help_text="Site where the work needs to be done"
    )
    assets = models.ManyToManyField(
        'assets.Asset', 
        related_name='tickets', 
        blank=True,
        help_text="Assets related to this ticket"
    )
    
    # Documents
    job_card = models.FileField(
        upload_to='media/job_cards/%Y/%m/%d/', 
        null=True, 
        blank=True,
        help_text="Completed job card with work details"
    )
    invoice = models.FileField(
        upload_to='media/invoices/%Y/%m/%d/', 
        null=True, 
        blank=True,
        help_text="Invoice for the work done"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Contractor rating (filled by site manager)
    contractor_rating = models.PositiveSmallIntegerField(
        null=True, 
        blank=True,
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="Rating from 1 to 5"
    )
    contractor_feedback = models.TextField(
        null=True, 
        blank=True,
        help_text="Feedback about the contractor's work"
    )
    
    # Status tracking
    is_urgent = models.BooleanField(default=False)
    requires_follow_up = models.BooleanField(default=False)
    follow_up_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.id}: {self.title} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse(
            "ticket-detail", 
            kwargs={"tenant_slug": self.tenant.slug, "pk": self.pk}
        )
        
    def assign_contractor(self, contractor):
        """Helper method to assign a contractor to the ticket"""
        if contractor.role != 'CONTRACTOR':
            raise ValueError("Only users with role CONTRACTOR can be assigned to tickets")
            
        self.assignee = contractor
        self.status = self.Status.ASSIGNED
        self.assigned_at = timezone.now()
        self.save()
        
        # Send notification to contractor
        from .notifications import send_ticket_assignment_notification
        send_ticket_assignment_notification(self)
        
        return self
    
    def start_work(self):
        """Mark ticket as in progress"""
        self.status = self.Status.IN_PROGRESS
        self.started_at = timezone.now()
        self.save()
        
        # Send notification to site manager
        from .notifications import send_ticket_status_update
        send_ticket_status_update(self, self.Status.ASSIGNED)
        
        return self
    
    def mark_resolved(self):
        """Mark ticket as resolved (work completed)"""
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save()
        
        # Send notification to site manager
        from .notifications import send_ticket_status_update
        send_ticket_status_update(self, self.Status.IN_PROGRESS)
        
        return self
    
    def close_ticket(self, rating=None, feedback=None):
        """Close the ticket with optional rating"""
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        
        if rating is not None:
            self.contractor_rating = rating
        if feedback is not None:
            self.contractor_feedback = feedback
            
        self.save()
        
        # Send notification to contractor
        from .notifications import send_ticket_status_update
        send_ticket_status_update(self, self.Status.RESOLVED)
        
        return self

