'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Heart,
  Footprints,
  Moon,
  Dumbbell,
  Scale,
  Activity,
  TrendingUp,
  TrendingDown,
  Flame,
  Droplets,
  Target,
  RefreshCw,
  Smartphone,
  ArrowUp,
  ArrowDown,
  Minus,
} from 'lucide-react';

interface StepData {
  date: string;
  count: number;
  goal: number;
  distance_km: number;
  calories: number;
}

interface HeartRateData {
  current: number;
  resting: number;
  max_today: number;
  min_today: number;
  avg_today: number;
  zones: { zone: string; minutes: number; color: string }[];
}

interface SleepData {
  last_night: {
    duration_hours: number;
    deep_hours: number;
    light_hours: number;
    rem_hours: number;
    awake_hours: number;
    quality_score: number;
    bedtime: string;
    wake_time: string;
  };
  weekly_avg: number;
}

interface Workout {
  type: string;
  duration_min: number;
  calories: number;
  date: string;
  intensity: string;
}

interface BodyMetrics {
  weight_kg: number;
  height_cm: number;
  bmi: number;
  body_fat_pct: number;
  muscle_mass_kg: number;
}

interface DashboardData {
  wellness_score: number;
  steps: StepData;
  heart_rate: HeartRateData;
  sleep: SleepData;
  workouts: Workout[];
  body: BodyMetrics;
}

