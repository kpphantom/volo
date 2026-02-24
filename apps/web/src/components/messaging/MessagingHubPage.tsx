'use client';

import { useState, useEffect, useRef } from 'react';
import {
  MessageSquare, Send, Phone, Video, Search, RefreshCw,
  MoreVertical, Image, Paperclip, Smile, Check, CheckCheck,
  ArrowLeft, Shield, Briefcase, Clock,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

interface Message {
  platform: string;
  id: string;
  from: string;
  from_username: string;
  avatar: string | null;
  content: string;
  timestamp: string;
  chat_id: string;
  chat_title: string;
  read: boolean;
  type: string;
  is_from_me?: boolean;
}

interface PlatformInfo {
  id: string;
  name: string;
  connected: boolean;
  color: string;
}

const platformConfig: Record<string, { color: string; bg: string; icon: string }> = {
  telegram: { color: 'text-sky-400', bg: 'bg-sky-500/10', icon: '✈️' },
  whatsapp: { color: 'text-green-400', bg: 'bg-green-500/10', icon: '💬' },
  whatsapp_business: { color: 'text-teal-400', bg: 'bg-teal-500/10', icon: '💼' },
  imessage: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: '🍎' },
  signal: { color: 'text-blue-500', bg: 'bg-blue-500/10', icon: '🔒' },
};

