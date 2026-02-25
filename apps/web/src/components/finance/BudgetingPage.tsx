'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  DollarSign,
  CreditCard,
  PiggyBank,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Receipt,
  Target,
  Landmark,
  BarChart3,
  PieChart,
  Loader2,
  ExternalLink,
  Info,
  ChevronRight,
  Search,
  Filter,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useTranslation } from '@/lib/i18n';
import { toast } from 'sonner';

// ── Types ──────────────────────────────────────────────────────────────────

interface Account {
  id: string;
  name: string;
  type: string;
  subtype: string;
  mask: string;
  current: number;
  available: number | null;
  currency: string;
}

interface SpendingCategory {
  name: string;
  amount: number;
  pct: number;
}

interface SpendingBreakdown {
  total_spent: number;
  total_income: number;
  net: number;
  categories: SpendingCategory[];
  period_days: number;
  transaction_count: number;
}

interface Transaction {
  id: string;
  name: string;
  merchant: string | null;
  amount: number;
  date: string;
  category: string;
  pending: boolean;
}

interface Budget {
  category: string;
  limit: number;
  spent: number;
  pct: number;
}

interface FinanceOverview {
  accounts: Account[];
  total_current: number;
  total_available: number;
  spending: SpendingBreakdown;
  transactions: Transaction[];
  budgets: Budget[];
  is_demo: boolean;
}

interface FinanceStatus {
  connected: boolean;
  account_count: number;
  last_sync: string | null;
}

// ── Helpers ────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

const CATEGORY_META: Record<string, { label: string; color: string; icon: typeof DollarSign }> = {
  FOOD_AND_DRINK:     { label: 'Food & Drink',      color: '#f97316', icon: Receipt },
  RENT_AND_UTILITIES: { label: 'Rent & Utilities',   color: '#8b5cf6', icon: Landmark },
  TRANSPORTATION:     { label: 'Transportation',     color: '#3b82f6', icon: TrendingUp },
  ENTERTAINMENT:      { label: 'Entertainment',      color: '#ec4899', icon: PieChart },
  SHOPPING:           { label: 'Shopping',            color: '#10b981', icon: CreditCard },
  GENERAL_SERVICES:   { label: 'Services',            color: '#6366f1', icon: Target },
  TRANSFER_OUT:       { label: 'Transfers',           color: '#64748b', icon: ArrowUpRight },
};

const catMeta = (cat: string) =>
  CATEGORY_META[cat] ?? { label: cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), color: '#94a3b8', icon: DollarSign };

// ── Component ──────────────────────────────────────────────────────────────

