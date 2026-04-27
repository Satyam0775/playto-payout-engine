import React, { useState, useEffect } from 'react'
import { fetchMerchants } from './api/client'
import Dashboard from './pages/Dashboard'

export default function App() {
  const [merchants, setMerchants] = useState([])
  const [selectedMerchant, setSelectedMerchant] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMerchants()
      .then(res => {
        setMerchants(res.data)
        if (res.data.length > 0) setSelectedMerchant(res.data[0])
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-slate-300 text-lg animate-pulse">Loading Playto Pay...</div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center font-bold text-white text-sm">P</div>
            <span className="font-semibold text-white text-lg">Playto Pay</span>
            <span className="text-slate-500 text-sm">Payout Engine</span>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-slate-400 text-sm">Merchant:</label>
            <select
              className="bg-slate-800 border border-slate-700 text-white rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              value={selectedMerchant?.id || ''}
              onChange={e => setSelectedMerchant(merchants.find(m => m.id === e.target.value))}
            >
              {merchants.map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {selectedMerchant ? (
        <Dashboard merchant={selectedMerchant} />
      ) : (
        <div className="text-center text-slate-400 py-20">No merchants found. Run the seed script.</div>
      )}
    </div>
  )
}
