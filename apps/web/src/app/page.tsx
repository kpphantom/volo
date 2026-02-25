'use client';

import { useEffect, useState, lazy, Suspense } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { ChatArea } from '@/components/chat/ChatArea';
import { CommandPalette } from '@/components/command/CommandPalette';
import { TopBar } from '@/components/layout/TopBar';
import { cn } from '@/lib/utils';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { MobileBottomNav } from '@/components/layout/MobileBottomNav';
import { useAppStore } from '@/stores/appStore';
import { useAuthStore } from '@/stores/authStore';
import { useChatStore } from '@/stores/chatStore';
import { toast } from 'sonner';

// Lazy-loaded page components (code-split)
const DashboardPage = lazy(() => import('@/components/dashboard/DashboardPage').then(m => ({ default: m.DashboardPage })));
const SettingsPage = lazy(() => import('@/components/settings/SettingsPage').then(m => ({ default: m.SettingsPage })));
const ActivityFeed = lazy(() => import('@/components/activity/ActivityFeed').then(m => ({ default: m.ActivityFeed })));
const StandingOrdersPage = lazy(() => import('@/components/standing-orders/StandingOrdersPage').then(m => ({ default: m.StandingOrdersPage })));
const AnalyticsDashboard = lazy(() => import('@/components/analytics/AnalyticsDashboard').then(m => ({ default: m.AnalyticsDashboard })));
const MarketplacePage = lazy(() => import('@/components/marketplace/MarketplacePage').then(m => ({ default: m.MarketplacePage })));
const DocsPage = lazy(() => import('@/components/docs/DocsPage').then(m => ({ default: m.DocsPage })));
const ConversationHistory = lazy(() => import('@/components/conversation/ConversationHistory').then(m => ({ default: m.ConversationHistory })));
const GoogleServicesPage = lazy(() => import('@/components/google/GoogleServicesPage').then(m => ({ default: m.GoogleServicesPage })));
const YouTubeSummaryPage = lazy(() => import('@/components/youtube/YouTubeSummaryPage').then(m => ({ default: m.YouTubeSummaryPage })));
const SocialFeedPage = lazy(() => import('@/components/social/SocialFeedPage').then(m => ({ default: m.SocialFeedPage })));
const MessagingHubPage = lazy(() => import('@/components/messaging/MessagingHubPage').then(m => ({ default: m.MessagingHubPage })));
const HealthDashboardPage = lazy(() => import('@/components/health/HealthDashboardPage').then(m => ({ default: m.HealthDashboardPage })));
const VSCodePage = lazy(() => import('@/components/vscode/VSCodePage').then(m => ({ default: m.VSCodePage })));
const AuthPage = lazy(() => import('@/components/auth/AuthPage').then(m => ({ default: m.AuthPage })));
const OnboardingWizard = lazy(() => import('@/components/onboarding/OnboardingWizard').then(m => ({ default: m.OnboardingWizard })));

function PageSkeleton() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-zinc-500">Loading...</p>
      </div>
    </div>
  );
}