export function HealthDashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'activity' | 'sleep' | 'body'>('overview');

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/health/dashboard');
      const json = await res.json();
      setData(json);
    } catch {
      // Use demo data on error
      setData(getDemoData());
    } finally {
      setLoading(false);
    }
  };

  const getDemoData = (): DashboardData => ({
    wellness_score: 82,
    steps: { date: new Date().toISOString().split('T')[0], count: 8432, goal: 10000, distance_km: 6.2, calories: 342 },
    heart_rate: {
      current: 72, resting: 62, max_today: 145, min_today: 58, avg_today: 78,
      zones: [
        { zone: 'Fat Burn', minutes: 45, color: '#f59e0b' },
        { zone: 'Cardio', minutes: 22, color: '#ef4444' },
        { zone: 'Peak', minutes: 8, color: '#dc2626' },
        { zone: 'Rest', minutes: 365, color: '#22c55e' },
      ],
    },
    sleep: {
      last_night: {
        duration_hours: 7.4, deep_hours: 1.8, light_hours: 3.2, rem_hours: 1.9, awake_hours: 0.5,
        quality_score: 85, bedtime: '23:15', wake_time: '06:45',
      },
      weekly_avg: 7.1,
    },
    workouts: [
      { type: 'Running', duration_min: 35, calories: 380, date: new Date().toISOString(), intensity: 'high' },
      { type: 'Yoga', duration_min: 45, calories: 150, date: new Date(Date.now() - 86400000).toISOString(), intensity: 'low' },
      { type: 'Weight Training', duration_min: 50, calories: 290, date: new Date(Date.now() - 172800000).toISOString(), intensity: 'medium' },
      { type: 'Cycling', duration_min: 60, calories: 450, date: new Date(Date.now() - 259200000).toISOString(), intensity: 'high' },
      { type: 'Swimming', duration_min: 40, calories: 320, date: new Date(Date.now() - 345600000).toISOString(), intensity: 'medium' },
    ],
    body: { weight_kg: 75.2, height_cm: 178, bmi: 23.7, body_fat_pct: 18.5, muscle_mass_kg: 33.2 },
  });

  const getWellnessColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  const getWellnessGradient = (score: number) => {
    if (score >= 80) return 'from-emerald-500 to-emerald-700';
    if (score >= 60) return 'from-amber-500 to-amber-700';
    return 'from-red-500 to-red-700';
  };

  const getIntensityColor = (intensity: string) => {
    switch (intensity) {
      case 'high': return 'bg-red-500/20 text-red-400';
      case 'medium': return 'bg-amber-500/20 text-amber-400';
      case 'low': return 'bg-emerald-500/20 text-emerald-400';
      default: return 'bg-zinc-500/20 text-zinc-400';
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / 86400000);
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    return `${days} days ago`;
  };

  const tabs = [
    { id: 'overview' as const, label: 'Overview', icon: Activity },
    { id: 'activity' as const, label: 'Activity', icon: Dumbbell },
    { id: 'sleep' as const, label: 'Sleep', icon: Moon },
    { id: 'body' as const, label: 'Body', icon: Scale },
  ];

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-surface-dark-1">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center mx-auto animate-pulse">
            <Heart className="w-6 h-6 text-white" />
          </div>
          <p className="text-zinc-400 text-sm">Loading health data...</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const stepProgress = Math.min((data.steps.count / data.steps.goal) * 100, 100);

  return (
    <div className="flex-1 overflow-y-auto bg-surface-dark-1">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center">
                <Heart className="w-5 h-5 text-white" />
              </div>
              Health & Fitness
            </h1>
            <p className="text-zinc-500 text-sm mt-1">Your wellness dashboard powered by Apple Health & Google Fit</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <Smartphone className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-emerald-400">Synced</span>
            </div>
            <button
              onClick={fetchDashboard}
              className="p-2 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-white/5 pb-0">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
                activeTab === tab.id
                  ? 'text-rose-400 border-rose-400'
                  : 'text-zinc-500 border-transparent hover:text-zinc-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Wellness Score + Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Wellness Score Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="md:col-span-1 p-6 rounded-2xl bg-surface-dark-2 border border-white/5 flex flex-col items-center justify-center"
              >
                <div className="relative w-28 h-28 mb-3">
                  <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
                    <circle
                      cx="50" cy="50" r="42" fill="none"
                      stroke="url(#wellnessGrad)"
                      strokeWidth="8"
                      strokeLinecap="round"
                      strokeDasharray={`${data.wellness_score * 2.64} 264`}
                    />
                    <defs>
                      <linearGradient id="wellnessGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#f43f5e" />
                        <stop offset="100%" stopColor="#ec4899" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className={`text-3xl font-bold ${getWellnessColor(data.wellness_score)}`}>
                      {data.wellness_score}
                    </span>
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Score</span>
                  </div>
                </div>
                <p className="text-sm text-zinc-300 font-medium">Wellness Score</p>
                <p className="text-xs text-zinc-500 mt-1">Based on all metrics</p>
              </motion.div>

              {/* Quick Stats */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="p-5 rounded-2xl bg-surface-dark-2 border border-white/5"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Footprints className="w-4 h-4 text-blue-400" />
                  <span className="text-xs text-zinc-500 uppercase tracking-wider">Steps</span>
                </div>
                <p className="text-2xl font-bold text-white">{data.steps.count.toLocaleString()}</p>
                <div className="mt-2 w-full bg-white/5 rounded-full h-2">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all"
                    style={{ width: `${stepProgress}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1.5">
                  <span className="text-[10px] text-zinc-600">{Math.round(stepProgress)}%</span>
                  <span className="text-[10px] text-zinc-600">Goal: {data.steps.goal.toLocaleString()}</span>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="p-5 rounded-2xl bg-surface-dark-2 border border-white/5"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Heart className="w-4 h-4 text-rose-400" />
                  <span className="text-xs text-zinc-500 uppercase tracking-wider">Heart Rate</span>
                </div>
                <div className="flex items-end gap-2">
                  <p className="text-2xl font-bold text-white">{data.heart_rate.current}</p>
                  <span className="text-sm text-zinc-500 mb-1">bpm</span>
                </div>
                <div className="mt-2 flex gap-3 text-[10px]">
                  <span className="text-zinc-500">Resting: <span className="text-zinc-300">{data.heart_rate.resting}</span></span>
                  <span className="text-zinc-500">Range: <span className="text-zinc-300">{data.heart_rate.min_today}-{data.heart_rate.max_today}</span></span>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="p-5 rounded-2xl bg-surface-dark-2 border border-white/5"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Moon className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs text-zinc-500 uppercase tracking-wider">Sleep</span>
                </div>
                <div className="flex items-end gap-2">
                  <p className="text-2xl font-bold text-white">{data.sleep.last_night.duration_hours}</p>
                  <span className="text-sm text-zinc-500 mb-1">hours</span>
                </div>
                <div className="mt-2 flex gap-3 text-[10px]">
                  <span className="text-zinc-500">Quality: <span className="text-zinc-300">{data.sleep.last_night.quality_score}%</span></span>
                  <span className="text-zinc-500">Avg: <span className="text-zinc-300">{data.sleep.weekly_avg}h</span></span>
                </div>
              </motion.div>
            </div>

            {/* Activity Ring + Heart Rate Zones */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Today's Metrics */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="p-6 rounded-2xl bg-surface-dark-2 border border-white/5"
              >
                <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                  <Target className="w-4 h-4 text-brand-400" />
                  Today&apos;s Activity
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center p-4 rounded-xl bg-white/[0.02]">
                    <Flame className="w-5 h-5 text-orange-400 mx-auto mb-2" />
                    <p className="text-lg font-bold text-white">{data.steps.calories}</p>
                    <p className="text-[10px] text-zinc-500 mt-1">Calories</p>
                  </div>
                  <div className="text-center p-4 rounded-xl bg-white/[0.02]">
                    <Footprints className="w-5 h-5 text-blue-400 mx-auto mb-2" />
                    <p className="text-lg font-bold text-white">{data.steps.distance_km}</p>
                    <p className="text-[10px] text-zinc-500 mt-1">km Distance</p>
                  </div>
                  <div className="text-center p-4 rounded-xl bg-white/[0.02]">
                    <Activity className="w-5 h-5 text-emerald-400 mx-auto mb-2" />
                    <p className="text-lg font-bold text-white">{data.workouts.length}</p>
                    <p className="text-[10px] text-zinc-500 mt-1">Workouts</p>
                  </div>
                </div>
              </motion.div>

              {/* Heart Rate Zones */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
                className="p-6 rounded-2xl bg-surface-dark-2 border border-white/5"
              >
                <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                  <Heart className="w-4 h-4 text-rose-400" />
                  Heart Rate Zones
                </h3>
                <div className="space-y-3">
                  {data.heart_rate.zones.map((zone) => {
                    const totalMin = data.heart_rate.zones.reduce((acc, z) => acc + z.minutes, 0);
                    const pct = Math.round((zone.minutes / totalMin) * 100);
                    return (
                      <div key={zone.zone}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-zinc-400">{zone.zone}</span>
                          <span className="text-zinc-500">{zone.minutes} min ({pct}%)</span>
                        </div>
                        <div className="w-full bg-white/5 rounded-full h-2">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{ width: `${pct}%`, backgroundColor: zone.color }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            </div>

            {/* Recent Workouts */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="p-6 rounded-2xl bg-surface-dark-2 border border-white/5"
            >
              <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                <Dumbbell className="w-4 h-4 text-amber-400" />
                Recent Workouts
              </h3>
              <div className="space-y-2">
                {data.workouts.slice(0, 5).map((workout, i) => (
                  <div key={i} className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/[0.02] transition-colors">
                    <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0">
                      <Dumbbell className="w-5 h-5 text-amber-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white font-medium">{workout.type}</p>
                      <p className="text-xs text-zinc-500">{formatDate(workout.date)} · {workout.duration_min} min</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <p className="text-sm text-zinc-300">{workout.calories} cal</p>
                      </div>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full ${getIntensityColor(workout.intensity)}`}>
                        {workout.intensity}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        )}

        {/* Activity Tab */}
        {activeTab === 'activity' && (
          <div className="space-y-6">
            {/* Step Goal */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-6 rounded-2xl bg-surface-dark-2 border border-white/5"
            >
              <h3 className="text-sm font-medium text-white mb-6 flex items-center gap-2">
                <Footprints className="w-4 h-4 text-blue-400" />
                Step Progress
              </h3>
              <div className="flex items-center gap-8">
                <div className="relative w-36 h-36">
                  <svg className="w-36 h-36 -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
                    <circle
                      cx="50" cy="50" r="42" fill="none"
                      stroke="url(#stepGrad)"
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeDasharray={`${stepProgress * 2.64} 264`}
                    />
                    <defs>
                      <linearGradient id="stepGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#3b82f6" />
                        <stop offset="100%" stopColor="#06b6d4" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl font-bold text-white">{data.steps.count.toLocaleString()}</span>
                    <span className="text-[10px] text-zinc-500">of {data.steps.goal.toLocaleString()}</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 flex-1">
                  <div className="p-4 rounded-xl bg-white/[0.02]">
                    <Flame className="w-4 h-4 text-orange-400 mb-2" />
                    <p className="text-lg font-bold text-white">{data.steps.calories}</p>
                    <p className="text-xs text-zinc-500">Active Calories</p>
                  </div>
                  <div className="p-4 rounded-xl bg-white/[0.02]">
                    <TrendingUp className="w-4 h-4 text-emerald-400 mb-2" />
                    <p className="text-lg font-bold text-white">{data.steps.distance_km} km</p>
                    <p className="text-xs text-zinc-500">Distance</p>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* All Workouts */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="p-6 rounded-2xl bg-surface-dark-2 border border-white/5"
            >
              <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                <Dumbbell className="w-4 h-4 text-amber-400" />
                All Workouts
              </h3>
              <div className="space-y-2">
                {data.workouts.map((workout, i) => (
                  <div key={i} className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.02]">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center flex-shrink-0">
                      <Dumbbell className="w-6 h-6 text-amber-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white font-medium">{workout.type}</p>
                      <p className="text-xs text-zinc-500">{formatDate(workout.date)}</p>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <div className="text-center">
                        <p className="text-zinc-300 font-medium">{workout.duration_min}</p>
                        <p className="text-[10px] text-zinc-600">min</p>
                      </div>
                      <div className="text-center">
                        <p className="text-zinc-300 font-medium">{workout.calories}</p>
                        <p className="text-[10px] text-zinc-600">cal</p>
                      </div>
                      <span className={`text-[10px] px-2.5 py-1 rounded-full ${getIntensityColor(workout.intensity)}`}>
                        {workout.intensity}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        )}

        {/* Sleep Tab */}
        {activeTab === 'sleep' && (
          <div className="space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-6 rounded-2xl bg-surface-dark-2 border border-white/5"
            >
              <h3 className="text-sm font-medium text-white mb-6 flex items-center gap-2">
                <Moon className="w-4 h-4 text-indigo-400" />
                Last Night&apos;s Sleep
              </h3>
              <div className="flex items-center gap-8">
                <div className="relative w-36 h-36">
                  <svg className="w-36 h-36 -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
                    <circle
                      cx="50" cy="50" r="42" fill="none"
                      stroke="url(#sleepGrad)"
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeDasharray={`${data.sleep.last_night.quality_score * 2.64} 264`}
                    />
                    <defs>
                      <linearGradient id="sleepGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#6366f1" />
                        <stop offset="100%" stopColor="#8b5cf6" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl font-bold text-white">{data.sleep.last_night.quality_score}%</span>
                    <span className="text-[10px] text-zinc-500">Quality</span>
                  </div>
                </div>
                <div className="flex-1 space-y-3">
                  <div className="flex justify-between items-center p-3 rounded-xl bg-white/[0.02]">
                    <span className="text-sm text-zinc-400">Duration</span>
                    <span className="text-sm text-white font-medium">{data.sleep.last_night.duration_hours}h</span>
                  </div>
                  <div className="flex justify-between items-center p-3 rounded-xl bg-white/[0.02]">
                    <span className="text-sm text-zinc-400">Bedtime</span>
                    <span className="text-sm text-white font-medium">{data.sleep.last_night.bedtime}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 rounded-xl bg-white/[0.02]">
                    <span className="text-sm text-zinc-400">Wake Time</span>
                    <span className="text-sm text-white font-medium">{data.sleep.last_night.wake_time}</span>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Sleep Stages */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="p-6 rounded-2xl bg-surface-dark-2 border border-white/5"
            >
              <h3 className="text-sm font-medium text-white mb-4">Sleep Stages</h3>
              <div className="space-y-3">
                {[
                  { label: 'Deep Sleep', hours: data.sleep.last_night.deep_hours, color: '#6366f1', desc: 'Physical recovery' },
                  { label: 'Light Sleep', hours: data.sleep.last_night.light_hours, color: '#818cf8', desc: 'Memory consolidation' },
                  { label: 'REM Sleep', hours: data.sleep.last_night.rem_hours, color: '#a78bfa', desc: 'Dream state / mental recovery' },
                  { label: 'Awake', hours: data.sleep.last_night.awake_hours, color: '#ef4444', desc: 'Interruptions' },
                ].map(stage => {
                  const pct = Math.round((stage.hours / data.sleep.last_night.duration_hours) * 100);
                  return (
                    <div key={stage.label}>
                      <div className="flex justify-between text-xs mb-1">
                        <div>
                          <span className="text-zinc-300">{stage.label}</span>
                          <span className="text-zinc-600 ml-2">{stage.desc}</span>
                        </div>
                        <span className="text-zinc-400">{stage.hours}h ({pct}%)</span>
                      </div>
                      <div className="w-full bg-white/5 rounded-full h-2.5">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{ width: `${pct}%`, backgroundColor: stage.color }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </div>
        )}

        {/* Body Tab */}
        {activeTab === 'body' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: 'Weight', value: `${data.body.weight_kg} kg`, icon: Scale, color: 'text-blue-400', trend: 'down' as const },
                { label: 'BMI', value: data.body.bmi.toFixed(1), icon: Activity, color: 'text-emerald-400', trend: 'stable' as const },
                { label: 'Body Fat', value: `${data.body.body_fat_pct}%`, icon: Droplets, color: 'text-amber-400', trend: 'down' as const },
              ].map((metric, i) => (
                <motion.div
                  key={metric.label}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-6 rounded-2xl bg-surface-dark-2 border border-white/5"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <metric.icon className={`w-4 h-4 ${metric.color}`} />
                      <span className="text-xs text-zinc-500 uppercase tracking-wider">{metric.label}</span>
                    </div>
                    {metric.trend === 'down' && <ArrowDown className="w-4 h-4 text-emerald-400" />}
                    {metric.trend === 'stable' && <Minus className="w-4 h-4 text-zinc-500" />}
                  </div>
                  <p className="text-3xl font-bold text-white">{metric.value}</p>
                </motion.div>
              ))}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="p-6 rounded-2xl bg-surface-dark-2 border border-white/5"
            >
              <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                <Scale className="w-4 h-4 text-blue-400" />
                Body Composition
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.02] text-center">
                  <p className="text-xl font-bold text-white">{data.body.height_cm}</p>
                  <p className="text-xs text-zinc-500 mt-1">Height (cm)</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] text-center">
                  <p className="text-xl font-bold text-white">{data.body.weight_kg}</p>
                  <p className="text-xs text-zinc-500 mt-1">Weight (kg)</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] text-center">
                  <p className="text-xl font-bold text-white">{data.body.muscle_mass_kg}</p>
                  <p className="text-xs text-zinc-500 mt-1">Muscle Mass (kg)</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] text-center">
                  <p className="text-xl font-bold text-white">{data.body.bmi.toFixed(1)}</p>
                  <p className="text-xs text-zinc-500 mt-1">BMI</p>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}
