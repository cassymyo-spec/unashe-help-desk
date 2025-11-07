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

    # GET /api/<tenant_slug>/sites/budgets/
    @action(detail=False, methods=["get"], url_path="budgets")
    def budgets(self, request, *args, **kwargs):
        tenant_slug = self.kwargs.get("tenant_slug")
        tenant = get_tenant_by_slug_or_404(tenant_slug)
        year = request.query_params.get("year")
        if year:
            rows = (
                SiteBudget.objects.filter(tenant=tenant, year=year)
                .values("site__name", "site__slug")
                .annotate(budget_sum=Sum("amount"))
                .order_by("site__name")
            )
            data = [
                {"site": r["site__name"], "slug": r["site__slug"], "budget": str(r["budget_sum"]) if r["budget_sum"] is not None else "0"}
                for r in rows
            ]
            return Response(data)

        rows = (
            Site.objects.filter(tenant=tenant)
            .values("name", "slug", "budget")
            .order_by("name")
        )
        data = [
            {"site": r["name"], "slug": r["slug"], "budget": str(r["budget"]) if r["budget"] is not None else "0"}
            for r in rows
        ]
        return Response(data)

    # Nested monthly budgets for a single site
    # GET /api/<tenant_slug>/sites/<pk>/budgets/?year=YYYY
    # POST /api/<tenant_slug>/sites/<pk>/budgets/ { year, month, amount }
    @action(detail=True, methods=["get", "post"], url_path="budgets")
    def site_budgets(self, request, pk=None, *args, **kwargs):
        tenant_slug = self.kwargs.get("tenant_slug")
        tenant = get_tenant_by_slug_or_404(tenant_slug)
        site = self.get_queryset().filter(pk=pk).first()
        if not site:
            return Response({"detail": "Site not found"}, status=404)

        if request.method.lower() == "get":
            year = request.query_params.get("year")
            qs = SiteBudget.objects.filter(tenant=tenant, site=site)
            if year:
                qs = qs.filter(year=year)
            data = SiteBudgetSerializer(qs.order_by("year", "month"), many=True).data
            return Response(data)

        # POST -> upsert monthly budget
        serializer = SiteBudgetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data["year"]
        month = serializer.validated_data["month"]
        amount = serializer.validated_data["amount"]
        obj, _created = SiteBudget.objects.update_or_create(
            tenant=tenant, site=site, year=year, month=month,
            defaults={"amount": amount},
        )
        return Response(SiteBudgetSerializer(obj).data, status=201)
