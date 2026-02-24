'use client';

import { useState } from 'react';
import {
  Youtube, Search, Play, Clock, ThumbsUp, Eye, Sparkles,
  FileText, List, BookOpen, Baby, Loader2, ExternalLink,
  ChevronDown, Copy, Check, Share2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

type SummaryStyle = 'concise' | 'detailed' | 'bullet_points' | 'eli5';

interface VideoInfo {
  id: string;
  title: string;
  channel?: string;
  description?: string;
  duration?: string;
  views?: number;
  likes?: number;
  thumbnail?: string;
  url?: string;
}

interface SummaryResult {
  video: VideoInfo;
  summary: string;
  style: string;
  has_transcript: boolean;
}

const styleOptions: { id: SummaryStyle; label: string; icon: typeof FileText; desc: string }[] = [
  { id: 'concise', label: 'Concise', icon: FileText, desc: '3-5 sentences' },
  { id: 'detailed', label: 'Detailed', icon: BookOpen, desc: 'Full breakdown' },
  { id: 'bullet_points', label: 'Key Points', icon: List, desc: 'Bullet list' },
  { id: 'eli5', label: 'ELI5', icon: Baby, desc: 'Simple explain' },
];

export function YouTubeSummaryPage() {
  const [url, setUrl] = useState('');
  const [style, setStyle] = useState<SummaryStyle>('concise');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SummaryResult | null>(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<VideoInfo[]>([]);
  const [searching, setSearching] = useState(false);

  const handleSummarize = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await fetch('http://localhost:8000/api/youtube/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim(), style }),
      });
      if (!res.ok) throw new Error('Failed to summarize');
      const data = await res.json();
      setResult(data);
    } catch {
      setError('Could not summarize this video. Please check the URL and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`http://localhost:8000/api/youtube/search?q=${encodeURIComponent(searchQuery)}&limit=6`);
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleCopy = () => {
    if (result?.summary) {
      navigator.clipboard.writeText(result.summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatViews = (n?: number) => {
    if (!n) return '';
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
  };

  return (
    <div className="flex-1 overflow-y-auto bg-surface-dark-2">
      {/* Header */}
      <div className="border-b border-white/5 bg-surface-dark-1">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-600 to-red-700 flex items-center justify-center">
              <Youtube className="w-5 h-5 text-white" />
            </div>
            YouTube AI Summary
          </h1>
          <p className="text-zinc-400 mt-1">Paste any YouTube URL and get an instant AI-powered summary</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">
        {/* URL Input */}
        <div className="bg-white/[0.03] rounded-2xl border border-white/5 p-5">
          <label className="text-sm text-zinc-400 mb-2 block">Video URL</label>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Youtube className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-red-400" />
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSummarize()}
                placeholder="https://youtube.com/watch?v=... or paste video ID"
                className="w-full pl-12 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500/50"
              />
            </div>
            <button
              onClick={handleSummarize}
              disabled={loading || !url.trim()}
              className="px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm flex items-center gap-2 transition-colors"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              Summarize
            </button>
          </div>

          {/* Style Selector */}
          <div className="mt-4 flex gap-2 flex-wrap">
            {styleOptions.map((opt) => (
              <button
                key={opt.id}
                onClick={() => setStyle(opt.id)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all',
                  style === opt.id
                    ? 'bg-brand-600/20 text-brand-400 border border-brand-500/30'
                    : 'bg-white/5 text-zinc-400 border border-white/5 hover:bg-white/10 hover:text-white'
                )}
              >
                <opt.icon className="w-3.5 h-3.5" />
                {opt.label}
                <span className="text-zinc-500 text-[10px]">{opt.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Loading */}
        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-16 gap-4"
            >
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-600 to-red-700 flex items-center justify-center animate-pulse">
                  <Sparkles className="w-7 h-7 text-white" />
                </div>
              </div>
              <p className="text-zinc-400 text-sm">Analyzing video & generating summary...</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Result */}
        <AnimatePresence>
          {result && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              {/* Video Card */}
              <div className="flex gap-4 p-4 rounded-2xl bg-white/[0.03] border border-white/5">
                {result.video.thumbnail && (
                  <div className="relative flex-shrink-0 w-48 h-28 rounded-xl overflow-hidden">
                    <img
                      src={result.video.thumbnail}
                      alt={result.video.title}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 hover:opacity-100 transition-opacity">
                      <Play className="w-10 h-10 text-white" />
                    </div>
                    {result.video.duration && (
                      <span className="absolute bottom-1 right-1 bg-black/80 text-white text-xs px-1.5 py-0.5 rounded">
                        {result.video.duration}
                      </span>
                    )}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h3 className="text-white font-semibold line-clamp-2">{result.video.title}</h3>
                  {result.video.channel && (
                    <p className="text-zinc-400 text-sm mt-1">{result.video.channel}</p>
                  )}
                  <div className="flex items-center gap-4 mt-2 text-xs text-zinc-500">
                    {result.video.views !== undefined && (
                      <span className="flex items-center gap-1">
                        <Eye className="w-3.5 h-3.5" /> {formatViews(result.video.views)} views
                      </span>
                    )}
                    {result.video.likes !== undefined && (
                      <span className="flex items-center gap-1">
                        <ThumbsUp className="w-3.5 h-3.5" /> {formatViews(result.video.likes)}
                      </span>
                    )}
                    {result.has_transcript && (
                      <span className="flex items-center gap-1 text-green-400">
                        <FileText className="w-3.5 h-3.5" /> Transcript available
                      </span>
                    )}
                  </div>
                  {result.video.url && (
                    <a
                      href={result.video.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 mt-2 text-xs text-brand-400 hover:text-brand-300"
                    >
                      Watch on YouTube <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>

              {/* Summary */}
              <div className="rounded-2xl bg-white/[0.03] border border-white/5">
                <div className="flex items-center justify-between p-4 border-b border-white/5">
                  <h3 className="text-white font-semibold flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-brand-400" />
                    AI Summary
                    <span className="text-xs text-zinc-500 font-normal">({result.style})</span>
                  </h3>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleCopy}
                      className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
                    >
                      {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                    <button className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors">
                      <Share2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="p-5">
                  <div className="prose prose-invert prose-sm max-w-none text-zinc-300 leading-relaxed whitespace-pre-wrap">
                    {result.summary}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Search Section */}
        <div className="bg-white/[0.03] rounded-2xl border border-white/5 p-5">
          <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
            <Search className="w-4 h-4 text-zinc-400" />
            Search YouTube
          </h3>
          <div className="flex gap-3">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search for videos..."
              className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"
            />
            <button
              onClick={handleSearch}
              disabled={searching}
              className="px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white text-sm font-medium transition-colors"
            >
              {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
            </button>
          </div>

          {searchResults.length > 0 && (
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {searchResults.map((video) => (
                <button
                  key={video.id}
                  onClick={() => {
                    setUrl(video.url || `https://youtube.com/watch?v=${video.id}`);
                    setSearchResults([]);
                    setSearchQuery('');
                  }}
                  className="flex gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 transition-all text-left"
                >
                  {video.thumbnail && (
                    <img src={video.thumbnail} alt="" className="w-24 h-16 rounded-lg object-cover flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-medium line-clamp-2">{video.title}</p>
                    <p className="text-zinc-500 text-xs mt-1">{video.channel}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
