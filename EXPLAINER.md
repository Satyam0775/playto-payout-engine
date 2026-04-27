# EXPLAINER.md — Playto Payout Engine

---

## 1. The Ledger

**Balance calculation query** (`apps/ledger/services.py`):

```python
result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
    total_credits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.CREDIT)),
    total_debits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.DEBIT)),
)
total_credits = result['total_credits'] or 0
total_debits  = result['total_debits']  or 0
available     = total_credits - total_debits
```

This produces a single SQL query using conditional aggregation:

```sql
SELECT
  SUM(amount_paise) FILTER (WHERE entry_type = 'credit') AS total_credits,
  SUM(amount_paise) FILTER (WHERE entry_type = 'debit')  AS total_debits
FROM ledger_entries
WHERE merchant_id = %s;
```

**Why credits and debits this way:**

The balance is never stored as a column — it is always derived from the ledger at query time. This eliminates an entire class of consistency bugs where the stored balance can drift out of sync with the actual transaction history.

A **DEBIT** entry is written the moment a payout is requested, not when it settles. This means the invariant `available = SUM(credits) - SUM(debits)` holds at every point in time, with no special-casing needed for in-flight payouts.

When a payout **fails**, a **CREDIT** entry is created atomically inside the same transaction as the `FAILED` state transition — the refund and the status change are inseparable. When a payout **succeeds**, no new ledger entry is needed; the debit written at request time is the permanent record.

**Held balance** is informational only: `SUM(debit entries whose linked payout.status IN ['pending', 'processing'])`. It is computed on the same ledger table and shown in the dashboard so merchants can see which funds are currently locked in transit.

---

## 2. The Lock

**Exact code** (`apps/payouts/services.py`):

```python
@transaction.atomic
def create_payout(merchant_id, amount_paise, bank_account_id):
    # Acquire exclusive row-level lock on the merchant
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)

    # Compute balance via DB aggregation — no Python arithmetic on rows
    result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
        total_credits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.CREDIT)),
        total_debits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.DEBIT)),
    )
    available = (result['total_credits'] or 0) - (result['total_debits'] or 0)

    if available < amount_paise:
        raise InsufficientFundsError(...)

    payout = Payout.objects.create(...)
    LedgerEntry.objects.create(entry_type=DEBIT, ...)   # atomic with payout
    return payout
```

**Database primitive:** PostgreSQL row-level exclusive lock via `SELECT ... FOR UPDATE`.

