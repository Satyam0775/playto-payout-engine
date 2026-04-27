import React from 'react'

const STATUS_STYLES = {
  pending:    'bg-slate-700 text-slate-300',
  processing: 'bg-amber-500/20 text-amber-300',
  completed:  'bg-emerald-500/20 text-emerald-300',
  failed:     'bg-red-500/20 text-red-300',
}

function formatInr(paise) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 2,
  }).format(paise / 100)
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function PayoutHistory({ payouts }) {
  if (!payouts.length) {
    return (
      <div className="text-center text-slate-500 py-16 border border-dashed border-slate-800 rounded-xl">
        No payouts yet. Request your first payout above.
      </div>
    )
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800">
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">ID</th>
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">Amount</th>
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">Bank Account</th>
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">Status</th>
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">Retries</th>
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">Created</th>
          </tr>
        </thead>
        <tbody>
          {payouts.map((p, i) => (
            <tr key={p.id} className={`border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors ${i % 2 === 0 ? '' : 'bg-slate-800/10'}`}>
              <td className="px-4 py-3 font-mono text-slate-400 text-xs">{p.id?.slice(0, 8)}…</td>
              <td className="px-4 py-3 font-medium text-white">{formatInr(p.amount_paise)}</td>
              <td className="px-4 py-3 text-slate-300 font-mono text-xs">{p.bank_account_id}</td>
              <td className="px-4 py-3">
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${STATUS_STYLES[p.status] || ''}`}>
                  {p.status === 'processing' && <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse inline-block" />}
                  {p.status === 'pending' && <span className="w-1.5 h-1.5 rounded-full bg-slate-400 inline-block" />}
                  {p.status === 'completed' && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />}
                  {p.status === 'failed' && <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />}
                  {p.status}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-400">{p.retry_count}</td>
              <td className="px-4 py-3 text-slate-400">{formatDate(p.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