export default function HomePage() {
  const { currentPage, sidebarOpen, commandPaletteOpen, toggleSidebar, setCommandPaletteOpen, setSidebarOpen } = useAppStore();
  const { isAuthenticated, isLoading, user, login } = useAuthStore();
  const [showOnboarding, setShowOnboarding] = useState(false);

  // Handle OAuth callback (e.g. Twitter redirect with ?auth_token=...&provider=twitter)
  useEffect(() => {
    if (isAuthenticated) return;
    const params = new URLSearchParams(window.location.search);

    // Handle OAuth errors
    const error = params.get('error');
    if (error) {
      toast.error(decodeURIComponent(error));
      window.history.replaceState({}, '', '/');
      return;
    }

    const authToken = params.get('auth_token');
    const provider = params.get('provider');
    if (authToken && provider) {
      const userId = params.get('user_id') || `${provider}-user`;
      const name = params.get('name') || `${provider} User`;
      const email = params.get('email') || `user@${provider}.com`;
      const avatar = params.get('avatar') || undefined;
      const onboardingDone = params.get('onboarding_done') === '1';
      login(
        {
          id: userId,
          email: decodeURIComponent(email),
          name: decodeURIComponent(name),
          avatar,
          provider,
          onboardingComplete: onboardingDone,
        },
        authToken
      );
      // Clean URL
      window.history.replaceState({}, '', '/');
    }
  }, [isAuthenticated, login]);

  // Show onboarding after login if not completed
  useEffect(() => {
    if (isAuthenticated && user && !user.onboardingComplete) {
      setShowOnboarding(true);
    }
  }, [isAuthenticated, user]);

  // Global keyboard shortcuts
  useEffect(() => {
    if (!isAuthenticated) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey;

      if (meta && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(!commandPaletteOpen);
      }
      if (meta && e.key === 'n') {
        e.preventDefault();
        useChatStore.getState().clearMessages();
        useAppStore.getState().setPage('chat');
      }
      if (meta && e.key === ',') {
        e.preventDefault();
        useAppStore.getState().setPage('settings');
      }
      if (meta && e.key === 'b') {
        e.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAuthenticated, commandPaletteOpen, setCommandPaletteOpen, toggleSidebar]);

  // Close sidebar on mobile
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setSidebarOpen(false);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [setSidebarOpen]);

  // Auth loading state
  if (isLoading) {
    return (
      <div className="flex h-screen-safe items-center justify-center bg-surface-dark-0 dark:bg-surface-dark-0 light:bg-white">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center animate-pulse">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </div>
          <p className="text-sm text-zinc-400">Loading Volo...</p>
        </div>
      </div>
    );
  }

  // Auth gate — show login/register if not authenticated
  if (!isAuthenticated) {
    return (
      <Suspense fallback={<PageSkeleton />}>
        <AuthPage />
      </Suspense>
    );
  }

  return (
    <>
      {/* Onboarding Wizard */}
      {showOnboarding && (
        <Suspense fallback={null}>
          <OnboardingWizard onComplete={() => setShowOnboarding(false)} />
        </Suspense>
      )}

      <div className="flex h-screen-safe overflow-hidden">
        {/* Skip to content link for accessibility */}
        <a href="#main-content" className="skip-to-content">Skip to content</a>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 md:hidden animate-fade-in"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Sidebar — hidden on mobile, shown via hamburger */}
        <Sidebar />

        {/* Main Content */}
        <div className={cn(
          'flex-1 flex flex-col min-w-0',
          // On mobile: add bottom padding for nav bar, except on chat page (input handles it)
          currentPage !== 'chat' ? 'pb-20 md:pb-0 safe-area-bottom' : 'pb-0'
        )}>
          <TopBar
            onToggleSidebar={toggleSidebar}
            onOpenCommandPalette={() => setCommandPaletteOpen(true)}
          />
          <main id="main-content" role="main" aria-label="Page content" className="flex-1 flex flex-col min-h-0">
            <ErrorBoundary>
              {currentPage === 'chat' && <ChatArea />}
              <Suspense fallback={<PageSkeleton />}>
                {currentPage === 'dashboard' && <DashboardPage />}
                {currentPage === 'settings' && <SettingsPage />}
                {currentPage === 'activity' && <ActivityFeed />}
                {currentPage === 'standing-orders' && <StandingOrdersPage />}
                {currentPage === 'analytics' && <AnalyticsDashboard />}
                {currentPage === 'marketplace' && <MarketplacePage />}
                {currentPage === 'docs' && <DocsPage />}
                {currentPage === 'conversations' && <ConversationHistory />}
                {currentPage === 'google' && <GoogleServicesPage />}
                {currentPage === 'youtube' && <YouTubeSummaryPage />}
                {currentPage === 'social' && <SocialFeedPage />}
                {currentPage === 'messages' && <MessagingHubPage />}
                {currentPage === 'health' && <HealthDashboardPage />}
                {currentPage === 'vscode' && <VSCodePage />}
              </Suspense>
            </ErrorBoundary>
          </main>
        </div>

        {/* Command Palette (Cmd+K) */}
        <CommandPalette
          isOpen={commandPaletteOpen}
          onClose={() => setCommandPaletteOpen(false)}
        />
      </div>

      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />
    </>
  );
}
