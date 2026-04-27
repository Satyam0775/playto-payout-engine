import React, { useState, useEffect, useCallback } from 'react'
import BalanceCard from '../components/BalanceCard'
import PayoutForm from '../components/PayoutForm'
import PayoutHistory from '../components/PayoutHistory'
import LedgerHistory from '../components/LedgerHistory'
import { fetchBalance, fetchPayouts, fetchLedger } from '../api/client'

export default function Dashboard({ merchant }) {
  const [balance, setBalance] = useState(null)
  const [payouts, setPayouts] = useState([])
  const [ledger, setLedger] = useState([])
  const [activeTab, setActiveTab] = useState('payouts')
  const [refreshKey, setRefreshKey] = useState(0)

  const loadData = useCallback(async () => {
    try {
      const [balRes, payRes, ledRes] = await Promise.all([
        fetchBalance(merchant.id),
        fetchPayouts(merchant.id),
        fetchLedger(merchant.id),
      ])
      setBalance(balRes.data)
      setPayouts(payRes.data)
      setLedger(ledRes.data)
    } catch (err) {
      console.error('Failed to load data:', err)
    }
  }, [merchant.id])

  useEffect(() => {
    loadData()
  }, [loadData, refreshKey])

  // Poll for live status updates every 3 seconds
  useEffect(() => {
    const interval = setInterval(loadData, 3000)
    return () => clearInterval(interval)
  }, [loadData])

  const handlePayoutSuccess = () => {
    setTimeout(() => setRefreshKey(k => k + 1), 500)
  }

  return (
    <main className="max-w-7xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">{merchant.name}</h1>
        <p className="text-slate-400 text-sm mt-1">{merchant.email}</p>
      </div>

      {/* Balance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <BalanceCard
          label="Available Balance"
          value={balance?.available_balance_paise}
          color="sky"
          description="Ready to withdraw"
        />
        <BalanceCard
          label="Held Balance"
          value={balance?.held_balance_paise}
          color="amber"
          description="Pending / Processing payouts"
        />
        <BalanceCard
          label="Total Credits"
          value={balance?.total_credits_paise}
          color="emerald"
          description="All-time incoming payments"
        />
      </div>

      {/* Payout Form */}
      <div className="mb-8">
        <PayoutForm merchantId={merchant.id} onSuccess={handlePayoutSuccess} />
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800 mb-6">
        <div className="flex gap-6">
          {['payouts', 'ledger'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-medium capitalize border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-sky-500 text-sky-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab === 'payouts' ? `Payouts (${payouts.length})` : `Ledger (${ledger.length})`}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'payouts' ? (
        <PayoutHistory payouts={payouts} />
      ) : (
        <LedgerHistory entries={ledger} />
      )}
    </main>
  )
}
