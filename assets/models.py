from django.db import models

class Asset(models.Model):
    serial_number = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to='assets', null=True, blank=True)
    name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    quantity = models.IntegerField(default=1)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # unit = models.CharField(max_length=50, blank=True, null=True) // to be reviewed
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='assets')
    disable = models.BooleanField(default=False, null=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='assets', null=True, blank=True)
    updated_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='assets_updated', null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name or f"Asset {self.id} for Ticket {self.name}"


class AssetLog(models.Model):
    asset = models.ForeignKey("Asset", on_delete=models.CASCADE, related_name="logs")
    quantity = models.IntegerField(help_text="Current quantity after this change")
    change = models.IntegerField(help_text="Difference in quantity from previous state")
    unit = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Asset Log'
        verbose_name_plural = 'Asset Logs'

    def __str__(self):
        change_str = f"+{self.change}" if self.change > 0 else str(self.change)
        return f"{self.asset.name} - {change_str} (now: {self.quantity})"