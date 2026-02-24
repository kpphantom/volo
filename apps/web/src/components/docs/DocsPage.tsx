'use client';

import { useState } from 'react';
import {
  BookOpen,
  ChevronRight,
  Search,
  Code,
  Key,
  Zap,
  Shield,
  Wrench,
  Webhook,
  ExternalLink,
} from 'lucide-react';

interface DocSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  items: { id: string; title: string; content: string }[];
}

const DOCS: DocSection[] = [
  {
    id: 'quickstart',
    title: 'Getting Started',
    icon: <Zap className="w-4 h-4" />,
    items: [
      {
        id: 'intro',
        title: 'Introduction',
        content: `# Welcome to Volo

Volo is your **AI Life Operating System** — one agent to rule them all.

## What can Volo do?
- **Code Management**: GitHub repos, PRs, issues, deployments
- **Trading**: Portfolio tracking, live quotes, order execution
- **Communications**: Email triage, calendar, Slack, social media
- **Machine Control**: Run commands, manage files, SSH into servers
- **Web3**: Wallet tracking, DeFi positions, gas prices
- **Memory**: Learn your preferences, projects, and context over time

## Quick Start
1. Add your API key (Anthropic or OpenAI) in Settings
2. Connect your integrations (GitHub, email, etc.)
3. Start chatting — Volo will help with everything`,
      },
      {
        id: 'setup',
        title: 'Configuration',
        content: `# Configuration

## Environment Variables
Create a \`.env\` file with your API keys:
\`\`\`env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
\`\`\`

## Docker Setup
\`\`\`bash
docker-compose up -d
\`\`\`

This starts PostgreSQL, Redis, the API server, and the web frontend.`,
      },
    ],
  },
  {
    id: 'api',
    title: 'API Reference',
    icon: <Code className="w-4 h-4" />,
    items: [
      {
        id: 'chat',
        title: 'Chat API',
        content: `# Chat API

## POST /api/v1/chat
Send a message and receive a response.

\`\`\`json
{
  "message": "What's the price of Bitcoin?",
  "conversation_id": "optional-uuid",
  "stream": false
}
\`\`\`

### Response
\`\`\`json
{
  "id": "msg-uuid",
  "conversation_id": "conv-uuid",
  "response": "Bitcoin is currently trading at $67,234...",
  "tool_calls": [...],
  "model": "claude-sonnet-4-20250514"
}
\`\`\``,
      },
      {
        id: 'memory',
        title: 'Memory API',
        content: `# Memory API

## POST /api/v1/memory
Store a memory.

\`\`\`json
{
  "category": "preference",
  "content": "User prefers dark mode",
  "source": "api"
}
\`\`\`

## GET /api/v1/memory
List all memories. Optional \`?category=\` filter.`,
      },
      {
        id: 'tools',
        title: 'Tools API',
        content: `# Tools API

## GET /api/v1/tools
List all available tools and their descriptions.

## POST /api/v1/tools/{tool_name}
Execute a tool directly.

\`\`\`json
// POST /api/v1/tools/trading_quote
{ "symbol": "BTC" }
\`\`\``,
      },
    ],
  },
  {
    id: 'auth',
    title: 'Authentication',
    icon: <Key className="w-4 h-4" />,
    items: [
      {
        id: 'api-keys',
        title: 'API Keys',
        content: `# API Key Authentication

Generate an API key from Settings → API Keys.

Include it in requests:
\`\`\`
Authorization: Bearer volo_xxxxxxxxxxxxxxxx
\`\`\`

API keys inherit the permissions of the user who created them.`,
      },
      {
        id: 'jwt',
        title: 'JWT Auth',
        content: `# JWT Authentication

## Login
\`\`\`
POST /api/auth/login
{ "email": "user@example.com", "password": "..." }
\`\`\`

Returns access_token (15min) and refresh_token (7d).

## Refresh
\`\`\`
POST /api/auth/refresh
{ "refresh_token": "..." }
\`\`\``,
      },
    ],
  },
  {
    id: 'webhooks',
    title: 'Webhooks',
    icon: <Webhook className="w-4 h-4" />,
    items: [
      {
        id: 'setup',
        title: 'Setting Up Webhooks',
        content: `# Webhooks

Receive real-time notifications from external services.

## Supported Sources
- **GitHub** — Push events, PR events, issue events
- **Stripe** — Payment events, subscription changes
- **Slack** — Message events, slash commands

## Endpoint
Configure your webhook URL as:
\`\`\`
https://your-domain.com/api/webhooks/inbound/{source}
\`\`\``,
      },
    ],
  },
  {
    id: 'security',
    title: 'Security & Guardrails',
    icon: <Shield className="w-4 h-4" />,
    items: [
      {
        id: 'guardrails',
        title: 'Action Tiers',
        content: `# Guardrails

Volo uses a tiered action system:

| Tier | Actions | Behavior |
|------|---------|----------|
| **Auto** | Read data, search, quotes | Executes automatically |
| **Notify** | Send messages, create events | Executes + notifies you |
| **Approve** | Place orders, delete data | Requires your approval |
| **2FA** | Financial transactions | Requires 2FA confirmation |

You can customize these in Settings → Security.`,
      },
    ],
  },
];

