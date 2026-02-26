import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/api', () => ({
  api: { stream: vi.fn() },
}));

import { api } from '@/lib/api';
import { useChatStore } from '@/stores/chatStore';
import type { Message } from '@/components/chat/ChatMessage';

const mockStream = vi.mocked(api.stream);

/** Build a ReadableStream that emits SSE events then closes */
function sseBody(...events: object[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const ev of events) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(ev)}\n\n`));
      }
      controller.enqueue(encoder.encode('data: [DONE]\n\n'));
      controller.close();
    },
  });
}

function streamOk(...events: object[]) {
  return Promise.resolve({ ok: true, body: sseBody(...events) });
}

const baseMsg = (overrides: Partial<Message> = {}): Message => ({
  id: '1',
  role: 'user',
  content: 'hi',
  timestamp: new Date(),
  status: 'sent',
  ...overrides,
});

describe('chatStore', () => {
  beforeEach(() => {
    useChatStore.setState({
      messages: [],
      isThinking: false,
      conversationId: null,
      queuedMessage: null,
      abortController: null,
    });
    vi.clearAllMocks();
  });

  // ── addMessage ────────────────────────────────────────────────────────────

  describe('addMessage()', () => {
    it('appends a message to the list', () => {
      const msg = baseMsg();
      useChatStore.getState().addMessage(msg);
      expect(useChatStore.getState().messages).toHaveLength(1);
      expect(useChatStore.getState().messages[0]).toEqual(msg);
    });

    it('preserves existing messages', () => {
      useChatStore.getState().addMessage(baseMsg({ id: '1' }));
      useChatStore.getState().addMessage(baseMsg({ id: '2', role: 'assistant' }));
      expect(useChatStore.getState().messages).toHaveLength(2);
    });
  });

  // ── clearMessages ─────────────────────────────────────────────────────────

  describe('clearMessages()', () => {
    it('empties the message list', () => {
      useChatStore.setState({ messages: [baseMsg()] });
      useChatStore.getState().clearMessages();
      expect(useChatStore.getState().messages).toHaveLength(0);
    });

    it('resets conversationId to null', () => {
      useChatStore.setState({ conversationId: 'conv-1' });
      useChatStore.getState().clearMessages();
      expect(useChatStore.getState().conversationId).toBeNull();
    });
  });

  // ── setQueuedMessage ──────────────────────────────────────────────────────

  describe('setQueuedMessage()', () => {
    it('sets a queued message', () => {
      useChatStore.getState().setQueuedMessage('pending');
      expect(useChatStore.getState().queuedMessage).toBe('pending');
    });

    it('clears the queued message', () => {
      useChatStore.setState({ queuedMessage: 'pending' });
      useChatStore.getState().setQueuedMessage(null);
      expect(useChatStore.getState().queuedMessage).toBeNull();
    });
  });

  // ── stopGenerating ────────────────────────────────────────────────────────

  describe('stopGenerating()', () => {
    it('calls abort() on the current controller', () => {
      const controller = new AbortController();
      const spy = vi.spyOn(controller, 'abort');
      useChatStore.setState({ abortController: controller });

      useChatStore.getState().stopGenerating();

      expect(spy).toHaveBeenCalled();
    });

    it('is a no-op when no controller is set', () => {
      expect(() => useChatStore.getState().stopGenerating()).not.toThrow();
    });
  });

  // ── sendMessage ───────────────────────────────────────────────────────────

  describe('sendMessage()', () => {
    it('adds the user message immediately', async () => {
      mockStream.mockReturnValue(streamOk({ content: 'Hi' }));

      await (useChatStore.getState().sendMessage('Hello') as any);

      const msgs = useChatStore.getState().messages;
      expect(msgs[0].role).toBe('user');
      expect(msgs[0].content).toBe('Hello');
    });

    it('adds an assistant message with streamed content', async () => {
      mockStream.mockReturnValue(
        streamOk({ content: 'Hello ' }, { content: 'world!' }),
      );

      await (useChatStore.getState().sendMessage('Hi') as any);

      const assistant = useChatStore.getState().messages.find((m) => m.role === 'assistant')!;
      expect(assistant.content).toBe('Hello world!');
      expect(assistant.status).toBe('sent');
    });

    it('is not isThinking after completion', async () => {
      mockStream.mockReturnValue(streamOk({ content: 'Done' }));

      await (useChatStore.getState().sendMessage('hi') as any);

      expect(useChatStore.getState().isThinking).toBe(false);
    });

    it('stores conversationId from SSE event', async () => {
      mockStream.mockReturnValue(
        streamOk({ conversation_id: 'conv-xyz' }, { content: 'Hi' }),
      );

      await (useChatStore.getState().sendMessage('Hello') as any);

      expect(useChatStore.getState().conversationId).toBe('conv-xyz');
    });

    it('adds a new tool call from SSE', async () => {
      const tc = { id: 'tc-1', name: 'search', status: 'running', input: {}, result: null };
      mockStream.mockReturnValue(streamOk({ tool_call: tc }));

      await (useChatStore.getState().sendMessage('search') as any);

      const assistant = useChatStore.getState().messages.find((m) => m.role === 'assistant')!;
      expect(assistant.toolCalls).toHaveLength(1);
      expect(assistant.toolCalls![0].id).toBe('tc-1');
    });

    it('updates an existing tool call rather than duplicating it', async () => {
      const tc1 = { id: 'tc-1', name: 'search', status: 'running', input: {}, result: null };
      const tc2 = { id: 'tc-1', name: 'search', status: 'done', input: {}, result: 'results' };
      mockStream.mockReturnValue(streamOk({ tool_call: tc1 }, { tool_call: tc2 }));

      await (useChatStore.getState().sendMessage('search') as any);

      const assistant = useChatStore.getState().messages.find((m) => m.role === 'assistant')!;
      expect(assistant.toolCalls).toHaveLength(1);
      expect(assistant.toolCalls![0].status).toBe('done');
    });

    it('skips malformed SSE JSON and continues streaming', async () => {
      const encoder = new TextEncoder();
      const body = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: not-valid-json\n\n'));
          controller.enqueue(encoder.encode('data: {"content":"ok"}\n\n'));
          controller.close();
        },
      });
      mockStream.mockResolvedValue({ ok: true, body });

      await expect(
        useChatStore.getState().sendMessage('hi') as any,
      ).resolves.not.toThrow();

      const assistant = useChatStore.getState().messages.find((m) => m.role === 'assistant')!;
      expect(assistant.content).toBe('ok');
    });

    it('adds an error message on stream failure', async () => {
      mockStream.mockRejectedValue(new Error('Network error'));

      await (useChatStore.getState().sendMessage('Hello') as any);

      const errMsg = useChatStore.getState().messages.find((m) => m.status === 'error')!;
      expect(errMsg).toBeDefined();
      expect(errMsg.role).toBe('assistant');
      expect(useChatStore.getState().isThinking).toBe(false);
    });

    it('handles AbortError before assistant message is created — no error message added', async () => {
      const abortError = new DOMException('Aborted', 'AbortError');
      mockStream.mockRejectedValue(abortError);

      await (useChatStore.getState().sendMessage('hi') as any);

      const msgs = useChatStore.getState().messages;
      // User message is present, no error message
      expect(msgs).toHaveLength(1);
      expect(msgs[0].role).toBe('user');
      expect(msgs.find((m) => m.status === 'error')).toBeUndefined();
      expect(useChatStore.getState().isThinking).toBe(false);
    });

    it('passes conversationId to the API on subsequent messages', async () => {
      useChatStore.setState({ conversationId: 'existing-conv' });
      mockStream.mockReturnValue(streamOk({ content: 'Hi' }));

      await (useChatStore.getState().sendMessage('follow up') as any);

      const [, body] = mockStream.mock.calls[0];
      expect((body as any).conversation_id).toBe('existing-conv');
    });
  });
});
