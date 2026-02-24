'use client';

import { useState, useEffect } from 'react';
import {
  Clock,
  Plus,
  Play,
  Pause,
  Trash2,
  Edit3,
  RefreshCw,
  Zap,
  Calendar,
} from 'lucide-react';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface StandingOrder {
  id: string;
  name: string;
  schedule: string;
  prompt: string;
  enabled: boolean;
  last_run: string | null;
  next_run: string | null;
  run_count: number;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function StandingOrdersPage() {
  const [orders, setOrders] = useState<StandingOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', schedule: '0 9 * * *', prompt: '' });

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const data = await api.get<{ orders: StandingOrder[] }>('/api/standing-orders');
      setOrders(data?.orders || []);
    } catch {
      setOrders([]);
    } finally {
      setLoading(false);
    }
  };

  const createOrder = async () => {
    try {
      await api.post('/api/standing-orders', formData);
      toast.success('Standing order created');
      setShowForm(false);
      setFormData({ name: '', schedule: '0 9 * * *', prompt: '' });
      fetchOrders();
    } catch {
      toast.error('Failed to create standing order');
    }
  };

  const toggleOrder = async (id: string) => {
    const order = orders.find((o) => o.id === id);
    if (!order) return;
    const newEnabled = !order.enabled;
    setOrders((o) =>
      o.map((order) =>
        order.id === id ? { ...order, enabled: newEnabled } : order,
      ),
    );
    try {
      await api.patch(`/api/standing-orders/${id}`, { enabled: newEnabled });
      toast.success(newEnabled ? 'Order enabled' : 'Order paused');
    } catch {
      setOrders((o) =>
        o.map((order) =>
          order.id === id ? { ...order, enabled: !newEnabled } : order,
        ),
      );
      toast.error('Failed to update order');
    }
  };

  const deleteOrder = async (id: string) => {
    try {
      await api.delete(`/api/standing-orders/${id}`);
      toast.success('Order deleted');
    } catch {
      toast.error('Failed to delete order');
    }
    setOrders((o) => o.filter((order) => order.id !== id));
  };

  const runNow = async (id: string) => {
    try {
      await api.post(`/api/standing-orders/${id}/run`, {});
      toast.success('Order executed! Check chat for results.');
    } catch {
      toast.error('Failed to run order');
    }
  };

  const scheduleLabels: Record<string, string> = {
    '0 9 * * *': 'Every day at 9am',
    '0 9 * * 1-5': 'Weekdays at 9am',
    '0 17 * * 5': 'Fridays at 5pm',
    '*/30 * * * *': 'Every 30 minutes',
    '0 */2 * * *': 'Every 2 hours',
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">
              Standing Orders
            </h1>
            <p className="text-sm text-[var(--text-muted)]">
              Automated tasks that run on a schedule
            </p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm"
          >
            <Plus className="w-4 h-4" /> New Order
          </button>
        </div>

        {/* New order form */}
        {showForm && (
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5 mb-6">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
              Create Standing Order
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-[var(--text-muted)] mb-1 block">Name</label>
                <input
                  value={formData.name}
                  onChange={(e) => setFormData((d) => ({ ...d, name: e.target.value }))}
                  placeholder="e.g. Morning Briefing"
                  className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border)] rounded-lg text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] mb-1 block">Schedule (cron)</label>
                <select
                  value={formData.schedule}
                  onChange={(e) => setFormData((d) => ({ ...d, schedule: e.target.value }))}
                  className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border)] rounded-lg text-sm text-[var(--text-primary)] focus:outline-none focus:border-blue-500"
                >
                  {Object.entries(scheduleLabels).map(([cron, label]) => (
                    <option key={cron} value={cron}>
                      {label} ({cron})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] mb-1 block">Prompt</label>
                <textarea
                  value={formData.prompt}
                  onChange={(e) => setFormData((d) => ({ ...d, prompt: e.target.value }))}
                  placeholder="What should Volo do?"
                  rows={3}
                  className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border)] rounded-lg text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                >
                  Cancel
                </button>
                <button
                  onClick={createOrder}
                  disabled={!formData.name || !formData.prompt}
                  className="px-4 py-2 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-40 transition-colors"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Orders list */}
        <div className="space-y-3">
          {orders.map((order) => (
            <div
              key={order.id}
              className={`bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 transition-opacity ${
                !order.enabled ? 'opacity-50' : ''
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Zap className={`w-4 h-4 ${order.enabled ? 'text-yellow-400' : 'text-[var(--text-muted)]'}`} />
                  <h3 className="font-medium text-[var(--text-primary)]">{order.name}</h3>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => runNow(order.id)}
                    className="p-1.5 text-[var(--text-muted)] hover:text-green-400 transition-colors"
                    title="Run now"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => toggleOrder(order.id)}
                    className="p-1.5 text-[var(--text-muted)] hover:text-yellow-400 transition-colors"
                    title={order.enabled ? 'Pause' : 'Resume'}
                  >
                    {order.enabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => deleteOrder(order.id)}
                    className="p-1.5 text-[var(--text-muted)] hover:text-red-400 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <p className="text-sm text-[var(--text-secondary)] mb-3 line-clamp-2">
                {order.prompt}
              </p>
              <div className="flex items-center gap-4 text-xs text-[var(--text-muted)]">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {scheduleLabels[order.schedule] || order.schedule}
                </span>
                <span className="flex items-center gap-1">
                  <RefreshCw className="w-3 h-3" />
                  {order.run_count} runs
                </span>
                {order.last_run && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Last: {new Date(order.last_run).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          ))}

          {orders.length === 0 && !loading && (
            <div className="py-16 text-center">
              <Clock className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3 opacity-40" />
              <h3 className="text-lg font-medium text-[var(--text-primary)] mb-1">No standing orders</h3>
              <p className="text-sm text-[var(--text-muted)]">
                Create automated tasks that run on a schedule.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
