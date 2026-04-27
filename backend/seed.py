#!/usr/bin/env python
"""
Seed script: creates 3 merchants with credit history.
Run: python manage.py shell < seed.py   OR   python seed.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from apps.merchants.models import Merchant
from apps.ledger.models import LedgerEntry

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
            (450000,  'Consulting retainer - March 2025'),
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


def run():
    print('Seeding database...')
    for data in MERCHANTS:
        merchant, created = Merchant.objects.get_or_create(
            email=data['email'],
            defaults={'name': data['name']},
        )
        action = 'Created' if created else 'Found'
        print(f'  {action} merchant: {merchant.name}')

        for amount, description in data['credits']:
            LedgerEntry.objects.get_or_create(
                merchant=merchant,
                description=description,
                defaults={
                    'entry_type': LedgerEntry.CREDIT,
                    'amount_paise': amount,
                },
            )
            print(f'    Credit: {amount} paise - {description}')

    print('Done! Merchants seeded with credit history.')
    print()
    print('Summary:')
    for m in Merchant.objects.all():
        from apps.ledger.services import get_merchant_balance
        bal = get_merchant_balance(m.id)
        print(f'  {m.name}: {bal["available"]} paise available')


if __name__ == '__main__':
    run()
