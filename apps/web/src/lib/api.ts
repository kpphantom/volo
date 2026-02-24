/**
 * Centralized API client for Volo
 * All API calls go through here — no more hardcoded URLs
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', body, headers = {}, signal } = options;

    const config: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
      signal,
    };

    if (body && method !== 'GET') {
      config.body = JSON.stringify(body);
    }

    const res = await fetch(`${this.baseUrl}${endpoint}`, config);

    if (!res.ok) {
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
  async stream(endpoint: string, body?: unknown): Promise<Response> {
    const res = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`Stream request failed: ${res.status}`);
    return res;
  }

  get url() {
    return this.baseUrl;
  }
}

export const api = new ApiClient(API_URL);
export { API_URL };
