'use client';

import { Brain, User, Copy, RotateCcw, ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { toast } from 'sonner';

export interface ToolCall {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  result?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'streaming' | 'error';
  toolCalls?: ToolCall[];
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRegenerate = () => {
    // Find the last user message and resend it
    const messages = useChatStore.getState().messages;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUserMsg) {
      // Remove the current assistant message and all messages after
      const msgIndex = messages.findIndex((m) => m.id === message.id);
      if (msgIndex >= 0) {
        useChatStore.setState({
          messages: messages.slice(0, msgIndex),
        });
      }
      useChatStore.getState().sendMessage(lastUserMsg.content);
      toast.info('Regenerating response...');
    }
  };

  const handleFeedback = async (type: 'up' | 'down') => {
    setFeedback(type);
    try {
      await api.post('/api/chat/feedback', {
        message_id: message.id,
        conversation_id: useChatStore.getState().conversationId,
        feedback: type === 'up' ? 'positive' : 'negative',
      });
      toast.success(type === 'up' ? 'Thanks for the feedback!' : 'Feedback noted, we\'ll improve');
    } catch {
      // Feedback is best-effort, don't show error
    }
  };

  return (
    <div
      className={cn(
        'flex gap-4 animate-slide-up',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center mt-1',
          isUser
            ? 'bg-zinc-700'
            : 'bg-gradient-to-br from-brand-500 to-brand-700'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-zinc-300" />
        ) : (
          <Brain className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={cn('flex-1 min-w-0', isUser ? 'text-right' : 'text-left')}>
        <div className={cn('flex items-center gap-2 mb-1', isUser && 'justify-end')}>
          <span className="text-xs font-medium text-zinc-400">
            {isUser ? 'You' : 'Volo'}
          </span>
          <span className="text-[10px] text-zinc-600">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>

        <div
          className={cn(
            'inline-block rounded-2xl px-4 py-3 text-sm leading-relaxed max-w-full',
            isUser
              ? 'bg-brand-600/20 text-zinc-200 rounded-br-md'
              : 'bg-surface-dark-2 text-zinc-300 rounded-bl-md border border-white/5'
          )}
        >
          {/* Tool calls display */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mb-3 space-y-2">
              {message.toolCalls.map((tool) => (
                <div
                  key={tool.id}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 text-xs"
                >
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full',
                      tool.status === 'running' && 'bg-amber-400 animate-pulse-soft',
                      tool.status === 'completed' && 'bg-emerald-400',
                      tool.status === 'failed' && 'bg-red-400'
                    )}
                  />
                  <span className="font-mono text-zinc-400">
                    {formatToolName(tool.name)}
                  </span>
                  <span className="text-zinc-600">
                    {tool.status === 'running' && 'Running...'}
                    {tool.status === 'completed' && 'Done'}
                    {tool.status === 'failed' && 'Failed'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Message content */}
          {isUser ? (
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none break-words">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const isInline = !className;
                    return isInline ? (
                      <code
                        className="bg-white/10 text-brand-300 px-1.5 py-0.5 rounded text-xs font-mono"
                        {...props}
                      >
                        {children}
                      </code>
                    ) : (
                      <code className={cn(className, 'text-xs')} {...props}>
                        {children}
                      </code>
                    );
                  },
                  pre({ children, ...props }) {
                    return (
                      <pre
                        className="bg-black/40 rounded-xl p-4 overflow-x-auto border border-white/5 my-3"
                        {...props}
                      >
                        {children}
                      </pre>
                    );
                  },
                  table({ children, ...props }) {
                    return (
                      <div className="overflow-x-auto my-3">
                        <table className="w-full text-xs border-collapse" {...props}>
                          {children}
                        </table>
                      </div>
                    );
                  },
                  th({ children, ...props }) {
                    return (
                      <th className="border border-white/10 px-3 py-2 bg-white/5 text-left text-zinc-300 font-medium" {...props}>
                        {children}
                      </th>
                    );
                  },
                  td({ children, ...props }) {
                    return (
                      <td className="border border-white/10 px-3 py-2 text-zinc-400" {...props}>
                        {children}
                      </td>
                    );
                  },
                  a({ href, children, ...props }) {
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-brand-400 hover:text-brand-300 underline underline-offset-2"
                        {...props}
                      >
                        {children}
                      </a>
                    );
                  },
                  ul({ children, ...props }) {
                    return <ul className="list-disc list-inside space-y-1 my-2" {...props}>{children}</ul>;
                  },
                  ol({ children, ...props }) {
                    return <ol className="list-decimal list-inside space-y-1 my-2" {...props}>{children}</ol>;
                  },
                  h1({ children, ...props }) {
                    return <h1 className="text-lg font-bold text-white mt-4 mb-2" {...props}>{children}</h1>;
                  },
                  h2({ children, ...props }) {
                    return <h2 className="text-base font-bold text-white mt-3 mb-2" {...props}>{children}</h2>;
                  },
                  h3({ children, ...props }) {
                    return <h3 className="text-sm font-bold text-zinc-200 mt-3 mb-1" {...props}>{children}</h3>;
                  },
                  blockquote({ children, ...props }) {
                    return (
                      <blockquote className="border-l-2 border-brand-500 pl-3 my-2 text-zinc-400 italic" {...props}>
                        {children}
                      </blockquote>
                    );
                  },
                  p({ children, ...props }) {
                    return <p className="my-1.5 leading-relaxed" {...props}>{children}</p>;
                  },
                  strong({ children, ...props }) {
                    return <strong className="font-semibold text-zinc-200" {...props}>{children}</strong>;
                  },
                  hr(props) {
                    return <hr className="border-white/10 my-4" {...props} />;
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
              {message.status === 'streaming' && (
                <span className="cursor-blink" />
              )}
            </div>
          )}
        </div>

        {/* Assistant message actions */}
        {!isUser && message.status !== 'streaming' && message.content && (
          <div className="flex items-center gap-1 mt-2">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg hover:bg-white/5 transition-colors group"
              title="Copy"
            >
              {copied ? (
                <Check className="w-3 h-3 text-emerald-400" />
              ) : (
                <Copy className="w-3 h-3 text-zinc-600 group-hover:text-zinc-400" />
              )}
            </button>
            <button
              onClick={handleRegenerate}
              className="p-1.5 rounded-lg hover:bg-white/5 transition-colors group"
              title="Regenerate"
            >
              <RotateCcw className="w-3 h-3 text-zinc-600 group-hover:text-zinc-400" />
            </button>
            <button
              onClick={() => handleFeedback('up')}
              className="p-1.5 rounded-lg hover:bg-white/5 transition-colors group"
              title="Good response"
            >
              <ThumbsUp className={cn('w-3 h-3', feedback === 'up' ? 'text-emerald-400' : 'text-zinc-600 group-hover:text-emerald-400')} />
            </button>
            <button
              onClick={() => handleFeedback('down')}
              className="p-1.5 rounded-lg hover:bg-white/5 transition-colors group"
              title="Bad response"
            >
              <ThumbsDown className={cn('w-3 h-3', feedback === 'down' ? 'text-red-400' : 'text-zinc-600 group-hover:text-red-400')} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function formatToolName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
