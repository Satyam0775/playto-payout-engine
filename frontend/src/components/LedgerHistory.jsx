import React from 'react'

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

export default function LedgerHistory({ entries }) {
  if (!entries.length) {
    return (
      <div className="text-center text-slate-500 py-16 border border-dashed border-slate-800 rounded-xl">
        No ledger entries yet.
      </div>
    )
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800">
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">Type</th>
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">Amount</th>
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">Description</th>
            <th className="text-left text-xs text-slate-500 uppercase tracking-wider px-4 py-3">Date</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={e.id} className={`border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors ${i % 2 === 0 ? '' : 'bg-slate-800/10'}`}>
              <td className="px-4 py-3">
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                  e.entry_type === 'credit'
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : 'bg-red-500/20 text-red-300'
                }`}>
                  {e.entry_type === 'credit' ? '↑ Credit' : '↓ Debit'}
                </span>
              </td>
              <td className={`px-4 py-3 font-medium ${e.entry_type === 'credit' ? 'text-emerald-400' : 'text-red-400'}`}>
                {e.entry_type === 'credit' ? '+' : '-'}{formatInr(e.amount_paise)}
              </td>
              <td className="px-4 py-3 text-slate-300">{e.description}</td>
              <td className="px-4 py-3 text-slate-400">{formatDate(e.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
