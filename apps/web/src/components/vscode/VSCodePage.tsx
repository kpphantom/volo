'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Monitor,
  Github,
  Circle,
  FolderGit2,
  Star,
  Lock,
  Globe,
  ArrowRight,
  Terminal,
  Copy,
  Check,
  Wifi,
  WifiOff,
  Code,
  MessageSquare,
  Send,
  Loader2,
  Plus,
  X,
  Smartphone,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Types ──────────────────────────────────────────────────

interface Repo {
  id: number;
  name: string;
  full_name: string;
  description: string;
  language: string;
  private: boolean;
  clone_url: string;
  ssh_url: string;
  html_url: string;
  updated_at: string;
  stargazers_count: number;
  default_branch: string;
}

interface FileChange {
  backup_id: string;
  file_path: string;
  had_original: boolean;
  lines_added: number;
  lines_removed: number;
  review_status: 'pending' | 'kept' | 'undone';
}

interface ToolStep {
  id: string;
  name: string;
  input: Record<string, unknown>;
  status: 'running' | 'completed' | 'error' | 'pending_approval' | 'skipped';
  result?: Record<string, unknown>;
  fileChange?: FileChange;
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  toolSteps?: ToolStep[];
}

interface Session {
  session_id: string;
  repo: Repo;
  messages: ChatMessage[];
}

type PageView = 'setup' | 'repos' | 'coding';

const langColors: Record<string, string> = {
  TypeScript: 'bg-blue-500',
  JavaScript: 'bg-yellow-400',
  Python: 'bg-green-500',
  Rust: 'bg-orange-500',
  Go: 'bg-cyan-400',
  Java: 'bg-red-500',
  Ruby: 'bg-red-400',
  Swift: 'bg-orange-400',
  Kotlin: 'bg-purple-500',
  'C++': 'bg-pink-500',
  C: 'bg-gray-500',
  HTML: 'bg-orange-600',
  CSS: 'bg-blue-400',
  React: 'bg-cyan-500',
  Shell: 'bg-green-400',
};

// ── Markdown Components (matches main chat) ────────────────

const markdownComponents = {
  code({ className, children, ...props }: any) {
    const isInline = !className;
    return isInline ? (
      <code className="bg-white/10 text-brand-300 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>{children}</code>
    ) : (
      <code className={cn(className, 'text-xs')} {...props}>{children}</code>
    );
  },
  pre({ children, ...props }: any) {
    return <pre className="bg-black/40 rounded-xl p-4 overflow-x-auto border border-white/5 my-3" {...props}>{children}</pre>;
  },
  a({ href, children, ...props }: any) {
    return <a href={href} target="_blank" rel="noopener noreferrer" className="text-brand-400 hover:text-brand-300 underline underline-offset-2" {...props}>{children}</a>;
  },
  ul({ children, ...props }: any) {
    return <ul className="list-disc list-inside space-y-1 my-2" {...props}>{children}</ul>;
  },
  ol({ children, ...props }: any) {
    return <ol className="list-decimal list-inside space-y-1 my-2" {...props}>{children}</ol>;
  },
  h1({ children, ...props }: any) {
    return <h1 className="text-lg font-bold text-white mt-4 mb-2" {...props}>{children}</h1>;
  },
  h2({ children, ...props }: any) {
    return <h2 className="text-base font-bold text-white mt-3 mb-2" {...props}>{children}</h2>;
  },
  h3({ children, ...props }: any) {
    return <h3 className="text-sm font-bold text-zinc-200 mt-3 mb-1" {...props}>{children}</h3>;
  },
  blockquote({ children, ...props }: any) {
    return <blockquote className="border-l-2 border-brand-500 pl-3 my-2 text-zinc-400 italic" {...props}>{children}</blockquote>;
  },
  p({ children, ...props }: any) {
    return <p className="my-1.5 leading-relaxed" {...props}>{children}</p>;
  },
  strong({ children, ...props }: any) {
    return <strong className="font-semibold text-zinc-200" {...props}>{children}</strong>;
  },
  hr(props: any) {
    return <hr className="border-white/10 my-4" {...props} />;
  },
};

// ── Main Component ─────────────────────────────────────────