export function BudgetingPage() {
  const [data, setData] = useState<FinanceOverview | null>(null);
  const [status, setStatus] = useState<FinanceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions' | 'budgets'>('overview');
  const [txSearch, setTxSearch] = useState('');
  const [editingBudget, setEditingBudget] = useState<string | null>(null);
  const [budgetInput, setBudgetInput] = useState('');
  const [savingBudget, setSavingBudget] = useState(false);
  const [linkLoading, setLinkLoading] = useState(false);
  const { t } = useTranslation();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [overview, finStatus] = await Promise.all([
        api.get<FinanceOverview>('/api/finance/overview'),
        api.get<FinanceStatus>('/api/finance/status'),
      ]);
      setData(overview);
      setStatus(finStatus);
    } catch {
      // Will show empty state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Plaid Link — opens Plaid Link drop-in widget via CDN
  const handleConnectBank = useCallback(async () => {
    setLinkLoading(true);
    try {
      const { link_token } = await api.get<{ link_token: string }>('/api/finance/plaid/link-token');
      if (!link_token) {
        toast.error('Plaid not configured. Set PLAID_CLIENT_ID and PLAID_SECRET in your .env');
        return;
      }

      // Load Plaid Link SDK dynamically
      const existingScript = document.getElementById('plaid-link-sdk');
      const loadScript = (): Promise<void> =>
        new Promise((resolve, reject) => {
          if (existingScript && (window as any).Plaid) { resolve(); return; }
          const script = document.createElement('script');
          script.id = 'plaid-link-sdk';
          script.src = 'https://cdn.plaid.com/link/v2/stable/link-initialize.js';
          script.onload = () => resolve();
          script.onerror = () => reject(new Error('Failed to load Plaid SDK'));
          document.head.appendChild(script);
        });

      await loadScript();

      const Plaid = (window as any).Plaid;
      if (!Plaid) { toast.error('Plaid SDK failed to load'); return; }

      const handler = Plaid.create({
        token: link_token,
        onSuccess: async (publicToken: string, metadata: any) => {
          try {
            await api.post('/api/finance/plaid/exchange', {
              public_token: publicToken,
              institution_name: metadata?.institution?.name ?? 'Bank',
            });
            toast.success('Bank account connected!');
            fetchData();
          } catch {
            toast.error('Failed to link account');
          }
        },
        onExit: (err: any) => {
          if (err) toast.error('Plaid Link exited with error');
        },
      });
      handler.open();
    } catch {
      toast.error('Could not start Plaid Link — check API configuration');
    } finally {
      setLinkLoading(false);
    }
  }, [fetchData]);

  const handleSaveBudget = async (category: string) => {
    const limit = parseFloat(budgetInput);
    if (isNaN(limit) || limit <= 0) return;
    setSavingBudget(true);
    try {
      await api.post('/api/finance/budgets', { category, limit });
      await fetchData();
      setEditingBudget(null);
      setBudgetInput('');
    } catch {
      // ignore
    } finally {
      setSavingBudget(false);
    }
  };

  // ── Loading ────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
          <p className="text-sm text-zinc-500">Loading finance data...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center px-6">
          <Wallet className="w-12 h-12 text-zinc-600" />
          <h2 className="text-lg font-semibold text-white">Finance Unavailable</h2>
          <p className="text-sm text-zinc-400 max-w-md">
            Could not load finance data. Check your connection and try again.
          </p>
          <button
            onClick={fetchData}
            className="mt-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const filteredTx = data.transactions.filter(tx => {
    if (!txSearch) return true;
    const q = txSearch.toLowerCase();
    return (
      tx.name.toLowerCase().includes(q) ||
      (tx.merchant?.toLowerCase().includes(q)) ||
      tx.category.toLowerCase().includes(q)
    );
  });

  const tabs = [
    { id: 'overview' as const, label: 'Overview', icon: BarChart3 },
    { id: 'transactions' as const, label: 'Transactions', icon: Receipt },
    { id: 'budgets' as const, label: 'Budgets', icon: Target },
  ];

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 md:px-8 py-6 space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Wallet className="w-7 h-7 text-brand-400" />
              Finance & Budgeting
            </h1>
            <p className="text-sm text-zinc-400 mt-1">
              {status?.connected
                ? `Connected · ${status.account_count} account${status.account_count !== 1 ? 's' : ''}`
                : 'Using demo data — connect Plaid in Settings to see real data'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {data.is_demo && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 text-xs font-medium border border-amber-500/20">
                <Info className="w-3.5 h-3.5" />
                Demo Mode
              </span>
            )}
            {data.is_demo && (
              <button
                onClick={handleConnectBank}
                disabled={linkLoading}
                className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {linkLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Landmark className="w-4 h-4" />}
                Connect Bank
              </button>
            )}
            <button
              onClick={fetchData}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <SummaryCard
            label="Total Balance"
            value={fmt(data.total_current)}
            icon={Wallet}
            color="brand"
          />
          <SummaryCard
            label="Available"
            value={fmt(data.total_available)}
            icon={DollarSign}
            color="emerald"
          />
          <SummaryCard
            label="Monthly Spending"
            value={fmt(data.spending.total_spent)}
            icon={TrendingDown}
            color="rose"
            sub={`${data.spending.transaction_count} transactions`}
          />
          <SummaryCard
            label="Net Cash Flow"
            value={fmt(data.spending.net)}
            icon={data.spending.net >= 0 ? TrendingUp : TrendingDown}
            color={data.spending.net >= 0 ? 'emerald' : 'rose'}
            sub={`${fmt(data.spending.total_income)} income`}
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-white/5 rounded-xl p-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-brand-600 text-white shadow-lg'
                  : 'text-zinc-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="space-y-6"
            >
              {/* Accounts */}
              <Section title="Accounts" icon={Landmark}>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {data.accounts.map(acc => (
                    <div
                      key={acc.id}
                      className="p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:border-white/10 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          {acc.type === 'depository' ? (
                            <PiggyBank className="w-5 h-5 text-emerald-400" />
                          ) : (
                            <CreditCard className="w-5 h-5 text-rose-400" />
                          )}
                          <span className="text-sm font-medium text-white">{acc.name}</span>
                        </div>
                        <span className="text-xs text-zinc-500">····{acc.mask}</span>
                      </div>
                      <p className="text-xl font-bold text-white">{fmt(acc.current)}</p>
                      {acc.available !== null && (
                        <p className="text-xs text-zinc-500 mt-1">
                          {fmt(acc.available)} available
                        </p>
                      )}
                      <span className="inline-block mt-2 text-[10px] uppercase tracking-wider text-zinc-600 font-medium">
                        {acc.subtype}
                      </span>
                    </div>
                  ))}
                </div>
              </Section>

              {/* Spending Breakdown */}
              <Section title="Spending Breakdown" icon={PieChart} sub={`Last ${data.spending.period_days} days`}>
                <div className="space-y-3">
                  {data.spending.categories.map(cat => {
                    const meta = catMeta(cat.name);
                    return (
                      <div key={cat.name} className="group">
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <meta.icon className="w-4 h-4" style={{ color: meta.color }} />
                            <span className="text-sm text-zinc-300">{meta.label}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-zinc-500">{cat.pct}%</span>
                            <span className="text-sm font-medium text-white">{fmt(cat.amount)}</span>
                          </div>
                        </div>
                        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                          <motion.div
                            className="h-full rounded-full"
                            style={{ backgroundColor: meta.color }}
                            initial={{ width: 0 }}
                            animate={{ width: `${cat.pct}%` }}
                            transition={{ duration: 0.8, ease: 'easeOut' }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Section>

              {/* Recent Transactions (top 5) */}
              <Section title="Recent Transactions" icon={Receipt}>
                <div className="space-y-1">
                  {data.transactions.slice(0, 5).map(tx => (
                    <TransactionRow key={tx.id} tx={tx} />
                  ))}
                </div>
                {data.transactions.length > 5 && (
                  <button
                    onClick={() => setActiveTab('transactions')}
                    className="mt-3 text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1 transition-colors"
                  >
                    View all transactions <ChevronRight className="w-4 h-4" />
                  </button>
                )}
              </Section>
            </motion.div>
          )}

          {activeTab === 'transactions' && (
            <motion.div
              key="transactions"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="space-y-4"
            >
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                <input
                  value={txSearch}
                  onChange={e => setTxSearch(e.target.value)}
                  placeholder="Search transactions..."
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/30 transition-all"
                />
              </div>

              <div className="rounded-xl bg-white/[0.02] border border-white/5 overflow-hidden divide-y divide-white/5">
                {filteredTx.length === 0 ? (
                  <div className="p-8 text-center text-zinc-500 text-sm">No transactions found</div>
                ) : (
                  filteredTx.map(tx => <TransactionRow key={tx.id} tx={tx} />)
                )}
              </div>
            </motion.div>
          )}

          {activeTab === 'budgets' && (
            <motion.div
              key="budgets"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="space-y-4"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.budgets.map(b => {
                  const meta = catMeta(b.category);
                  const isOver = b.pct >= 100;
                  const isWarning = b.pct >= 80 && b.pct < 100;
                  const isEditing = editingBudget === b.category;

                  return (
                    <div
                      key={b.category}
                      className={`p-5 rounded-xl border transition-all ${
                        isOver
                          ? 'bg-rose-500/5 border-rose-500/20'
                          : isWarning
                          ? 'bg-amber-500/5 border-amber-500/20'
                          : 'bg-white/[0.03] border-white/5 hover:border-white/10'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center"
                            style={{ backgroundColor: `${meta.color}20` }}
                          >
                            <meta.icon className="w-4 h-4" style={{ color: meta.color }} />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">{meta.label}</p>
                            <p className="text-xs text-zinc-500">
                              {fmt(b.spent)} of {fmt(b.limit)}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {isOver ? (
                            <AlertCircle className="w-5 h-5 text-rose-400" />
                          ) : isWarning ? (
                            <AlertCircle className="w-5 h-5 text-amber-400" />
                          ) : (
                            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                          )}
                          <span
                            className={`text-lg font-bold ${
                              isOver ? 'text-rose-400' : isWarning ? 'text-amber-400' : 'text-emerald-400'
                            }`}
                          >
                            {b.pct.toFixed(0)}%
                          </span>
                        </div>
                      </div>

                      {/* Progress bar */}
                      <div className="h-3 rounded-full bg-white/5 overflow-hidden mb-3">
                        <motion.div
                          className="h-full rounded-full"
                          style={{
                            backgroundColor: isOver
                              ? '#f43f5e'
                              : isWarning
                              ? '#f59e0b'
                              : meta.color,
                          }}
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.min(b.pct, 100)}%` }}
                          transition={{ duration: 0.8, ease: 'easeOut' }}
                        />
                      </div>

                      {/* Remaining or over */}
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-zinc-500">
                          {isOver
                            ? `${fmt(b.spent - b.limit)} over budget`
                            : `${fmt(b.limit - b.spent)} remaining`}
                        </span>
                        {isEditing ? (
                          <div className="flex items-center gap-2">
                            <input
                              type="number"
                              value={budgetInput}
                              onChange={e => setBudgetInput(e.target.value)}
                              placeholder="New limit"
                              className="w-24 px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-xs text-white focus:outline-none focus:border-brand-500/50"
                              autoFocus
                              onKeyDown={e => e.key === 'Enter' && handleSaveBudget(b.category)}
                            />
                            <button
                              onClick={() => handleSaveBudget(b.category)}
                              disabled={savingBudget}
                              className="px-2 py-1 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition-colors disabled:opacity-50"
                            >
                              {savingBudget ? '...' : 'Save'}
                            </button>
                            <button
                              onClick={() => { setEditingBudget(null); setBudgetInput(''); }}
                              className="px-2 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-400 text-xs transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => { setEditingBudget(b.category); setBudgetInput(String(b.limit)); }}
                            className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
                          >
                            Edit limit
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* All spending categories without explicit budgets */}
              {data.spending.categories.filter(c => !data.budgets.find(b => b.category === c.name)).length > 0 && (
                <Section title="Unbudgeted Categories" icon={BarChart3}>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {data.spending.categories
                      .filter(c => !data.budgets.find(b => b.category === c.name))
                      .map(cat => {
                        const meta = catMeta(cat.name);
                        return (
                          <div
                            key={cat.name}
                            className="flex items-center justify-between p-3 rounded-xl bg-white/[0.03] border border-white/5"
                          >
                            <div className="flex items-center gap-2">
                              <meta.icon className="w-4 h-4" style={{ color: meta.color }} />
                              <span className="text-sm text-zinc-300">{meta.label}</span>
                            </div>
                            <span className="text-sm font-medium text-white">{fmt(cat.amount)}</span>
                          </div>
                        );
                      })}
                  </div>
                </Section>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  icon: Icon,
  color,
  sub,
}: {
  label: string;
  value: string;
  icon: typeof DollarSign;
  color: string;
  sub?: string;
}) {
  const colorMap: Record<string, string> = {
    brand: 'from-brand-500/20 to-brand-600/5 text-brand-400',
    emerald: 'from-emerald-500/20 to-emerald-600/5 text-emerald-400',
    rose: 'from-rose-500/20 to-rose-600/5 text-rose-400',
    amber: 'from-amber-500/20 to-amber-600/5 text-amber-400',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:border-white/10 transition-colors"
    >
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${colorMap[color] ?? colorMap.brand} flex items-center justify-center`}>
          <Icon className="w-4.5 h-4.5" />
        </div>
        <span className="text-xs text-zinc-500 uppercase tracking-wider font-medium">{label}</span>
      </div>
      <p className="text-xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
    </motion.div>
  );
}

function Section({
  title,
  icon: Icon,
  sub,
  children,
}: {
  title: string;
  icon: typeof DollarSign;
  sub?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="p-5 rounded-xl bg-white/[0.02] border border-white/5">
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-5 h-5 text-brand-400" />
        <h2 className="text-base font-semibold text-white">{title}</h2>
        {sub && <span className="text-xs text-zinc-500 ml-auto">{sub}</span>}
      </div>
      {children}
    </div>
  );
}

function TransactionRow({ tx }: { tx: Transaction }) {
  const meta = catMeta(tx.category);
  const isIncome = tx.amount < 0;

  return (
    <div className="flex items-center gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors">
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${meta.color}15` }}
      >
        <meta.icon className="w-4 h-4" style={{ color: meta.color }} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-white truncate">{tx.merchant ?? tx.name}</p>
        <p className="text-xs text-zinc-500">{meta.label} · {tx.date}</p>
      </div>
      <div className="text-right shrink-0">
        <p className={`text-sm font-semibold ${isIncome ? 'text-emerald-400' : 'text-white'}`}>
          {isIncome ? '+' : '-'}{fmt(Math.abs(tx.amount))}
        </p>
        {tx.pending && (
          <span className="text-[10px] text-amber-400 uppercase tracking-wider">Pending</span>
        )}
      </div>
    </div>
  );
}