export function DocsPage() {
  const [activeSection, setActiveSection] = useState(DOCS[0].id);
  const [activeItem, setActiveItem] = useState(DOCS[0].items[0].id);
  const [search, setSearch] = useState('');

  const currentSection = DOCS.find((s) => s.id === activeSection);
  const currentItem = currentSection?.items.find((i) => i.id === activeItem);

  // Filter sections by search query
  const filteredDocs = search.trim()
    ? DOCS.map((section) => ({
        ...section,
        items: section.items.filter(
          (item) =>
            item.title.toLowerCase().includes(search.toLowerCase()) ||
            item.content.toLowerCase().includes(search.toLowerCase())
        ),
      })).filter((s) => s.items.length > 0)
    : DOCS;

  return (
    <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
      {/* Mobile Section Selector */}
      <div className="md:hidden border-b border-[var(--border)] px-4 py-2 overflow-x-auto">
        <div className="flex gap-2">
          {DOCS.map((section) => (
            <button
              key={section.id}
              onClick={() => {
                setActiveSection(section.id);
                setActiveItem(section.items[0].id);
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-colors ${
                activeSection === section.id
                  ? 'bg-brand-500/10 text-brand-400 border border-brand-500/30'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] border border-transparent'
              }`}
            >
              {section.icon}
              {section.title}
            </button>
          ))}
        </div>
      </div>

      {/* Desktop Sidebar */}
      <div className="w-64 border-r border-[var(--border)] overflow-y-auto p-4 hidden md:block">
        <div className="relative mb-4">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search docs..."
            className="w-full pl-9 pr-3 py-2 text-sm bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-brand-500"
          />
        </div>

        <nav className="space-y-4">
          {filteredDocs.map((section) => (
            <div key={section.id}>
              <button
                onClick={() => {
                  setActiveSection(section.id);
                  setActiveItem(section.items[0].id);
                }}
                className={`flex items-center gap-2 text-sm font-medium w-full text-left px-2 py-1.5 rounded-lg transition-colors ${
                  activeSection === section.id
                    ? 'text-brand-400'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                {section.icon}
                {section.title}
              </button>
              {activeSection === section.id && (
                <div className="ml-6 mt-1 space-y-0.5">
                  {section.items.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setActiveItem(item.id)}
                      className={`block text-xs w-full text-left px-2 py-1.5 rounded transition-colors ${
                        activeItem === item.id
                          ? 'text-brand-400 bg-brand-500/10'
                          : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                      }`}
                    >
                      {item.title}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-3xl mx-auto">
          {currentItem ? (
            <div className="prose prose-invert max-w-none">
              <div className="text-sm text-[var(--text-muted)] mb-4 flex items-center gap-1">
                <BookOpen className="w-4 h-4" />
                {currentSection?.title}
                <ChevronRight className="w-3 h-3" />
                {currentItem.title}
              </div>
              <div
                className="text-[var(--text-primary)] whitespace-pre-wrap"
                style={{ fontFamily: 'inherit' }}
              >
                {(() => {
                  // Inline markdown formatter
                  const formatInline = (text: string): React.ReactNode[] => {
                    const parts: React.ReactNode[] = [];
                    // Match **bold**, `code`, [link](url)
                    const regex = /(\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\))/g;
                    let lastIndex = 0;
                    let match: RegExpExecArray | null;
                    let key = 0;
                    while ((match = regex.exec(text)) !== null) {
                      if (match.index > lastIndex) {
                        parts.push(text.slice(lastIndex, match.index));
                      }
                      if (match[2]) {
                        parts.push(<strong key={key++} className="font-semibold text-[var(--text-primary)]">{match[2]}</strong>);
                      } else if (match[3]) {
                        parts.push(<code key={key++} className="px-1.5 py-0.5 rounded bg-white/10 text-brand-400 text-xs font-mono">{match[3]}</code>);
                      } else if (match[4] && match[5]) {
                        parts.push(<a key={key++} href={match[5]} target="_blank" rel="noopener noreferrer" className="text-brand-400 hover:underline">{match[4]}</a>);
                      }
                      lastIndex = match.index + match[0].length;
                    }
                    if (lastIndex < text.length) {
                      parts.push(text.slice(lastIndex));
                    }
                    return parts.length > 0 ? parts : [text];
                  };

                  const lines = currentItem.content.split('\n');
                  const elements: React.ReactNode[] = [];
                  let inCodeBlock = false;
                  let codeLines: string[] = [];
                  let codeLang = '';
                  
                  lines.forEach((line, i) => {
                    if (line.startsWith('```') && !inCodeBlock) {
                      inCodeBlock = true;
                      codeLang = line.slice(3).trim();
                      codeLines = [];
                      return;
                    }
                    if (line.startsWith('```') && inCodeBlock) {
                      inCodeBlock = false;
                      elements.push(
                        <div key={`code-${i}`} className="my-3 rounded-xl overflow-hidden border border-white/5">
                          {codeLang && (
                            <div className="px-4 py-1.5 bg-white/5 text-[10px] text-zinc-500 font-mono uppercase tracking-wider border-b border-white/5">
                              {codeLang}
                            </div>
                          )}
                          <pre className="p-4 bg-surface-dark-0 overflow-x-auto">
                            <code className="text-sm font-mono text-zinc-300 whitespace-pre">
                              {codeLines.join('\n')}
                            </code>
                          </pre>
                        </div>
                      );
                      return;
                    }
                    if (inCodeBlock) {
                      codeLines.push(line);
                      return;
                    }
                    if (line.startsWith('# '))
                      elements.push(<h1 key={i} className="text-2xl font-bold mb-4 mt-6">{formatInline(line.slice(2))}</h1>);
                    else if (line.startsWith('## '))
                      elements.push(<h2 key={i} className="text-xl font-semibold mb-3 mt-5">{formatInline(line.slice(3))}</h2>);
                    else if (line.startsWith('### '))
                      elements.push(<h3 key={i} className="text-lg font-medium mb-2 mt-4">{formatInline(line.slice(4))}</h3>);
                    else if (line.startsWith('- '))
                      elements.push(<li key={i} className="text-sm text-[var(--text-secondary)] ml-4 mb-1">{formatInline(line.slice(2))}</li>);
                    else if (line.startsWith('|'))
                      elements.push(<p key={i} className="text-sm font-mono text-[var(--text-secondary)]">{line}</p>);
                    else
                      elements.push(<p key={i} className="text-sm text-[var(--text-secondary)] mb-2">{formatInline(line)}</p>);
                  });
                  return elements;
                })()}
              </div>
            </div>
          ) : (
            <div className="py-16 text-center">
              <BookOpen className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3 opacity-40" />
              <p className="text-sm text-[var(--text-muted)]">Select a doc page</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
