import type { Metadata, Viewport } from 'next';
import { Toaster } from 'sonner';
import { ThemeProvider } from '@/components/providers/ThemeProvider';
import { ToasterThemeSync } from '@/components/providers/ToasterThemeSync';
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
  viewportFit: 'cover',
  interactiveWidget: 'resizes-content',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="bg-surface-dark-0 text-zinc-200 antialiased overscroll-none" style={{ minHeight: '100dvh' }}>
        <ThemeProvider>
          {children}
        </ThemeProvider>
        <ToasterThemeSync />
      </body>
    </html>
  );
}
