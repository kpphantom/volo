/**
 * Centralized API client for Volo
 *
 * The API base URL is no longer baked into the bundle at build time.
 * Instead, initApiUrl() fetches /api/config (a Next.js server-side route)
 * at app mount, which reads process.env.API_URL at runtime. This lets the
 * same Docker image run in any environment without a rebuild.
 *
 * Call initApiUrl() once in the root component useEffect before any other
 * API calls. Until it resolves, requests fall back to http://localhost:8000.
 */

// Module-level URL — written once by initApiUrl(), read by every request.
let _apiUrl = 'http://localhost:8000';

/**
 * Fetch the runtime API URL from the Next.js config route and store it.
 * Safe to call multiple times — only the first call performs the fetch.
 */
export async function initApiUrl(): Promise<void> {
  if (typeof window === 'undefined') return;
  try {
    const res = await fetch('/runtime-config');
    if (res.ok) {
      const { apiUrl } = await res.json();
      if (apiUrl) _apiUrl = apiUrl;
    }
  } catch {
    // Network unavailable during init — keep localhost default.
  }
}

/** Get auth token from persisted Zustand store without importing the store (avoids circular deps) */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem('volo-auth');
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.state?.token || null;
  } catch {
    return null;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

class ApiClient {
  private async request<T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', body, headers = {}, signal } = options;

    const token = getAuthToken();
    const config: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      signal,
    };

    if (body && method !== 'GET') {
      config.body = JSON.stringify(body);
    }

    const res = await fetch(`${_apiUrl}${endpoint}`, config);

    if (!res.ok) {
      // Auto-logout on 401 Unauthorized
      if (res.status === 401) {
        try {
          localStorage.removeItem('volo-auth');
          window.location.href = '/';
        } catch {}
        throw new Error('Session expired. Please log in again.');
      }
      const error = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(error.detail || error.message || `Request failed: ${res.status}`);
    }

    // Handle 204 No Content
    if (res.status === 204) return undefined as T;

    return res.json();
  }

  get<T = unknown>(endpoint: string, signal?: AbortSignal) {
    return this.request<T>(endpoint, { signal });
  }

  post<T = unknown>(endpoint: string, body?: unknown) {
    return this.request<T>(endpoint, { method: 'POST', body });
  }

  patch<T = unknown>(endpoint: string, body?: unknown) {
    return this.request<T>(endpoint, { method: 'PATCH', body });
  }

  put<T = unknown>(endpoint: string, body?: unknown) {
    return this.request<T>(endpoint, { method: 'PUT', body });
  }

  delete<T = unknown>(endpoint: string) {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  /** Get the raw Response for streaming endpoints */
  async stream(endpoint: string, body?: unknown, signal?: AbortSignal): Promise<Response> {
    const token = getAuthToken();
    const res = await fetch(`${_apiUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
    if (!res.ok) throw new Error(`Stream request failed: ${res.status}`);
    return res;
  }

  get url() {
    return _apiUrl;
  }
}

export const api = new ApiClient();

/** Current resolved API URL — updated by initApiUrl(). */
export { _apiUrl as API_URL };
