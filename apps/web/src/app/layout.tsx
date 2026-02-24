import type { Metadata, Viewport } from 'next';
import { Toaster } from 'sonner';
import { ThemeProvider } from '@/components/providers/ThemeProvider';
import './globals.css';

export const metadata: Metadata = {
  title: 'Volo — AI Life OS',
  description: 'One agent. Total control. Your AI operating system for code, trading, communications, and life.',
  keywords: ['AI assistant', 'life OS', 'productivity', 'trading', 'coding', 'agent'],
  authors: [{ name: 'Volo' }],
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Volo',
  },
  openGraph: {
    title: 'Volo — AI Life OS',
    description: 'One agent. Total control.',
    type: 'website',
  },
};

export const viewport: Viewport = {
  themeColor: '#09090b',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="bg-surface-dark-0 text-zinc-200 min-h-screen antialiased">
        <ThemeProvider>
          {children}
        </ThemeProvider>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#18181b',
              border: '1px solid rgba(255,255,255,0.05)',
              color: '#e4e4e7',
              fontSize: '13px',
            },
          }}
        />
      </body>
    </html>
  );
}
