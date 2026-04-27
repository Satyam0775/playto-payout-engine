from django.core.management.base import BaseCommand
from apps.merchants.models import Merchant
from apps.ledger.models import LedgerEntry
from apps.ledger.services import get_merchant_balance


MERCHANTS = [
    {
        'name': 'Ravi Designs Studio',
        'email': 'ravi@designs.io',
        'credits': [
            (500000, 'Payment from Acme Corp - Invoice #1001'),
            (300000, 'Payment from GlobalTech - Invoice #1002'),
            (200000, 'Payment from StartupXYZ - Invoice #1003'),
        ],
    },
    {
        'name': 'Priya Freelance Dev',
        'email': 'priya@freelance.dev',
        'credits': [
            (1000000, 'Project payment - Frontend build'),
            (450000, 'Consulting retainer - March 2025'),
        ],
    },
    {
        'name': 'Arjun Marketing Co',
        'email': 'arjun@marketingco.in',
        'credits': [
            (750000, 'Campaign management - Q1 2025'),
            (250000, 'SEO package - Client A'),
            (125000, 'Social media audit - Client B'),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed initial merchants and credit ledger entries"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Seeding database..."))

        for data in MERCHANTS:
            merchant, created = Merchant.objects.get_or_create(
                email=data['email'],
                defaults={'name': data['name']},
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created merchant: {merchant.name}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Found merchant: {merchant.name}"))

            for amount, description in data['credits']:
                entry, created_entry = LedgerEntry.objects.get_or_create(
                    merchant=merchant,
                    description=description,
                    defaults={
                        'entry_type': LedgerEntry.CREDIT,
                        'amount_paise': amount,
                    },
                )

                if created_entry:
                    self.stdout.write(f"  Credit added: {amount} paise - {description}")
                else:
                    self.stdout.write(f"  Already exists: {description}")

        self.stdout.write(self.style.SUCCESS("\nSeeding completed!\n"))

        self.stdout.write(self.style.WARNING("Summary:"))
        for m in Merchant.objects.all():
            bal = get_merchant_balance(m.id)
            self.stdout.write(f"{m.name}: {bal['available']} paise available")
