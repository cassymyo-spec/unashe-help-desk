from __future__ import annotations

import random
from datetime import datetime

from django.core.management.base import BaseCommand, CommandParser
from django.contrib.auth import get_user_model
from django.db import transaction

from tenants.models import Tenant, Site, SiteBudget
from tickets.models import Ticket

User = get_user_model()

STATUSES = [s for s, _ in Ticket.Status.choices]
PRIORITIES = [p for p, _ in Ticket.Priority.choices]


class Command(BaseCommand):
    help = "Seed dummy data: tenants, sites, users, tickets, and monthly budgets"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--tenant", type=str, default="acme", help="Tenant slug to seed into (created if missing)")
        parser.add_argument("--tenant-name", type=str, default="Acme Corp", help="Tenant display name")
        parser.add_argument("--sites", type=int, default=3, help="How many sites to create")
        parser.add_argument("--managers", type=int, default=2, help="How many site managers to create")
        parser.add_argument("--contractors", type=int, default=5, help="How many contractors to create")
        parser.add_argument("--tickets", type=int, default=30, help="How many tickets to create")
        parser.add_argument("--admin-email", type=str, default="admin@acme.com", help="Admin email (created if missing)")
        parser.add_argument("--admin-username", type=str, default="admin", help="Admin username")
        parser.add_argument("--admin-password", type=str, default="admin123", help="Admin password if creating")
        parser.add_argument("--year", type=int, default=datetime.now().year, help="Year for monthly budgets")

    @transaction.atomic
    def handle(self, *args, **opts):
        tenant_slug: str = opts["tenant"]
        tenant_name: str = opts["tenant_name"]
        site_count: int = opts["sites"]
        manager_count: int = opts["managers"]
        contractor_count: int = opts["contractors"]
        ticket_count: int = opts["tickets"]
        admin_email: str = opts["admin_email"]
        admin_username: str = opts["admin_username"]
        admin_password: str = opts["admin_password"]
        year: int = opts["year"]

        tenant, _ = Tenant.objects.get_or_create(slug=tenant_slug, defaults={"name": tenant_name})
        self.stdout.write(self.style.SUCCESS(f"Tenant: {tenant.slug}"))

        # Admin user
        admin_user, created_admin = User.objects.get_or_create(
            username=admin_username,
            defaults={
                "email": admin_email,
                "role": "ADMIN",
                "tenant": tenant,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created_admin:
            admin_user.set_password(admin_password)
            admin_user.save()
        else:
            # ensure tenant and role are correct if user existed
            update_fields = []
            if admin_user.tenant_id != tenant.id:
                admin_user.tenant = tenant
                update_fields.append("tenant")
            if admin_user.role != "ADMIN":
                admin_user.role = "ADMIN"
                update_fields.append("role")
            if update_fields:
                admin_user.save(update_fields=update_fields)
        self.stdout.write(self.style.SUCCESS(f"Admin: {admin_user.username}"))

        # Sites
        sites: list[Site] = []
        for i in range(site_count):
            slug = f"site-{i+1}"
            site, _ = Site.objects.get_or_create(
                tenant=tenant,
                slug=slug,
                defaults={
                    "name": f"Site {i+1}",
                    "budget": random.randint(50_000, 200_000),
                },
            )
            sites.append(site)
        self.stdout.write(self.style.SUCCESS(f"Sites: {len(sites)}"))

        # Site monthly budgets (simple ramp)
        for site in sites:
            for month in range(1, 13):
                amount = random.randint(5_000, 20_000)
                SiteBudget.objects.update_or_create(
                    tenant=tenant, site=site, year=year, month=month, defaults={"amount": amount}
                )
        self.stdout.write(self.style.SUCCESS("Monthly budgets created/updated"))

        # Managers
        managers: list[User] = []
        for i in range(manager_count):
            username = f"manager{i+1}"
            email = f"manager{i+1}@{tenant.slug}.com"
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "role": "SITE_MANAGER",
                    "tenant": tenant,
                },
            )
            if created:
                u.set_password("password123")
                u.save()
            # assign to random site
            u.site = random.choice(sites) if sites else None
            u.save(update_fields=["site"]) if u.site_id else None
            managers.append(u)
        self.stdout.write(self.style.SUCCESS(f"Managers: {len(managers)}"))

        # Contractors
        contractors: list[User] = []
        for i in range(contractor_count):
            username = f"contractor{i+1}"
            email = f"contractor{i+1}@{tenant.slug}.com"
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "role": "CONTRACTOR",
                    "tenant": tenant,
                },
            )
            if created:
                u.set_password("password123")
                u.save()
            # optionally attach to site
            if sites and random.random() < 0.7:
                u.site = random.choice(sites)
                u.save(update_fields=["site"])
            contractors.append(u)
        self.stdout.write(self.style.SUCCESS(f"Contractors: {len(contractors)}"))

        # Tickets
        authors = managers + contractors
        if not authors:
            authors = [admin_user]
        for i in range(ticket_count):
            site = random.choice(sites) if sites else None
            created_by = random.choice(authors)
            assignee = random.choice(contractors) if contractors and random.random() < 0.6 else None
            Ticket.objects.create(
                title=f"Ticket {i+1}",
                description=f"Auto-generated ticket {i+1} for tenant {tenant.slug}",
                status=random.choice(STATUSES),
                priority=random.choice(PRIORITIES),
                tenant=tenant,
                created_by=created_by,
                assignee=assignee,
                site=site,
            )
        self.stdout.write(self.style.SUCCESS(f"Tickets: {ticket_count}"))

        self.stdout.write(self.style.SUCCESS("Seeding complete."))
