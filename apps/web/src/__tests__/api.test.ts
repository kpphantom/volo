import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '@/lib/api';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function mockOk(body: unknown, status = 200) {
  return {
    ok: true,
    status,
    json: async () => body,
  };
}

function mockErr(status: number, body: unknown) {
  return {
    ok: false,
    status,
    json: async () => body,
  };
}

describe('ApiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  // ── Auth header injection ─────────────────────────────────────────────────

  describe('Authorization header', () => {
    it('adds Bearer token when present in localStorage', async () => {
      localStorage.setItem('volo-auth', JSON.stringify({ state: { token: 'my-token' } }));
      mockFetch.mockResolvedValue(mockOk({}));

      await api.get('/api/test');

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers['Authorization']).toBe('Bearer my-token');
    });

    it('omits Authorization header when no token stored', async () => {
      mockFetch.mockResolvedValue(mockOk({}));

      await api.get('/api/test');

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers['Authorization']).toBeUndefined();
    });

    it('omits Authorization header when localStorage value is malformed JSON', async () => {
      localStorage.setItem('volo-auth', 'not-valid-json');
      mockFetch.mockResolvedValue(mockOk({}));

      await api.get('/api/test');

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers['Authorization']).toBeUndefined();
    });

    it('omits Authorization header when state.token is missing', async () => {
      localStorage.setItem('volo-auth', JSON.stringify({ state: {} }));
      mockFetch.mockResolvedValue(mockOk({}));

      await api.get('/api/test');

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers['Authorization']).toBeUndefined();
    });
  });

  // ── 401 auto-logout ───────────────────────────────────────────────────────

  describe('401 auto-logout', () => {
    it('removes volo-auth from localStorage and throws "Session expired"', async () => {
      localStorage.setItem('volo-auth', JSON.stringify({ state: { token: 'expired' } }));
      mockFetch.mockResolvedValue(mockErr(401, {}));
      const removeSpy = vi.spyOn(Storage.prototype, 'removeItem');

      await expect(api.get('/api/test')).rejects.toThrow('Session expired. Please log in again.');
      expect(removeSpy).toHaveBeenCalledWith('volo-auth');
    });
  });

  // ── HTTP error handling ───────────────────────────────────────────────────

  describe('HTTP error handling', () => {
    it('throws using detail field from JSON error body', async () => {
      mockFetch.mockResolvedValue(mockErr(400, { detail: 'Bad input' }));
      await expect(api.post('/api/test', {})).rejects.toThrow('Bad input');
    });

    it('throws using message field when detail is absent', async () => {
      mockFetch.mockResolvedValue(mockErr(500, { message: 'Internal error' }));
      await expect(api.post('/api/test', {})).rejects.toThrow('Internal error');
    });

    it('falls back to "HTTP <status>" when response body is not JSON', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => { throw new Error('not json'); },
      });
      await expect(api.get('/api/test')).rejects.toThrow('HTTP 503');
    });
  });

  // ── 204 No Content ────────────────────────────────────────────────────────

  it('returns undefined for 204 No Content responses', async () => {
    mockFetch.mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    const result = await api.delete('/api/test/1');
    expect(result).toBeUndefined();
  });

  // ── HTTP method correctness ───────────────────────────────────────────────

  describe('HTTP methods', () => {
    it('GET uses GET method and sends no body', async () => {
      mockFetch.mockResolvedValue(mockOk({}));
      await api.get('/api/test');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('GET');
      expect(opts.body).toBeUndefined();
    });

    it('POST serializes body as JSON', async () => {
      mockFetch.mockResolvedValue(mockOk({}));
      await api.post('/api/test', { key: 'value' });
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body)).toEqual({ key: 'value' });
    });

    it('PATCH serializes body as JSON', async () => {
      mockFetch.mockResolvedValue(mockOk({}));
      await api.patch('/api/test', { title: 'new' });
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('PATCH');
      expect(JSON.parse(opts.body)).toEqual({ title: 'new' });
    });

    it('PUT serializes body as JSON', async () => {
      mockFetch.mockResolvedValue(mockOk({}));
      await api.put('/api/test', { value: 1 });
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('PUT');
      expect(JSON.parse(opts.body)).toEqual({ value: 1 });
    });

    it('DELETE uses DELETE method and sends no body', async () => {
      mockFetch.mockResolvedValue(mockOk({}));
      await api.delete('/api/test/1');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('DELETE');
      expect(opts.body).toBeUndefined();
    });
  });

  // ── AbortSignal ───────────────────────────────────────────────────────────

  it('passes AbortSignal to fetch', async () => {
    const controller = new AbortController();
    mockFetch.mockResolvedValue(mockOk({}));

    await api.get('/api/test', controller.signal);

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.signal).toBe(controller.signal);
  });

  // ── stream() ──────────────────────────────────────────────────────────────

  describe('stream()', () => {
    it('returns the raw Response on success', async () => {
      const fakeResponse = { ok: true, status: 200, body: 'stream' };
      mockFetch.mockResolvedValue(fakeResponse);

      const result = await api.stream('/api/chat', { message: 'hi' });
      expect(result).toBe(fakeResponse);
    });

    it('throws on non-ok stream response', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 503 });
      await expect(api.stream('/api/chat', {})).rejects.toThrow('Stream request failed: 503');
    });

    it('includes auth token in stream request', async () => {
      localStorage.setItem('volo-auth', JSON.stringify({ state: { token: 'stream-tok' } }));
      mockFetch.mockResolvedValue({ ok: true, status: 200, body: null });

      await api.stream('/api/chat', {});

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers['Authorization']).toBe('Bearer stream-tok');
    });

    it('passes AbortSignal to stream fetch', async () => {
      const controller = new AbortController();
      mockFetch.mockResolvedValue({ ok: true, status: 200, body: null });

      await api.stream('/api/chat', {}, controller.signal);

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.signal).toBe(controller.signal);
    });
  });
});
