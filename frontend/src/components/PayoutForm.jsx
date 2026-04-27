import React, { useState } from 'react'
import { createPayout, generateUUID } from '../api/client'

export default function PayoutForm({ merchantId, onSuccess }) {
  const [amount, setAmount] = useState('')
  const [bankAccount, setBankAccount] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [touched, setTouched] = useState({ amount: false, bankAccount: false })

  const amountValue = parseFloat(amount)
  const amountError = touched.amount && (!amount || isNaN(amountValue) || amountValue <= 0)
  const bankError = touched.bankAccount && !bankAccount.trim()

  const handleSubmit = async (e) => {
    e.preventDefault()
    console.log('FORM SUBMITTED')

    setMessage(null)
    setTouched({ amount: true, bankAccount: true })

    if (!amountValue || amountValue <= 0) {
      setMessage({ type: 'error', text: 'Please enter a valid amount greater than ₹0.' })
      return
    }

    if (!bankAccount.trim()) {
      setMessage({ type: 'error', text: 'Bank account ID is required.' })
      return
    }

    setLoading(true)

    try {
      const amountPaise = Math.round(amountValue * 100)

      // FIX: generate UUID then immediately validate it is a non-empty string.
      // If generateUUID() ever returns undefined (broken import, env issue),
      // fall back to the inline generator so the header is NEVER blank.
      let idempotencyKey = generateUUID()
      if (!idempotencyKey || typeof idempotencyKey !== 'string' || idempotencyKey.trim() === '') {
        idempotencyKey = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
          const r = (Math.random() * 16) | 0
          return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
        })
        console.warn('[PayoutForm] generateUUID() returned invalid value, used fallback:', idempotencyKey)
      }

      console.log('[PayoutForm] Calling createPayout with:', {
        merchantId,
        amountPaise,
        bankAccount: bankAccount.trim(),
        idempotencyKey,
      })

      const res = await createPayout(
        merchantId,
        amountPaise,
        bankAccount.trim(),
        idempotencyKey,
      )

      console.log('[PayoutForm] Response:', res.data)

      setMessage({
        type: 'success',
        text: `Payout of ₹${amountValue.toLocaleString('en-IN')} requested! ID: ${String(res.data.id).slice(0, 8)}… Status: ${res.data.status}`,
      })

      setAmount('')
      setBankAccount('')
      setTouched({ amount: false, bankAccount: false })
      onSuccess?.()
    } catch (err) {
      console.error('[PayoutForm] Error:', err)

      const backendError =
        err.response?.data?.error ||
        err.response?.data?.amount_paise?.[0] ||
        err.response?.data?.bank_account_id?.[0] ||
        err.response?.data?.merchant_id?.[0] ||
        null

      const networkError = !err.response
        ? 'Cannot reach server. Check backend is running and CORS_ALLOW_HEADERS includes "idempotency-key".'
        : null

      const fallback = `Error ${err.response?.status || ''}: Something went wrong.`

      setMessage({
        type: 'error',
        text: backendError || networkError || fallback,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-800 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center">
          <svg className="w-4 h-4 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </div>
        <div>
          <h2 className="text-sm font-semibold text-white leading-tight">Request Payout</h2>
          <p className="text-xs text-slate-500 leading-tight mt-0.5">Funds transfer to your bank account</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <div className="p-6 space-y-5">

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2 tracking-wide uppercase">
              Payout Amount
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 font-medium text-sm select-none pointer-events-none">
                ₹
              </span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                placeholder="0.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                onBlur={() => setTouched((t) => ({ ...t, amount: true }))}
                disabled={loading}
                className={`w-full bg-slate-800 border rounded-xl pl-8 pr-4 py-3 text-white text-sm placeholder-slate-600
                  focus:outline-none focus:ring-2 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed
                  [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none
                  ${amountError
                    ? 'border-red-500/60 focus:ring-red-500/30 bg-red-500/5'
                    : 'border-slate-700 focus:ring-sky-500/40 focus:border-sky-500/60 hover:border-slate-600'
                  }`}
              />
              {amount && !amountError && !isNaN(amountValue) && (
                <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs text-slate-500 pointer-events-none">
                  = {Math.round(amountValue * 100).toLocaleString('en-IN')} paise
                </span>
              )}
            </div>
            {amountError && (
              <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
                <svg className="w-3 h-3 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Enter a valid amount greater than ₹0
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2 tracking-wide uppercase">
              Bank Account ID
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
                </svg>
              </span>
              <input
                type="text"
                placeholder="e.g. HDFC0001234567"
                value={bankAccount}
                onChange={(e) => setBankAccount(e.target.value)}
                onBlur={() => setTouched((t) => ({ ...t, bankAccount: true }))}
                disabled={loading}
                className={`w-full bg-slate-800 border rounded-xl pl-10 pr-4 py-3 text-white text-sm placeholder-slate-600
                  focus:outline-none focus:ring-2 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed font-mono tracking-wide
                  ${bankError
                    ? 'border-red-500/60 focus:ring-red-500/30 bg-red-500/5'
                    : 'border-slate-700 focus:ring-sky-500/40 focus:border-sky-500/60 hover:border-slate-600'
                  }`}
              />
            </div>
            {bankError && (
              <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1">
                <svg className="w-3 h-3 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Bank account ID is required
              </p>
            )}
          </div>

          {message && (
            <div
              className={`flex items-start gap-3 px-4 py-3 rounded-xl text-sm border
                ${message.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300'
                  : 'bg-red-500/10 border-red-500/25 text-red-300'
                }`}
            >
              {message.type === 'success' ? (
                <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              )}
              <span>{message.text}</span>
            </div>
          )}
        </div>

        <div className="px-6 pb-6">
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-sky-600 hover:bg-sky-500 active:bg-sky-700
              disabled:opacity-60 disabled:cursor-not-allowed
              text-white font-semibold text-sm rounded-xl py-3 px-6
              transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:ring-offset-2 focus:ring-offset-slate-900
              flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Requesting Payout…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Request Payout
              </>
            )}
          </button>
          <p className="text-center text-xs text-slate-600 mt-3">
            A unique idempotency key is auto-generated per request
          </p>
        </div>
      </form>
    </div>
  )
}