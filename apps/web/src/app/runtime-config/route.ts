import { NextResponse } from 'next/server';

/**
 * Runtime config endpoint — reads server-side env vars so the same Docker
 * image can be promoted across environments without rebuilding.
 *
 * The client fetches this once at app mount via initApiUrl() in api.ts.
 * API_URL must never have a NEXT_PUBLIC_ prefix; it stays server-side only.
 */
export function GET() {
  return NextResponse.json({
    apiUrl: process.env.API_URL || 'http://localhost:8000',
  });
}