export function MessagingHubPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [activePlatform, setActivePlatform] = useState<string>('all');
  const [activeChat, setActiveChat] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [replyText, setReplyText] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetchMessages(); }, []);

  const fetchMessages = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/messages');
      const data = await res.json();
      setMessages(data.messages || []);
      setPlatforms(data.platforms || []);
    } catch {
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  // Group messages into "chats" by chat_id
  const chats = messages.reduce<Record<string, { title: string; platform: string; messages: Message[]; lastMessage: Message; unread: number }>>((acc, msg) => {
    const key = `${msg.platform}-${msg.chat_id}`;
    if (!acc[key]) {
      acc[key] = {
        title: msg.chat_title || msg.from,
        platform: msg.platform,
        messages: [],
        lastMessage: msg,
        unread: 0,
      };
    }
    acc[key].messages.push(msg);
    if (!msg.read) acc[key].unread++;
    // Keep the most recent as lastMessage
    if (msg.timestamp > acc[key].lastMessage.timestamp) {
      acc[key].lastMessage = msg;
    }
    return acc;
  }, {});

  const chatList = Object.entries(chats)
    .filter(([_, chat]) => activePlatform === 'all' || chat.platform === activePlatform)
    .filter(([_, chat]) =>
      !searchQuery || chat.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      chat.lastMessage.content.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort(([, a], [, b]) => b.lastMessage.timestamp.localeCompare(a.lastMessage.timestamp));

  const activeChatData = activeChat ? chats[activeChat] : null;

  const timeAgo = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'now';
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    return `${Math.floor(hours / 24)}d`;
  };

  const handleSend = async () => {
    if (!replyText.trim() || !activeChatData) return;
    
    try {
      await fetch('http://localhost:8000/api/messages/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: activeChatData.platform,
          to: activeChatData.lastMessage.chat_id,
          text: replyText,
        }),
      });
    } catch {}
    
    // Optimistic update
    const newMsg: Message = {
      platform: activeChatData.platform,
      id: `sent-${Date.now()}`,
      from: 'You',
      from_username: '',
      avatar: null,
      content: replyText,
      timestamp: new Date().toISOString(),
      chat_id: activeChatData.lastMessage.chat_id,
      chat_title: activeChatData.title,
      read: true,
      type: 'text',
      is_from_me: true,
    };
    setMessages((prev) => [newMsg, ...prev]);
    setReplyText('');
  };

  const totalUnread = Object.values(chats).reduce((sum, c) => sum + c.unread, 0);

  return (
    <div className="flex-1 flex overflow-hidden bg-surface-dark-2">
      {/* Chat List */}
      <div className={cn(
        'flex flex-col border-r border-white/5 bg-surface-dark-1 transition-all',
        activeChat ? 'hidden md:flex w-80' : 'w-full md:w-80',
      )}>
        {/* Header */}
        <div className="px-4 py-3 border-b border-white/5">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-brand-400" />
              Messages
              {totalUnread > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-brand-600 text-white text-xs font-bold">
                  {totalUnread}
                </span>
              )}
            </h1>
            <button onClick={fetchMessages} className="p-2 rounded-lg hover:bg-white/10 text-zinc-400">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search messages..."
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-brand-500/50"
            />
          </div>

          {/* Platform Tabs */}
          <div className="flex gap-1.5 mt-3 overflow-x-auto scrollbar-hidden">
            <button
              onClick={() => setActivePlatform('all')}
              className={cn(
                'px-2.5 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
                activePlatform === 'all' ? 'bg-brand-600 text-white' : 'bg-white/5 text-zinc-400 hover:bg-white/10'
              )}
            >
              All
            </button>
            {platforms.map((p) => {
              const cfg = platformConfig[p.id] || { color: 'text-white', bg: 'bg-white/10', icon: '💬' };
              return (
                <button
                  key={p.id}
                  onClick={() => setActivePlatform(p.id)}
                  className={cn(
                    'flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
                    activePlatform === p.id ? 'bg-white/15 text-white' : 'bg-white/5 text-zinc-400 hover:bg-white/10'
                  )}
                >
                  <span>{cfg.icon}</span>
                  {p.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Chat List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex gap-3 p-4 animate-pulse">
                <div className="w-12 h-12 rounded-full bg-white/5" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-white/5 rounded w-32" />
                  <div className="h-3 bg-white/5 rounded w-48" />
                </div>
              </div>
            ))
          ) : chatList.length === 0 ? (
            <div className="p-8 text-center text-zinc-500 text-sm">
              No conversations yet
            </div>
          ) : (
            chatList.map(([chatKey, chat]) => {
              const cfg = platformConfig[chat.platform] || { color: 'text-white', bg: 'bg-white/10', icon: '💬' };
              return (
                <button
                  key={chatKey}
                  onClick={() => setActiveChat(chatKey)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.03] transition-colors border-b border-white/[0.03]',
                    activeChat === chatKey && 'bg-white/[0.05]'
                  )}
                >
                  <div className={cn('w-11 h-11 rounded-full flex items-center justify-center text-lg', cfg.bg)}>
                    {cfg.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-white text-sm font-medium truncate">{chat.title}</span>
                      <span className="text-zinc-500 text-xs flex-shrink-0">{timeAgo(chat.lastMessage.timestamp)}</span>
                    </div>
                    <div className="flex items-center justify-between mt-0.5">
                      <p className="text-zinc-400 text-xs truncate">{chat.lastMessage.content}</p>
                      {chat.unread > 0 && (
                        <span className="ml-2 w-5 h-5 rounded-full bg-brand-600 text-white text-[10px] flex items-center justify-center font-bold flex-shrink-0">
                          {chat.unread}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Chat View */}
      <div className={cn(
        'flex-1 flex flex-col',
        !activeChat && 'hidden md:flex',
      )}>
        {activeChatData ? (
          <>
            {/* Chat Header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5 bg-surface-dark-1">
              <button
                onClick={() => setActiveChat(null)}
                className="md:hidden p-2 rounded-lg hover:bg-white/10 text-zinc-400"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center text-lg',
                platformConfig[activeChatData.platform]?.bg || 'bg-white/10'
              )}>
                {platformConfig[activeChatData.platform]?.icon || '💬'}
              </div>
              <div className="flex-1">
                <h2 className="text-white font-semibold text-sm">{activeChatData.title}</h2>
                <p className={cn('text-xs capitalize', platformConfig[activeChatData.platform]?.color || 'text-zinc-400')}>
                  {activeChatData.platform.replace('_', ' ')}
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button className="p-2 rounded-lg hover:bg-white/10 text-zinc-400">
                  <Phone className="w-4 h-4" />
                </button>
                <button className="p-2 rounded-lg hover:bg-white/10 text-zinc-400">
                  <Video className="w-4 h-4" />
                </button>
                <button className="p-2 rounded-lg hover:bg-white/10 text-zinc-400">
                  <MoreVertical className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {[...activeChatData.messages].reverse().map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn('flex', msg.is_from_me ? 'justify-end' : 'justify-start')}
                >
                  <div className={cn(
                    'max-w-[75%] px-4 py-2.5 rounded-2xl text-sm',
                    msg.is_from_me
                      ? 'bg-brand-600 text-white rounded-br-md'
                      : 'bg-white/[0.06] text-zinc-200 rounded-bl-md'
                  )}>
                    {!msg.is_from_me && (
                      <p className="text-xs font-medium text-zinc-400 mb-1">{msg.from}</p>
                    )}
                    <p className="leading-relaxed">{msg.content}</p>
                    <div className={cn(
                      'flex items-center justify-end gap-1 mt-1',
                      msg.is_from_me ? 'text-white/50' : 'text-zinc-500'
                    )}>
                      <span className="text-[10px]">{timeAgo(msg.timestamp)}</span>
                      {msg.is_from_me && (
                        msg.read ? <CheckCheck className="w-3.5 h-3.5" /> : <Check className="w-3.5 h-3.5" />
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Reply Bar */}
            <div className="px-4 py-3 border-t border-white/5 bg-surface-dark-1">
              <div className="flex items-center gap-2">
                <button className="p-2 rounded-lg hover:bg-white/10 text-zinc-400">
                  <Paperclip className="w-5 h-5" />
                </button>
                <input
                  type="text"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Type a message..."
                  className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-brand-500/50"
                />
                <button className="p-2 rounded-lg hover:bg-white/10 text-zinc-400">
                  <Smile className="w-5 h-5" />
                </button>
                <button
                  onClick={handleSend}
                  disabled={!replyText.trim()}
                  className="p-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-30 text-white transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-zinc-500">
            <div className="text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <h3 className="text-lg font-medium text-zinc-400 mb-1">Your Unified Inbox</h3>
              <p className="text-sm">Select a conversation from the left to start messaging</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
