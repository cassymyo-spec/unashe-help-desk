from django.db import models
from datetime import date

class Tenant(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    domain = models.CharField(max_length=200)

    def __str__(self):
        return self.slug


class Site(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=200)
    slug = models.SlugField()
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "slug"], name="uniq_site_slug_per_tenant"),
        ]

    def __str__(self):
        return f"{self.tenant.slug}/{self.slug}"


class SiteBudget(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='site_budgets')
    site = models.ForeignKey('tenants.Site', on_delete=models.CASCADE, related_name='budgets')
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()  # 1-12
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["site", "year", "month"], name="uniq_site_budget_month"),
        ]

    def __str__(self):
        return f"{self.site} {self.year}-{self.month:02d}: {self.amount}"
