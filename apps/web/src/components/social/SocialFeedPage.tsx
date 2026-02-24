'use client';

import { useState, useEffect } from 'react';
import {
  Heart, ThumbsUp, MessageCircle, Share2, RefreshCw, Filter,
  ExternalLink, Twitter, Instagram, Linkedin, Music, Facebook as FacebookIcon,
  Globe, TrendingUp, Bookmark, MoreHorizontal,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface SocialPost {
  platform: string;
  id: string;
  author: string;
  username: string;
  avatar: string;
  content: string;
  timestamp: string;
  likes: number;
  comments: number;
  shares: number;
  subreddit?: string;
  media: { url: string; type: string }[];
  url: string;
}

interface PlatformInfo {
  id: string;
  name: string;
  connected: boolean;
  color: string;
}

const platformIcons: Record<string, typeof Twitter> = {
  twitter: Twitter,
  instagram: Instagram,
  linkedin: Linkedin,
  reddit: MessageCircle,
  tiktok: Music,
  facebook: FacebookIcon,
};

const platformColors: Record<string, string> = {
  twitter: 'text-blue-400',
  instagram: 'text-pink-400',
  linkedin: 'text-blue-500',
  reddit: 'text-orange-500',
  tiktok: 'text-white',
  facebook: 'text-blue-500',
};

const platformBg: Record<string, string> = {
  twitter: 'bg-blue-500/10',
  instagram: 'bg-gradient-to-br from-purple-500/10 to-pink-500/10',
  linkedin: 'bg-blue-500/10',
  reddit: 'bg-orange-500/10',
  tiktok: 'bg-white/10',
  facebook: 'bg-blue-500/10',
};

export function SocialFeedPage() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [activePlatform, setActivePlatform] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [savedPosts, setSavedPosts] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchFeed();
  }, []);

  const fetchFeed = async (platform?: string) => {
    setLoading(true);
    try {
      const path = platform && platform !== 'all'
        ? `/api/social/feed/${platform}`
        : '/api/social/feed';
      const data = await api.get<{ posts: SocialPost[]; platforms: PlatformInfo[] }>(path);
      setPosts(data.posts || []);
      if (data.platforms) setPlatforms(data.platforms);
    } catch {
      setPosts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterPlatform = (platform: string) => {
    setActivePlatform(platform);
    if (platform === 'all') {
      fetchFeed();
    } else {
      fetchFeed(platform);
    }
  };

  const toggleSave = (postId: string) => {
    setSavedPosts((prev) => {
      const next = new Set(prev);
      if (next.has(postId)) next.delete(postId);
      else next.add(postId);
      return next;
    });
  };

  const formatCount = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
  };

  const timeAgo = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    return `${Math.floor(hours / 24)}d`;
  };

  return (
    <div className="flex-1 overflow-y-auto bg-surface-dark-2">
      {/* Header */}
      <div className="border-b border-white/5 bg-surface-dark-1 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-bold text-white flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Globe className="w-5 h-5 text-white" />
              </div>
              Social Feed
            </h1>
            <button
              onClick={() => fetchFeed(activePlatform === 'all' ? undefined : activePlatform)}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {/* Platform Filter Tabs */}
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hidden">
            <button
              onClick={() => handleFilterPlatform('all')}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
                activePlatform === 'all'
                  ? 'bg-brand-600 text-white'
                  : 'bg-white/5 text-zinc-400 hover:bg-white/10'
              )}
            >
              All Platforms
            </button>
            {platforms.map((p) => {
              const Icon = platformIcons[p.id] || Globe;
              return (
                <button
                  key={p.id}
                  onClick={() => handleFilterPlatform(p.id)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
                    activePlatform === p.id
                      ? 'bg-white/15 text-white'
                      : 'bg-white/5 text-zinc-400 hover:bg-white/10'
                  )}
                >
                  <Icon className={cn('w-3.5 h-3.5', platformColors[p.id])} />
                  {p.name}
                  {!p.connected && (
                    <span className="text-[9px] ml-1 px-1 py-0.5 rounded bg-amber-500/20 text-amber-400">DEMO</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Feed */}
      <div className="max-w-3xl mx-auto px-6 py-4 space-y-3">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-40 rounded-2xl bg-white/5 animate-pulse" />
          ))
        ) : posts.length === 0 ? (
          <div className="text-center py-16 text-zinc-500">
            <Globe className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No posts to show. Connect your accounts to see your feed.</p>
          </div>
        ) : (
          posts.map((post, idx) => {
            const PlatformIcon = platformIcons[post.platform] || Globe;
            return (
              <motion.div
                key={post.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.03 }}
                className="p-5 rounded-2xl bg-white/[0.03] border border-white/5 hover:border-white/10 transition-all"
              >
                {/* Post Header */}
                <div className="flex items-start gap-3">
                  <div className={cn('w-10 h-10 rounded-full flex items-center justify-center', platformBg[post.platform])}>
                    {post.avatar ? (
                      <img src={post.avatar} alt="" className="w-10 h-10 rounded-full" />
                    ) : (
                      <PlatformIcon className={cn('w-5 h-5', platformColors[post.platform])} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-semibold text-sm">{post.author}</span>
                      <span className="text-zinc-500 text-sm">{post.username}</span>
                      <span className="text-zinc-600 text-xs">· {timeAgo(post.timestamp)}</span>
                    </div>
                    {post.subreddit && (
                      <span className="text-orange-400 text-xs">r/{post.subreddit}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <PlatformIcon className={cn('w-4 h-4', platformColors[post.platform])} />
                    <button onClick={() => { if (post.url) window.open(post.url, '_blank'); else toast.info('Open on platform to see options'); }} className="p-1 rounded-lg hover:bg-white/10 text-zinc-500" title="Open original">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Content */}
                <p className="mt-3 text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">
                  {post.content}
                </p>

                {/* Media */}
                {post.media && post.media.length > 0 && post.media[0].url && (
                  <div className="mt-3 rounded-xl overflow-hidden">
                    <img
                      src={post.media[0].url}
                      alt=""
                      className="w-full max-h-80 object-cover rounded-xl"
                    />
                  </div>
                )}

                {/* Actions */}
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center gap-5">
                    <button onClick={() => { if (post.url) window.open(post.url, '_blank'); }} className="flex items-center gap-1.5 text-zinc-500 hover:text-red-400 transition-colors text-xs" title="Like">
                      <Heart className="w-4 h-4" />
                      {post.likes > 0 && formatCount(post.likes)}
                    </button>
                    <button onClick={() => { if (post.url) window.open(post.url, '_blank'); }} className="flex items-center gap-1.5 text-zinc-500 hover:text-blue-400 transition-colors text-xs" title="Comment">
                      <MessageCircle className="w-4 h-4" />
                      {post.comments > 0 && formatCount(post.comments)}
                    </button>
                    <button onClick={() => { if (navigator.share && post.url) { navigator.share({ title: post.author, url: post.url }).catch(() => {}); } else if (post.url) { navigator.clipboard.writeText(post.url); toast.success('Link copied!'); } }} className="flex items-center gap-1.5 text-zinc-500 hover:text-green-400 transition-colors text-xs" title="Share">
                      <Share2 className="w-4 h-4" />
                      {post.shares > 0 && formatCount(post.shares)}
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggleSave(post.id)}
                      className={cn(
                        'p-1.5 rounded-lg transition-colors',
                        savedPosts.has(post.id)
                          ? 'text-brand-400 bg-brand-500/10'
                          : 'text-zinc-500 hover:text-white hover:bg-white/10'
                      )}
                    >
                      <Bookmark className="w-4 h-4" />
                    </button>
                    {post.url && (
                      <a
                        href={post.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-white/10 transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