When two concurrent payout requests arrive for the same merchant, both attempt to acquire `SELECT FOR UPDATE` on the merchant row. PostgreSQL serialises them: the second request blocks at that line until the first transaction commits. Once the first commits, the second wakes up, re-reads the ledger (which now includes the first payout's debit), and correctly calculates an insufficient balance.

This is a **database-level** guarantee. Python's GIL only protects a single process's threads. Application-level locks (threading.Lock, Redis locks) break across multiple Gunicorn workers or multiple machines. `SELECT FOR UPDATE` works correctly regardless of how many processes or servers are running.

---

## 3. The Idempotency

**How the system recognises a seen key** (`apps/idempotency/models.py`):

```python
class IdempotencyKey(models.Model):
    merchant        = models.ForeignKey(Merchant, ...)
    key             = models.CharField(max_length=255)
    is_in_flight    = models.BooleanField(default=False)
    response_status = models.IntegerField()
    response_body   = models.JSONField()

    class Meta:
        unique_together = [['merchant', 'key']]
```

A `(merchant, key)` database unique constraint ensures it is physically impossible to create two rows for the same key from the same merchant, even under concurrent requests. Keys expire after 24 hours, enforced at query time: `created_at__gt = now - 24h`.

**Request flow in `PayoutCreateView.post()`:**

1. Query for an existing `IdempotencyKey` row within the 24-hour window.
2. If found and `is_in_flight=False` → first request completed; return the stored `response_body` and `response_status` unchanged.
3. If found and `is_in_flight=True` → first request is still being processed; return 409 Conflict immediately.
4. If not found → call `get_or_create(is_in_flight=True)`. If `created=False`, another request raced past step 1 and created the row first → return 409.
5. Process the payout, then update the key atomically: `is_in_flight=False`, save the full response body and status code.

**What happens if the first request is still in-flight when a second arrives:**

The first request sets `is_in_flight=True` before doing any payout work. The second request hits step 3, sees the `True` flag, and returns 409 without touching the payout table. This prevents duplicate payouts even when the client retries during a slow response.

---

## 4. The State Machine

**Where illegal transitions are blocked** (`apps/payouts/models.py`):

```python
VALID_TRANSITIONS = {
    'pending':    ['processing'],
    'processing': ['completed', 'failed'],
    'completed':  [],      # terminal — nothing allowed
    'failed':     [],      # terminal — nothing allowed
}

def transition_to(self, new_status):
    allowed = self.VALID_TRANSITIONS.get(self.status, [])
    if new_status not in allowed:
        raise ValidationError(
            f'Illegal state transition: {self.status} -> {new_status}. '
            f'Allowed from {self.status}: {allowed}'
        )
    self.status = new_status
```

Every status change in the codebase — whether from the Celery worker, the retry task, or a direct service call — goes through `transition_to()`. There is no other code path that writes to `payout.status`. `completed` and `failed` have an empty allowed list, so any attempt to move out of a terminal state raises `ValidationError` and the transaction rolls back.

**The full async lifecycle:**

1. `POST /api/v1/payouts/` → payout created as `pending`, DEBIT ledger entry written, Celery task dispatched.
2. Celery worker picks it up → transitions to `processing`, records `processing_started_at`.
3. Worker simulates a ~3-second bank settlement delay, then transitions to `completed`.
4. If the worker crashes or the bank hangs, `check_stuck_payouts` (runs every 30 seconds via Celery beat) detects payouts where `processing_started_at < now - 30s` and queues `retry_stuck_payout`.
5. `retry_stuck_payout` applies exponential backoff (`2^retry_count` seconds), resets the payout to `pending`, and re-dispatches the worker. After 3 failed retries the payout transitions to `failed` and a CREDIT refund entry is written in the same transaction.

The refund credit and the `FAILED` state transition always happen inside a single `transaction.atomic()` block — it is impossible to have one without the other.

---

## 5. The AI Audit

**What AI wrote (subtly wrong locking):**

```python
# AI-generated version — WRONG
@transaction.atomic
def create_payout(merchant_id, amount_paise, bank_account_id):
    # AI locked the *payout queryset*, not the merchant row
    existing_payouts = Payout.objects.select_for_update().filter(
        merchant_id=merchant_id,
        status__in=['pending', 'processing']
    )
    held     = existing_payouts.aggregate(total=Sum('amount_paise'))['total'] or 0
    credits  = LedgerEntry.objects.filter(..., entry_type='credit').aggregate(...)['total'] or 0
    debits   = LedgerEntry.objects.filter(..., entry_type='debit').aggregate(...)['total'] or 0
    available = credits - debits - held

    if available < amount_paise:
        raise InsufficientFundsError(...)
    ...
```

**What I caught:**

`SELECT FOR UPDATE` on the payout table only locks rows that **already exist**. When two requests arrive simultaneously, neither payout row exists yet. Both transactions read zero existing rows, both lock nothing, both compute `held = 0`, both compute `available = 10000`, both pass the balance check, and both insert a new payout — overdraft achieved.

The lock must be on a **pre-existing shared resource** that all concurrent requests for the same merchant must acquire before proceeding. The Merchant row is that resource: it always exists, it is unique per merchant, and locking it forces all concurrent requests into a strict serial queue at the database level.

**What I replaced it with:**

```python
# Correct version
merchant = Merchant.objects.select_for_update().get(id=merchant_id)
```

`SELECT FOR UPDATE` on the merchant row means: the second request cannot read past this line until the first transaction commits. By the time the second request acquires the lock and aggregates the ledger, the first transaction's DEBIT entry is already committed and visible. The second request correctly sees insufficient funds and raises `InsufficientFundsError`. No overdraft, no race condition, zero Python-level coordination needed.