import React from 'react'

const colorMap = {
  sky:     'bg-sky-500/10 border-sky-500/20 text-sky-400',
  amber:   'bg-amber-500/10 border-amber-500/20 text-amber-400',
  emerald: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
}

function formatInr(paise) {
  if (paise === null || paise === undefined) return '—'
  const rupees = paise / 100
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(rupees)
}

export default function BalanceCard({ label, value, color, description }) {
  const cls = colorMap[color] || colorMap.sky

  return (
    <div className={`rounded-xl border p-5 ${cls}`}>
      <p className="text-xs font-medium uppercase tracking-wider opacity-70 mb-1">{label}</p>
      <p className="text-2xl font-bold">
        {value !== null && value !== undefined ? formatInr(value) : <span className="opacity-40">Loading…</span>}
      </p>
      <p className="text-xs opacity-60 mt-1">{description}</p>
    </div>
  )
}
