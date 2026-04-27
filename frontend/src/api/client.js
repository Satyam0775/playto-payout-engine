// ---------------- IMPORTS ----------------
import axios from 'axios'


// ---------------- BASE URL (DOMAIN SETUP) ----------------

// Use env if available, else fallback to local backend
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001'


// ---------------- AXIOS CLIENT ----------------

const client = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})


// ---------------- UUID GENERATOR ----------------

export function generateUUID() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  // fallback UUID generator
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}


// ---------------- GET APIs ----------------

// Get all merchants
export const fetchMerchants = () => client.get('/merchants/')

// Get merchant balance
export const fetchBalance = (merchantId) =>
  client.get(`/merchants/${merchantId}/balance/`)

// Get payouts list
export const fetchPayouts = (merchantId) =>
  client.get(`/merchants/${merchantId}/payouts/`)

// Get ledger entries
export const fetchLedger = (merchantId) =>
  client.get(`/merchants/${merchantId}/ledger/`)

// Get single payout
export const fetchPayout = (payoutId) =>
  client.get(`/payouts/${payoutId}/`)


// ---------------- POST API (FINAL FIXED) ----------------

// Create payout
export const createPayout = (
  merchantId,
  amountPaise,
  bankAccountId,
  idempotencyKey
) =>
  client.post(
    '/payouts/',
    {
      merchant_id: merchantId,
      amount_paise: amountPaise,
      bank_account_id: bankAccountId,
    },
    {
      headers: {
        // ALWAYS send valid UUID (critical for backend)
        'Idempotency-Key': idempotencyKey || generateUUID(),
      },
    }
  )


// ---------------- EXPORT ----------------

export default client