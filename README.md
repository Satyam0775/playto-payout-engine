# Playto Payout Engine

Cross-border payout engine for Indian merchants. Merchants accumulate balance from international customer payments and withdraw to Indian bank accounts.

## Stack
- **Backend**: Django 4.2 + DRF + PostgreSQL
- **Jobs**: Celery + Redis (real async, no fake sync)
- **Frontend**: React 18 + Tailwind CSS + Vite

---

## Quick Start (Docker Compose — recommended)

Docker Compose is the primary way to run this project. It starts all services automatically: PostgreSQL, Redis, Django backend, Celery worker, Celery beat scheduler, and the React frontend.

```bash
# Clone and start everything
docker-compose up --build

# The backend seed script runs automatically on first start.
# Celery worker and beat scheduler also start automatically — no manual steps needed.

# Open dashboard: http://localhost:5174
# Backend API:    http://localhost:8001/api/v1/
```

> The Celery worker automatically processes payouts in the background. No manual worker setup is needed in Docker mode.

---

## How it Works (Flow)

```
User submits payout request
        ↓
POST /api/v1/payouts/ (with Idempotency-Key header)
        ↓
Django validates request + checks available balance
        ↓
Payout record created in DB (status: pending) + funds held via ledger DEBIT
        ↓
Celery task dispatched to background worker
        ↓
Worker transitions payout to processing → simulates bank settlement (~3s delay)
        ↓
Payout marked completed → React dashboard polls and reflects updated status
```

---

## Manual Setup

### Prerequisites
- Python 3.11+, Node 18+, PostgreSQL 15, Redis 7

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Create a .env file (copy from .env.example)
cp .env.example .env
# Edit .env with your DB and Redis credentials

# Run migrations
python manage.py migrate

# Seed merchants with credit history
python seed.py

# Start Django dev server
python manage.py runserver 8001

# In a separate terminal — start Celery worker
celery -A project worker --loglevel=info

# In another terminal — start Celery beat (periodic tasks)
celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Frontend

```bash
cd frontend
npm install
# Create .env.local
echo "VITE_API_URL=http://localhost:8001" > .env.local
npm run dev
# Open http://localhost:5174
```

---

## API Reference

### Merchants
```
GET  /api/v1/merchants/                          List all merchants
GET  /api/v1/merchants/{id}/balance/             Get balance (available + held)
GET  /api/v1/merchants/{id}/payouts/             List merchant payouts
GET  /api/v1/merchants/{id}/ledger/              List ledger entries
```

### Payouts
```
POST /api/v1/payouts/                            Create payout (requires Idempotency-Key header)
GET  /api/v1/payouts/{id}/                       Get payout status
```

> **Important:** Every POST `/api/v1/payouts/` request **must** include an `Idempotency-Key` header containing a valid UUID. Requests without this header will be rejected with HTTP 400. Sending the same key twice returns the original response with no duplicate payout created.

#### POST /api/v1/payouts/ Example
```bash
curl -X POST http://localhost:8001/api/v1/payouts/ \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "merchant_id": "<merchant-uuid>",
    "amount_paise": 50000,
    "bank_account_id": "HDFC0001234567"
  }'
```

---

## Payout Lifecycle

Payouts are processed **asynchronously** by a Celery worker that simulates real bank settlement. This simulates real bank processing using background workers with delay. The full state flow is:

```
pending → processing → completed
pending → processing → failed  (funds automatically refunded to merchant balance)
```

- **Pending**: payout created, funds held immediately
- **Processing**: Celery worker has picked up the payout and is simulating bank settlement
- **Completed**: settlement confirmed, funds permanently debited
- **Failed**: bank rejected the payout; a refund credit entry is created atomically in the same transaction

**Retry logic**: payouts stuck in `processing` for more than 30 seconds are automatically retried with exponential backoff (up to 3 attempts). After 3 failures the payout is marked `failed` and funds are refunded.

---

## Running Tests

```bash
cd backend
python manage.py test tests
```

Tests cover:
- `test_concurrency.py` — Two simultaneous 60-rupee requests on 100-rupee balance; exactly one succeeds
- `test_idempotency.py` — Same Idempotency-Key returns identical response, no duplicate created

---

## Key Features

- **Async payout processing** — Celery worker handles all payout state transitions in the background
- **Idempotent API** — safe to retry; duplicate requests return the original response, never create duplicate payouts
- **Ledger-based balance system** — balance is always derived from credits minus debits, never stored directly
- **Retry handling for stuck payouts** — exponential backoff with automatic failure and refund after 3 attempts
- **Dockerized full system** — single `docker-compose up --build` starts every service

---

## Architecture Decisions

See `EXPLAINER.md` for detailed answers to the 5 grading questions.

### Money model
All amounts are stored as `BigIntegerField` in paise. No floats, no Decimal. Balance is **never stored** — always computed via a single DB aggregation query.

### Concurrency
`SELECT FOR UPDATE` on the Merchant row serialises concurrent payout requests at the database level.

### Ledger model
- **CREDIT**: created for incoming customer payments OR failed-payout refunds
- **DEBIT**: created atomically with a new payout request
- `available_balance = SUM(credits) - SUM(debits)`
- `held_balance = debits whose linked payout is still PENDING/PROCESSING`

### State machine
`Payout.transition_to(new_status)` is the single enforcement point. Raises `ValidationError` on illegal transitions.