export function VSCodePage() {
  const [view, setView] = useState<PageView>('setup');
  const [agentOnline, setAgentOnline] = useState(false);
  const [agentKey, setAgentKey] = useState<string | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [reposConnected, setReposConnected] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [keyCopied, setKeyCopied] = useState(false);
  const [githubToken, setGithubToken] = useState('');
  const [showTokenInput, setShowTokenInput] = useState(false);

  // Multi-session state
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const activeSession = sessions.find((s) => s.session_id === activeSessionId) || null;

  // Poll agent status
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/api/remote/agent-status?user_id=dev-user`);
        const data = await res.json();
        setAgentOnline(data.online);
        // Restore active sessions on load
        if (data.sessions && data.sessions.length > 0 && sessions.length === 0) {
          // Sessions exist from a previous connection — restore them
          const restored: Session[] = data.sessions.map((s: any) => ({
            session_id: s.session_id,
            repo: {
              id: 0,
              name: s.repo.split('/').pop() || s.repo,
              full_name: s.repo,
              description: '',
              language: '',
              private: false,
              clone_url: s.clone_url || '',
              ssh_url: '',
              html_url: '',
              updated_at: s.started_at,
              stargazers_count: 0,
              default_branch: 'main',
            },
            messages: [{
              role: 'system' as const,
              content: `Reconnected to session on **${s.repo}**.`,
              timestamp: new Date(s.started_at),
            }],
          }));
          setSessions(restored);
          setActiveSessionId(restored[0].session_id);
          setView('coding');
        }
      } catch {
        setAgentOnline(false);
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Auto-fetch repos on repos view
  useEffect(() => {
    if (view === 'repos' && repos.length === 0 && !reposLoading) {
      fetchRepos();
    }
  }, [view]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages]);

  // Generate agent key
  const handleGenerateKey = async () => {
    try {
      const res = await fetch(`${API_URL}/api/remote/agent-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'dev-user', github_token: githubToken || undefined }),
      });
      const data = await res.json();
      setAgentKey(data.agent_key);
      if (data.online) setAgentOnline(true);
      toast.success(data.is_new ? 'Agent key generated!' : 'Agent key retrieved');
    } catch {
      toast.error('Failed to generate agent key');
    }
  };

  // Fetch repos
  const fetchRepos = async () => {
    setReposLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/remote/github/repos?user_id=dev-user`);
      const data = await res.json();
      setRepos(data.repos || []);
      setReposConnected(data.connected || false);
    } catch {
      toast.error('Failed to load repos');
    } finally {
      setReposLoading(false);
    }
  };

  // Start a new session on a repo
  const handleStartSession = async (repo: Repo) => {
    // Check if session already exists for this repo
    const existing = sessions.find((s) => s.repo.full_name === repo.full_name);
    if (existing) {
      setActiveSessionId(existing.session_id);
      setView('coding');
      toast.info(`Switched to existing session: ${repo.name}`);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/remote/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'dev-user',
          repo_full_name: repo.full_name,
          repo_clone_url: repo.clone_url,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || 'Failed to start session');
        return;
      }
      const data = await res.json();

      const newSession: Session = {
        session_id: data.session_id,
        repo,
        messages: [
          {
            role: 'system',
            content: `Session started on **${repo.full_name}**. VS Code is opening on your desktop. Chat with Claude to write code, run commands, and build — all from your phone.`,
            timestamp: new Date(),
          },
        ],
      };

      setSessions((prev) => [...prev, newSession]);
      setActiveSessionId(data.session_id);
      setView('coding');
      toast.success(`Session started: ${repo.name}`);
    } catch {
      toast.error('Failed to start session');
    }
  };

  // End a specific session
  const handleEndSession = async (sessionId: string) => {
    await fetch(`${API_URL}/api/remote/session/end?session_id=${sessionId}`, { method: 'POST' });

    setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));

    // Switch to next tab or back to repos
    if (activeSessionId === sessionId) {
      const remaining = sessions.filter((s) => s.session_id !== sessionId);
      if (remaining.length > 0) {
        setActiveSessionId(remaining[remaining.length - 1].session_id);
      } else {
        setActiveSessionId(null);
        setView('repos');
      }
    }
    toast.success('Session ended');
  };

  // ── Approval handlers (Allow/Skip for commands, Keep/Undo for files) ──

  // Handle Allow/Skip for pending commands
  const handleApprove = async (approvalId: string, decision: 'allow' | 'skip') => {
    try {
      await fetch(`${API_URL}/api/remote/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_id: approvalId, decision }),
      });
    } catch {
      toast.error('Failed to send approval');
    }
  };

  // Handle Keep for file changes (no-op — file is already written)
  const handleKeepFile = (stepId: string) => {
    setSessions((prev) =>
      prev.map((s) =>
        s.session_id === activeSessionId
          ? {
              ...s,
              messages: s.messages.map((m) =>
                m.toolSteps
                  ? {
                      ...m,
                      toolSteps: m.toolSteps.map((step) =>
                        step.id === stepId && step.fileChange
                          ? { ...step, fileChange: { ...step.fileChange, review_status: 'kept' as const } }
                          : step
                      ),
                    }
                  : m
              ),
            }
          : s
      )
    );
  };

  // Handle Undo for file changes — restores the original via agent
  const handleUndoFile = async (stepId: string, backupId: string) => {
    if (!activeSession) return;
    try {
      const res = await fetch(`${API_URL}/api/remote/undo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'dev-user',
          session_id: activeSession.session_id,
          backup_id: backupId,
        }),
      });
      if (res.ok) {
        setSessions((prev) =>
          prev.map((s) =>
            s.session_id === activeSessionId
              ? {
                  ...s,
                  messages: s.messages.map((m) =>
                    m.toolSteps
                      ? {
                          ...m,
                          toolSteps: m.toolSteps.map((step) =>
                            step.id === stepId && step.fileChange
                              ? { ...step, fileChange: { ...step.fileChange, review_status: 'undone' as const } }
                              : step
                          ),
                        }
                      : m
                  ),
                }
              : s
          )
        );
        toast.success('Changes undone');
      } else {
        toast.error('Failed to undo');
      }
    } catch {
      toast.error('Failed to undo changes');
    }
  };

  // Update messages for the active session
  const updateMessages = useCallback(
    (updater: (prev: ChatMessage[]) => ChatMessage[]) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.session_id === activeSessionId
            ? { ...s, messages: updater(s.messages) }
            : s
        )
      );
    },
    [activeSessionId]
  );

  // Send chat message — goes to the autonomous coding agent
  const handleSendChat = async () => {
    if (!chatInput.trim() || chatLoading || !activeSession) return;
    const msg = chatInput.trim();
    setChatInput('');

    updateMessages((prev) => [
      ...prev,
      { role: 'user', content: msg, timestamp: new Date() },
    ]);
    setChatLoading(true);

    try {
      // Use the dedicated remote/chat endpoint — autonomous agent loop
      const response = await fetch(`${API_URL}/api/remote/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'dev-user',
          session_id: activeSession.session_id,
          message: msg,
          messages: activeSession.messages
            .filter((m) => m.role !== 'system')
            .map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let toolSteps: ToolStep[] = [];

      // Add empty assistant message that we'll build up
      updateMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '', timestamp: new Date(), toolSteps: [] },
      ]);

      if (reader) {
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') continue;
              try {
                const parsed = JSON.parse(data);

                // Text content from the AI
                if (parsed.content) {
                  assistantContent += parsed.content;
                  const captured = assistantContent;
                  const capturedSteps = [...toolSteps];
                  updateMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      content: captured,
                      toolSteps: capturedSteps,
                    };
                    return updated;
                  });
                }

                // Tool call starting or status update (pending_approval → running)
                if (parsed.tool_call) {
                  const tc = parsed.tool_call;
                  const existingIdx = toolSteps.findIndex((s) => s.id === tc.id);
                  if (existingIdx >= 0) {
                    // Update existing step (e.g., pending_approval → running)
                    toolSteps = toolSteps.map((s) =>
                      s.id === tc.id ? { ...s, status: tc.status || 'running' } : s
                    );
                  } else {
                    // Add new step
                    toolSteps = [
                      ...toolSteps,
                      {
                        id: tc.id,
                        name: tc.name,
                        input: tc.input || {},
                        status: tc.status || 'running',
                      },
                    ];
                  }
                  const capturedSteps = [...toolSteps];
                  const captured = assistantContent;
                  updateMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      content: captured,
                      toolSteps: capturedSteps,
                    };
                    return updated;
                  });
                }

                // Tool result — the command finished, here's what happened
                if (parsed.tool_result) {
                  const tr = parsed.tool_result;
                  toolSteps = toolSteps.map((s) =>
                    s.id === tr.id
                      ? { ...s, status: (tr.status || 'completed') as ToolStep['status'], result: tr.result }
                      : s
                  );
                  const capturedSteps = [...toolSteps];
                  const captured = assistantContent;
                  updateMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      content: captured,
                      toolSteps: capturedSteps,
                    };
                    return updated;
                  });
                }

                // File change — write_file completed, show Keep/Undo
                if (parsed.file_change) {
                  const fc = parsed.file_change;
                  toolSteps = toolSteps.map((s) =>
                    s.id === fc.id
                      ? {
                          ...s,
                          fileChange: {
                            backup_id: fc.backup_id,
                            file_path: fc.file_path,
                            had_original: fc.had_original,
                            lines_added: fc.lines_added,
                            lines_removed: fc.lines_removed,
                            review_status: 'pending' as const,
                          },
                        }
                      : s
                  );
                  const capturedSteps = [...toolSteps];
                  const captured = assistantContent;
                  updateMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      content: captured,
                      toolSteps: capturedSteps,
                    };
                    return updated;
                  });
                }

                // Error from the agent
                if (parsed.error) {
                  assistantContent += `\n\n**Error:** ${parsed.error}`;
                  const captured = assistantContent;
                  updateMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      content: captured,
                    };
                    return updated;
                  });
                }
              } catch {
                // skip malformed JSON
              }
            }
          }
        }
      }
    } catch {
      updateMessages((prev) => [
        ...prev,
        { role: 'system', content: 'Failed to reach the server. Check your connection.', timestamp: new Date() },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Quick commands
  const handleQuickCommand = async (cmd: string) => {
    if (!activeSession) return;
    setChatLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/remote/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'dev-user',
          session_id: activeSession.session_id,
          command_type: 'run_command',
          payload: { command: cmd },
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const result = data.result;
        updateMessages((prev) => [
          ...prev,
          { role: 'user', content: `\`${cmd}\``, timestamp: new Date() },
          {
            role: 'system',
            content: `\`\`\`\n${result.stdout || result.stderr || result.error || 'Done'}\n\`\`\`${result.exit_code !== 0 ? `\n⚠️ Exit code: ${result.exit_code}` : ''}`,
            timestamp: new Date(),
          },
        ]);
      }
    } catch {
      toast.error('Command failed');
    } finally {
      setChatLoading(false);
    }
  };

  // Copy key
  const copyKey = () => {
    if (agentKey) {
      navigator.clipboard.writeText(agentKey);
      setKeyCopied(true);
      setTimeout(() => setKeyCopied(false), 2000);
    }
  };

  const filteredRepos = repos.filter(
    (r) =>
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // ── Setup Phase ────────────────────────────────────────────
  if (view === 'setup') {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
              <Monitor className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-zinc-100 mb-2">VS Code + Claude</h1>
            <p className="text-zinc-400 text-sm max-w-md mx-auto">
              Code from your phone using your machine&apos;s power. Open multiple repos, each in its own VS Code window, with independent chat sessions.
            </p>
          </div>

          {/* Status Card */}
          <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-zinc-200">Desktop Agent</h2>
              <div className={cn(
                'flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium',
                agentOnline
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-zinc-800 text-zinc-500 border border-white/5'
              )}>
                {agentOnline ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                {agentOnline ? 'Online' : 'Offline'}
              </div>
            </div>

            {!agentKey ? (
              <div className="space-y-4">
                <p className="text-xs text-zinc-500">
                  Generate an agent key to pair your desktop machine with Volo.
                </p>

                <button
                  onClick={() => setShowTokenInput(!showTokenInput)}
                  className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
                >
                  <Github className="w-3 h-3" />
                  {showTokenInput ? 'Hide' : 'Add'} GitHub token (optional)
                </button>

                <AnimatePresence>
                  {showTokenInput && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                    >
                      <input
                        type="password"
                        value={githubToken}
                        onChange={(e) => setGithubToken(e.target.value)}
                        placeholder="ghp_xxxxxxxxxxxx"
                        className="w-full px-3 py-2.5 rounded-lg bg-surface-dark-0 border border-white/5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-brand-500/30 min-h-[44px]"
                        aria-label="GitHub personal access token"
                      />
                      <p className="text-[10px] text-zinc-600 mt-1">
                        Needed to list your repos. Create at github.com/settings/tokens → scopes: repo
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>

                <button
                  onClick={handleGenerateKey}
                  className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors min-h-[48px]"
                >
                  Generate Agent Key
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-zinc-500 mb-2">Your Agent Key:</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 rounded-lg bg-surface-dark-0 border border-white/5 text-xs text-zinc-300 font-mono truncate">
                      {agentKey}
                    </code>
                    <button
                      onClick={copyKey}
                      className="p-2 rounded-lg hover:bg-white/5 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                      aria-label="Copy agent key"
                    >
                      {keyCopied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-zinc-400" />}
                    </button>
                  </div>
                </div>

                {agentOnline ? (
                  <button
                    onClick={() => {
                      fetchRepos();
                      setView('repos');
                    }}
                    className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors flex items-center justify-center gap-2 min-h-[48px]"
                  >
                    Browse Repositories
                    <ArrowRight className="w-4 h-4" />
                  </button>
                ) : (
                  <div className="rounded-xl bg-amber-500/5 border border-amber-500/10 p-4">
                    <p className="text-xs text-amber-400 font-medium mb-2">Set up your desktop</p>
                    <ol className="text-xs text-zinc-400 space-y-1.5 list-decimal list-inside">
                      <li>On your laptop, open Terminal</li>
                      <li><code className="text-zinc-300">cd ~/projects/volo/apps/agent</code></li>
                      <li><code className="text-zinc-300">cp .env.example .env</code></li>
                      <li>Paste your agent key in <code className="text-zinc-300">.env</code></li>
                      <li><code className="text-zinc-300">npm install && npm start</code></li>
                    </ol>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* How it works */}
          <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6">
            <h3 className="text-sm font-semibold text-zinc-200 mb-4">How it works</h3>
            <div className="space-y-4">
              {[
                { icon: Smartphone, text: 'Chat from your phone through Volo', color: 'text-blue-400' },
                { icon: MessageSquare, text: 'Claude understands your intent and generates code', color: 'text-violet-400' },
                { icon: Terminal, text: "Commands run on your desktop machine\u2019s terminal", color: 'text-emerald-400' },
                { icon: Code, text: 'Open multiple repos — each gets its own VS Code window and chat', color: 'text-amber-400' },
              ].map((step, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className={cn('w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0', step.color)}>
                    <step.icon className="w-4 h-4" />
                  </div>
                  <p className="text-sm text-zinc-400 pt-1">{step.text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Repo Picker Phase ──────────────────────────────────────
  if (view === 'repos') {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-xl font-bold text-zinc-100">Select Repository</h1>
              <p className="text-xs text-zinc-500 mt-1">
                Choose a repo to work on — you can open multiple
                {sessions.length > 0 && ` (${sessions.length} active)`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {sessions.length > 0 && (
                <button
                  onClick={() => setView('coding')}
                  className="px-3 py-1.5 rounded-lg bg-brand-600/10 text-brand-400 text-xs font-medium hover:bg-brand-600/20 transition-colors min-h-[32px]"
                >
                  Back to Sessions ({sessions.length})
                </button>
              )}
              <div className={cn(
                'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs',
                agentOnline ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
              )}>
                <Circle className={cn('w-2 h-2 fill-current', agentOnline ? 'text-emerald-400' : 'text-red-400')} />
                {agentOnline ? 'Online' : 'Offline'}
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="mb-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search repositories..."
              className="w-full px-4 py-3 rounded-xl bg-surface-dark-2 border border-white/5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-brand-500/30 min-h-[48px]"
              aria-label="Search repositories"
            />
          </div>

          {/* Repos list */}
          {reposLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-brand-400 animate-spin" />
            </div>
          ) : (
            <div className="space-y-2">
              {filteredRepos.map((repo) => {
                const hasSession = sessions.some((s) => s.repo.full_name === repo.full_name);
                return (
                  <motion.button
                    key={repo.id}
                    onClick={() => handleStartSession(repo)}
                    disabled={!agentOnline}
                    className={cn(
                      'w-full text-left rounded-xl bg-surface-dark-2 border p-4 transition-all',
                      hasSession
                        ? 'border-brand-500/30 bg-brand-500/[0.03]'
                        : 'border-white/5',
                      agentOnline
                        ? 'hover:border-brand-500/30 hover:bg-white/[0.02] cursor-pointer'
                        : 'opacity-50 cursor-not-allowed'
                    )}
                    whileHover={agentOnline ? { scale: 1.005 } : {}}
                    whileTap={agentOnline ? { scale: 0.995 } : {}}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <FolderGit2 className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                          <span className="text-sm font-medium text-zinc-200 truncate">{repo.full_name}</span>
                          {repo.private ? (
                            <Lock className="w-3 h-3 text-amber-500 flex-shrink-0" />
                          ) : (
                            <Globe className="w-3 h-3 text-zinc-600 flex-shrink-0" />
                          )}
                          {hasSession && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-brand-500/10 text-brand-400">
                              Active
                            </span>
                          )}
                        </div>
                        {repo.description && (
                          <p className="text-xs text-zinc-500 truncate mb-2">{repo.description}</p>
                        )}
                        <div className="flex items-center gap-3 text-xs text-zinc-600">
                          {repo.language && (
                            <span className="flex items-center gap-1">
                              <span className={cn('w-2 h-2 rounded-full', langColors[repo.language] || 'bg-zinc-500')} />
                              {repo.language}
                            </span>
                          )}
                          {repo.stargazers_count > 0 && (
                            <span className="flex items-center gap-1">
                              <Star className="w-3 h-3" />
                              {repo.stargazers_count}
                            </span>
                          )}
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-zinc-600 flex-shrink-0 mt-1" />
                    </div>
                  </motion.button>
                );
              })}

              {filteredRepos.length === 0 && !reposLoading && (
                <div className="text-center py-12">
                  <FolderGit2 className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
                  <p className="text-sm text-zinc-500">
                    {searchQuery ? 'No repos match your search' : 'No repositories found'}
                  </p>
                  {!reposConnected && (
                    <p className="text-xs text-zinc-600 mt-2">Add a GitHub token in setup to see your real repos</p>
                  )}
                </div>
              )}
            </div>
          )}

          <button
            onClick={() => setView(sessions.length > 0 ? 'coding' : 'setup')}
            className="mt-4 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            ← Back to {sessions.length > 0 ? 'sessions' : 'setup'}
          </button>
        </div>
      </div>
    );
  }

  // ── Coding Phase (Multi-Tab Sessions) ──────────────────────
  return (
    <div className="flex-1 flex flex-col h-full">
      {/* ── Session Tab Bar ─────────────────────────────────── */}
      <div className="flex items-center border-b border-white/5 bg-surface-dark-1 overflow-x-auto">
        {sessions.map((session) => (
          <button
            key={session.session_id}
            onClick={() => setActiveSessionId(session.session_id)}
            className={cn(
              'group flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap min-h-[40px]',
              session.session_id === activeSessionId
                ? 'border-brand-500 text-zinc-200 bg-white/[0.02]'
                : 'border-transparent text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.01]'
            )}
          >
            <Code className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="max-w-[120px] truncate">{session.repo.name}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleEndSession(session.session_id);
              }}
              className="ml-1 p-0.5 rounded hover:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"
              aria-label={`Close ${session.repo.name} session`}
            >
              <X className="w-3 h-3" />
            </button>
          </button>
        ))}

        {/* New session tab */}
        <button
          onClick={() => {
            fetchRepos();
            setView('repos');
          }}
          className="flex items-center gap-1 px-3 py-2.5 text-xs text-zinc-600 hover:text-zinc-300 transition-colors min-h-[40px]"
          aria-label="Open another repository"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>

        {/* Agent status pill — right side */}
        <div className="ml-auto flex items-center pr-3">
          <div className={cn(
            'flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px]',
            agentOnline ? 'text-emerald-400' : 'text-red-400'
          )}>
            <Circle className={cn('w-1.5 h-1.5 fill-current', agentOnline ? 'text-emerald-400' : 'text-red-400')} />
            {agentOnline ? 'Online' : 'Offline'}
          </div>
        </div>
      </div>

      {/* ── Active Session Content ───────────────────────────── */}
      {activeSession ? (
        <>
          {/* Session Header */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-surface-dark-1/50">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500/20 to-violet-500/20 flex items-center justify-center flex-shrink-0">
                <Code className="w-3.5 h-3.5 text-blue-400" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-zinc-200 truncate">{activeSession.repo.full_name}</p>
                <div className="flex items-center gap-2 text-[10px] text-zinc-500">
                  {activeSession.repo.language && <span>{activeSession.repo.language}</span>}
                  <span>·</span>
                  <span>{activeSession.messages.length} messages</span>
                </div>
              </div>
            </div>
            <button
              onClick={() => handleEndSession(activeSession.session_id)}
              className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-xs font-medium hover:bg-red-500/20 transition-colors min-h-[32px]"
            >
              End Session
            </button>
          </div>

          {/* Quick Actions Bar */}
          <div className="flex items-center gap-2 px-4 py-2 border-b border-white/5 overflow-x-auto">
            {[
              { label: 'git status', cmd: 'git status' },
              { label: 'git log', cmd: 'git log --oneline -10' },
              { label: 'ls', cmd: 'ls -la' },
              { label: 'npm test', cmd: 'npm test' },
              { label: 'npm run build', cmd: 'npm run build' },
            ].map((q) => (
              <button
                key={q.cmd}
                onClick={() => handleQuickCommand(q.cmd)}
                disabled={chatLoading || !agentOnline}
                className="flex-shrink-0 px-3 py-1.5 rounded-lg bg-surface-dark-2 border border-white/5 text-xs text-zinc-400 hover:text-zinc-200 hover:border-white/10 transition-colors disabled:opacity-50 min-h-[32px]"
              >
                <Terminal className="w-3 h-3 inline mr-1" />
                {q.label}
              </button>
            ))}
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {activeSession.messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  'max-w-[85%]',
                  msg.role === 'user' ? 'ml-auto' : 'mr-auto'
                )}
              >
                <div
                  className={cn(
                    'rounded-2xl px-4 py-3 text-sm leading-relaxed',
                    msg.role === 'user'
                      ? 'bg-brand-600 text-white rounded-br-md'
                      : msg.role === 'system'
                      ? 'bg-surface-dark-2 border border-white/5 text-zinc-400'
                      : 'bg-surface-dark-2 text-zinc-200 rounded-bl-md'
                  )}
                >
                  {msg.role === 'user' ? (
                    <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                  ) : (
                    <div className="prose prose-invert prose-sm max-w-none break-words">
                      {/* Tool Steps — show what the AI is doing on the machine */}
                      {msg.toolSteps && msg.toolSteps.length > 0 && (
                        <div className="space-y-2 mb-3">
                          {msg.toolSteps.map((step, si) => (
                            <div
                              key={si}
                              className="rounded-xl border border-white/5 bg-black/30 overflow-hidden"
                            >
                              {/* Tool header */}
                              <div className="flex items-center gap-2 px-3 py-2 bg-white/[0.03] border-b border-white/5">
                                {step.status === 'pending_approval' ? (
                                  <ShieldCheck className="w-3 h-3 text-amber-400 flex-shrink-0" />
                                ) : step.status === 'running' ? (
                                  <Loader2 className="w-3 h-3 text-blue-400 animate-spin flex-shrink-0" />
                                ) : step.status === 'completed' ? (
                                  <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                                ) : step.status === 'skipped' ? (
                                  <X className="w-3 h-3 text-zinc-500 flex-shrink-0" />
                                ) : (
                                  <X className="w-3 h-3 text-red-400 flex-shrink-0" />
                                )}
                                <span className="text-[11px] font-mono text-zinc-400 flex-1 truncate">
                                  {step.name === 'run_command' && (
                                    <><Terminal className="w-3 h-3 inline mr-1" />{String(step.input?.command || '').slice(0, 60)}</>
                                  )}
                                  {step.name === 'read_file' && (
                                    <><Code className="w-3 h-3 inline mr-1" />Read {String(step.input?.path || '')}</>
                                  )}
                                  {step.name === 'write_file' && (
                                    <><Code className="w-3 h-3 inline mr-1" />Write {String(step.input?.path || '')}</>
                                  )}
                                  {step.name === 'list_dir' && (
                                    <><FolderGit2 className="w-3 h-3 inline mr-1" />List {String(step.input?.path || '.')}</>
                                  )}
                                </span>
                              </div>

                              {/* ── Allow / Skip buttons for pending commands ── */}
                              {step.status === 'pending_approval' && step.name === 'run_command' && (
                                <div className="px-3 py-2.5 flex items-center gap-2 bg-amber-500/5">
                                  <span className="text-[11px] text-zinc-500 flex-1">Run this command?</span>
                                  <button
                                    onClick={() => handleApprove(step.id, 'allow')}
                                    className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition-colors min-h-[32px] flex items-center gap-1"
                                  >
                                    <Check className="w-3 h-3" />
                                    Allow
                                  </button>
                                  <button
                                    onClick={() => handleApprove(step.id, 'skip')}
                                    className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition-colors min-h-[32px]"
                                  >
                                    Skip
                                  </button>
                                </div>
                              )}

                              {/* Skipped indicator */}
                              {step.status === 'skipped' && (
                                <div className="px-3 py-1.5 text-[10px] text-zinc-500 italic">
                                  Skipped by user
                                </div>
                              )}

                              {/* Tool result */}
                              {step.result && (step.status === 'completed' || step.status === 'error') && (
                                <div className="px-3 py-2 max-h-48 overflow-y-auto">
                                  <pre className="text-[11px] font-mono text-zinc-400 whitespace-pre-wrap break-all">
                                    {step.name === 'run_command'
                                      ? (String(step.result.stdout || '') + String(step.result.stderr || '')).trim() || (step.result.exit_code === 0 ? 'Done (no output)' : `Exit code: ${step.result.exit_code}`)
                                      : step.name === 'read_file'
                                      ? String(step.result.content || step.result.error || JSON.stringify(step.result, null, 2)).slice(0, 3000)
                                      : step.name === 'write_file'
                                      ? (step.result.success ? `✓ ${String(step.result.file_path || step.input?.path || '')} (${step.result.bytes || 0} bytes)` : String(step.result.error || 'Written'))
                                      : step.name === 'list_dir'
                                      ? (Array.isArray(step.result.entries) ? (step.result.entries as Array<Record<string, unknown>>).map((e) => `${e.type === 'directory' ? '📁' : '📄'} ${e.name || e}`).join('\n') : String(step.result.entries || step.result.error || JSON.stringify(step.result, null, 2)))
                                      : JSON.stringify(step.result, null, 2).slice(0, 2000)
                                    }
                                  </pre>
                                </div>
                              )}

                              {/* ── Keep / Undo buttons for file changes ── */}
                              {step.fileChange && step.fileChange.review_status === 'pending' && (
                                <div className="px-3 py-2.5 flex items-center gap-2 border-t border-white/5 bg-blue-500/5">
                                  <span className="text-[11px] text-zinc-400 flex-1">
                                    {step.fileChange.had_original ? '1 file changed' : '1 file created'}
                                    {' '}
                                    <span className="text-emerald-400">+{step.fileChange.lines_added}</span>
                                    {step.fileChange.had_original && (
                                      <span className="text-red-400"> -{step.fileChange.lines_removed}</span>
                                    )}
                                  </span>
                                  <button
                                    onClick={() => handleKeepFile(step.id)}
                                    className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition-colors min-h-[32px]"
                                  >
                                    Keep
                                  </button>
                                  <button
                                    onClick={() => handleUndoFile(step.id, step.fileChange!.backup_id)}
                                    className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition-colors min-h-[32px] flex items-center gap-1"
                                  >
                                    <RotateCcw className="w-3 h-3" />
                                    Undo
                                  </button>
                                </div>
                              )}
                              {step.fileChange && step.fileChange.review_status === 'kept' && (
                                <div className="px-3 py-1.5 border-t border-white/5 flex items-center gap-1 text-[10px] text-emerald-400">
                                  <Check className="w-3 h-3" /> Changes kept
                                </div>
                              )}
                              {step.fileChange && step.fileChange.review_status === 'undone' && (
                                <div className="px-3 py-1.5 border-t border-white/5 flex items-center gap-1 text-[10px] text-zinc-500">
                                  <RotateCcw className="w-3 h-3" /> Changes undone
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {/* AI text response */}
                      {msg.content && (
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                          {msg.content}
                        </ReactMarkdown>
                      )}
                    </div>
                  )}
                </div>
                <p className="text-[10px] text-zinc-600 mt-1 px-1">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            ))}

            {chatLoading && (
              <div className="flex items-center gap-2 text-zinc-500 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Working on your machine...</span>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div className="border-t border-white/5 p-4 bg-surface-dark-1">
            <div className="flex items-end gap-2">
              <div className="flex-1 relative">
                <textarea
                  value={chatInput}
                  onChange={(e) => {
                    setChatInput(e.target.value);
                    e.target.style.height = 'auto';
                    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendChat();
                    }
                  }}
                  placeholder={agentOnline ? `Ask Claude about ${activeSession.repo.name}...` : 'Agent offline — connect your desktop first'}
                  disabled={!agentOnline}
                  rows={1}
                  className="w-full px-4 py-3 rounded-xl bg-surface-dark-2 border border-white/5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-brand-500/30 resize-none min-h-[48px] max-h-[120px] disabled:opacity-50"
                  aria-label="Chat message"
                />
              </div>
              <button
                onClick={handleSendChat}
                disabled={!chatInput.trim() || chatLoading || !agentOnline}
                className="p-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px] min-w-[48px] flex items-center justify-center"
                aria-label="Send message"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </>
      ) : (
        /* No sessions — prompt to open one */
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <FolderGit2 className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
            <p className="text-sm text-zinc-400 mb-4">No active sessions</p>
            <button
              onClick={() => {
                fetchRepos();
                setView('repos');
              }}
              className="px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors min-h-[48px]"
            >
              Open a Repository
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
