'use client';

import { useState } from 'react';
import {
  Package,
  Star,
  Download,
  Search,
  ExternalLink,
  Check,
  Zap,
} from 'lucide-react';

interface Plugin {
  id: string;
  name: string;
  description: string;
  author: string;
  category: string;
  downloads: number;
  rating: number;
  installed: boolean;
  icon: string;
}

const PLUGINS: Plugin[] = [
  {
    id: 'jira',
    name: 'Jira Integration',
    description: 'Manage Jira tickets, sprints, and boards directly from Volo.',
    author: 'Volo Team',
    category: 'Project Management',
    downloads: 12400,
    rating: 4.7,
    installed: false,
    icon: '📋',
  },
  {
    id: 'notion',
    name: 'Notion Sync',
    description: 'Read and write Notion pages, databases, and wikis.',
    author: 'Community',
    category: 'Productivity',
    downloads: 8900,
    rating: 4.5,
    installed: false,
    icon: '📝',
  },
  {
    id: 'aws',
    name: 'AWS Manager',
    description: 'Manage EC2 instances, S3 buckets, Lambda functions, and more.',
    author: 'Volo Team',
    category: 'Infrastructure',
    downloads: 6200,
    rating: 4.8,
    installed: true,
    icon: '☁️',
  },
  {
    id: 'figma',
    name: 'Figma Bridge',
    description: 'Extract designs, export assets, and generate code from Figma.',
    author: 'Community',
    category: 'Design',
    downloads: 5100,
    rating: 4.3,
    installed: false,
    icon: '🎨',
  },
  {
    id: 'datadog',
    name: 'Datadog Monitoring',
    description: 'Query metrics, check alerts, and manage monitors.',
    author: 'Volo Team',
    category: 'Monitoring',
    downloads: 3800,
    rating: 4.6,
    installed: false,
    icon: '📊',
  },
  {
    id: 'stripe',
    name: 'Stripe Dashboard',
    description: 'View payments, subscriptions, and revenue analytics.',
    author: 'Volo Team',
    category: 'Finance',
    downloads: 7200,
    rating: 4.9,
    installed: true,
    icon: '💳',
  },
];

const CATEGORIES = ['All', 'Project Management', 'Productivity', 'Infrastructure', 'Design', 'Monitoring', 'Finance'];

export function MarketplacePage() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [plugins, setPlugins] = useState(PLUGINS);

  const filtered = plugins.filter((p) => {
    const matchSearch =
      !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.description.toLowerCase().includes(search.toLowerCase());
    const matchCategory = category === 'All' || p.category === category;
    return matchSearch && matchCategory;
  });

  const toggleInstall = (id: string) => {
    setPlugins((ps) =>
      ps.map((p) => (p.id === id ? { ...p, installed: !p.installed } : p)),
    );
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Marketplace</h1>
          <p className="text-sm text-[var(--text-muted)]">
            Extend Volo with plugins and integrations
          </p>
        </div>

        {/* Search + Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search plugins..."
              className="w-full pl-10 pr-4 py-2.5 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        <div className="flex gap-2 flex-wrap mb-6">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                category === cat
                  ? 'bg-brand-500/10 text-brand-400 border border-brand-500/30'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] border border-transparent hover:border-[var(--border)]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((plugin) => (
            <div
              key={plugin.id}
              className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5 hover:border-brand-500/30 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{plugin.icon}</span>
                  <div>
                    <h3 className="font-medium text-[var(--text-primary)]">{plugin.name}</h3>
                    <p className="text-xs text-[var(--text-muted)]">by {plugin.author}</p>
                  </div>
                </div>
              </div>
              <p className="text-sm text-[var(--text-secondary)] mb-4 line-clamp-2">
                {plugin.description}
              </p>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                  <span className="flex items-center gap-1">
                    <Star className="w-3 h-3 text-yellow-400" />
                    {plugin.rating}
                  </span>
                  <span className="flex items-center gap-1">
                    <Download className="w-3 h-3" />
                    {(plugin.downloads / 1000).toFixed(1)}k
                  </span>
                </div>
                <button
                  onClick={() => toggleInstall(plugin.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                    plugin.installed
                      ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                      : 'bg-brand-500 text-white hover:bg-brand-600'
                  }`}
                >
                  {plugin.installed ? (
                    <>
                      <Check className="w-3 h-3" /> Installed
                    </>
                  ) : (
                    <>
                      <Download className="w-3 h-3" /> Install
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="py-16 text-center">
            <Package className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3 opacity-40" />
            <h3 className="text-lg font-medium text-[var(--text-primary)] mb-1">No plugins found</h3>
            <p className="text-sm text-[var(--text-muted)]">Try adjusting your search or filters.</p>
          </div>
        )}
      </div>
    </div>
  );
}
