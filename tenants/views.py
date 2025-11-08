from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import Tenant, Site, SiteBudget
from .serializers import TenantSerializer, SiteSerializer, SiteBudgetSerializer
from tenants.utils import get_tenant_by_slug_or_404
# from loguru import logger÷

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "ADMIN")

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated & IsAdmin]


class SiteViewSet(viewsets.ModelViewSet):
    serializer_class = SiteSerializer
    permission_classes = [permissions.IsAuthenticated & IsAdmin]

    def get_queryset(self):
        tenant_slug = self.kwargs.get("tenant_slug")
        tenant = get_tenant_by_slug_or_404(tenant_slug)
        return Site.objects.filter(tenant=tenant).order_by("name")

    def perform_create(self, serializer):
        print(self.request.user.role)
        tenant_slug = self.kwargs.get("tenant_slug")
        tenant = get_tenant_by_slug_or_404(tenant_slug)
        serializer.save(tenant=tenant)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="budgets")
    def budgets(self, request, *args, **kwargs):
        from django.db.models import Sum, Q
        from django.utils import timezone
        from tickets.models import Ticket
        
        tenant_slug = self.kwargs.get("tenant_slug")
        tenant = get_tenant_by_slug_or_404(tenant_slug)
        year = request.query_params.get("year")
        month = request.query_params.get("month")
        
        if year:
            budget_query = Q(tenant=tenant, year=year)
            if month:
                budget_query &= Q(month=month)
                
            rows = (
                SiteBudget.objects.filter(budget_query)
                .values("site__name", "site__slug", "year", "month")
                .annotate(budget_sum=Sum("amount"))
                .order_by("site__name")
            )
            
            spending_query = Q(site__tenant=tenant, invoice_amount__isnull=False)
            if year and month:
                start_date = timezone.datetime(int(year), int(month), 1)
                if int(month) == 12:
                    end_date = timezone.datetime(int(year) + 1, 1, 1)
                else:
                    end_date = timezone.datetime(int(year), int(month) + 1, 1)
                spending_query &= Q(resolved_at__gte=start_date, resolved_at__lt=end_date)
            
            spending = Ticket.objects.filter(spending_query).values('site__name').annotate(
                total_spent=Sum('invoice_amount')
            )
            
            data = []
            for row in rows:
                site_spending = next(
                    (s for s in spending if s['site__name'] == row['site__name']),
                    {'total_spent': 0}
                )
                data.append({
                    'site': row['site__name'],
                    'slug': row['site__slug'],
                    'budget': str(row['budget_sum']) if row['budget_sum'] is not None else '0',
                    'year': row['year'],
                    'month': row.get('month'),
                    'spent': float(site_spending['total_spent']) if site_spending['total_spent'] else 0,
                    'remaining': float(row['budget_sum'] - site_spending['total_spent']) if row['budget_sum'] and site_spending['total_spent'] else float(row['budget_sum'] or 0),
                    'utilization': (float(site_spending['total_spent']) / float(row['budget_sum']) * 100) if row['budget_sum'] and site_spending['total_spent'] else 0
                })
            
            return Response(data)
        
        sites = Site.objects.filter(tenant=tenant).order_by('name')
        result = []
        
        for site in sites:
            latest_budget = SiteBudget.objects.filter(site=site).order_by('-year', '-month').first()
            
            # Calculate current month's spending
            today = timezone.now()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = today.replace(day=28) + timezone.timedelta(days=4)  # Get to next month
            start_of_next_month = next_month.replace(day=1)
            
            monthly_spending = Ticket.objects.filter(
                site=site,
                resolved_at__gte=start_of_month,
                resolved_at__lt=start_of_next_month,
                invoice_amount__isnull=False
            ).aggregate(total=Sum('invoice_amount'))['total'] or 0
            
            result.append({
                'site': site.name,
                'slug': site.slug,
                'budget': str(latest_budget.amount) if latest_budget else '0',
                'year': latest_budget.year if latest_budget else today.year,
                'month': latest_budget.month if latest_budget else today.month,
                'spent': float(monthly_spending),
                'remaining': float(latest_budget.amount - monthly_spending) if latest_budget else 0,
                'utilization': (float(monthly_spending) / float(latest_budget.amount) * 100) if latest_budget and latest_budget.amount > 0 else 0
            })
            
        return Response(result)

    # Nested monthly budgets for a single site
    # GET /api/<tenant_slug>/sites/<pk>/budgets/?year=YYYY
    # POST /api/<tenant_slug>/sites/<pk>/budgets/ { year, month, amount }
    @action(detail=True, methods=["get", "post"], url_path="budgets")
    def site_budgets(self, request, pk=None, *args, **kwargs):
        from django.utils import timezone
        from django.db.models import Sum
        from tickets.models import Ticket
        
        tenant_slug = self.kwargs.get("tenant_slug")
        tenant = get_tenant_by_slug_or_404(tenant_slug)
        site = self.get_queryset().filter(pk=pk).first()
        if not site:
            return Response({"detail": "Site not found"}, status=404)

        if request.method.lower() == "get":
            year = request.query_params.get("year")
            month = request.query_params.get("month")
            
            # If year is provided, return all budgets for that year (or specific month)
            if year:
                qs = SiteBudget.objects.filter(tenant=tenant, site=site, year=year)
                if month:
                    qs = qs.filter(month=month)
                
                # Get spending data for each month
                budgets = qs.order_by("year", "month")
                result = []
                
                for budget in budgets:
                    # Calculate spending for this budget period
                    start_date = timezone.datetime(budget.year, budget.month, 1)
                    if budget.month == 12:
                        end_date = timezone.datetime(budget.year + 1, 1, 1)
                    else:
                        end_date = timezone.datetime(budget.year, budget.month + 1, 1)
                    
                    spending = Ticket.objects.filter(
                        site=site,
                        resolved_at__gte=start_date,
                        resolved_at__lt=end_date,
                        invoice_amount__isnull=False
                    ).aggregate(total=Sum('invoice_amount'))['total'] or 0
                    
                    result.append({
                        **SiteBudgetSerializer(budget).data,
                        'spent': float(spending),
                        'remaining': float(budget.amount - spending) if budget.amount else 0,
                        'utilization': (float(spending) / float(budget.amount) * 100) if budget.amount > 0 else 0
                    })
                
                return Response(result)
            
            # If no year is specified, return the latest budget with current month's spending
            latest_budget = SiteBudget.objects.filter(site=site).order_by('-year', '-month').first()
            
            # Calculate current month's spending
            today = timezone.now()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = today.replace(day=28) + timezone.timedelta(days=4)  # Get to next month
            start_of_next_month = next_month.replace(day=1)
            
            monthly_spending = Ticket.objects.filter(
                site=site,
                resolved_at__gte=start_of_month,
                resolved_at__lt=start_of_next_month,
                invoice_amount__isnull=False
            ).aggregate(total=Sum('invoice_amount'))['total'] or 0
            
            if latest_budget:
                data = {
                    **SiteBudgetSerializer(latest_budget).data,
                    'spent': float(monthly_spending),
                    'remaining': float(latest_budget.amount - monthly_spending) if latest_budget.amount else 0,
                    'utilization': (float(monthly_spending) / float(latest_budget.amount) * 100) if latest_budget.amount > 0 else 0
                }
                return Response(data)
            return Response({"detail": "No budget found for this site"}, status=404)

        # POST -> upsert monthly budget
        serializer = SiteBudgetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data["year"]
        month = serializer.validated_data["month"]
        amount = serializer.validated_data["amount"]
        
        # Create or update budget
        obj, created = SiteBudget.objects.update_or_create(
            tenant=tenant, 
            site=site, 
            year=year, 
            month=month,
            defaults={"amount": amount},
        )
        
        # If this is a new budget for the current month, update the site's default budget
        if created and year == timezone.now().year and month == timezone.now().month:
            site.budget = amount
            site.save(update_fields=['budget'])
        
        return Response(SiteBudgetSerializer(obj).data, status=201 if created else 200)
