'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

/**
 * Google Services OAuth callback page.
 * Google redirects here with ?code=...&state=...
 * We POST the code to /api/google/callback, then notify the opener and close.
 */
export default function GoogleCallbackPage() {
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Connecting your Google account...');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const error = params.get('error');

    if (error) {
      setStatus('error');
      setMessage(`Google denied access: ${error}`);
      setTimeout(() => window.close(), 2000);
      return;
    }

    if (!code) {
      setStatus('error');
      setMessage('No authorization code received.');
      setTimeout(() => window.close(), 2000);
      return;
    }

    // Exchange code for tokens via our API
    api.post<{ success: boolean; profile?: { name?: string; email?: string } }>(
      '/api/google/callback',
      { code, state: params.get('state') || 'volo' }
    )
      .then((data) => {
        setStatus('success');
        setMessage(
          data.profile?.email
            ? `Connected as ${data.profile.email}!`
            : 'Google account connected!'
        );
        // Notify parent window (restrict to same origin)
        if (window.opener) {
          window.opener.postMessage({ type: 'google-connected', success: true }, window.location.origin);
        }
        setTimeout(() => window.close(), 1500);
      })
      .catch((err) => {
        setStatus('error');
        setMessage(err?.message || 'Failed to connect Google account.');
        if (window.opener) {
          window.opener.postMessage({ type: 'google-connected', success: false }, window.location.origin);
        }
        setTimeout(() => window.close(), 3000);
      });
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-white">
      <div className="text-center space-y-4 p-8">
        {status === 'processing' && (
          <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto" />
        )}
        {status === 'success' && (
          <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
        {status === 'error' && (
          <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
        )}
        <p className="text-lg font-medium">{message}</p>
        <p className="text-zinc-500 text-sm">This window will close automatically.</p>
      </div>
    </div>
  );
}
