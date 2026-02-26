/**
 * Performance validation tests — compare optimized vs pre-optimization patterns.
 *
 * Each test section corresponds to one of the five changes made:
 *   1. ChatMessage: React.memo + stable REMARK_PLUGINS constant
 *   2. ChatArea / ConversationHistory / Sidebar: narrow Zustand selectors
 *   3. navGroups / themeOptions: module-level static constants (reference stability)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, act, cleanup } from '@testing-library/react';
import React, { Profiler } from 'react';
import { useChatStore } from '@/stores/chatStore';
import type { Message } from '@/components/chat/ChatMessage';

// ── Mock dependencies used by ChatMessage ──────────────────────────────────

// Capture remarkPlugins reference on every ReactMarkdown render.
// If REMARK_PLUGINS is a module-level constant, every render passes the SAME array reference.
// If it were inline ([remarkGfm]), each render would pass a NEW array object.
const capturedPluginArrays: unknown[] = [];

vi.mock('react-markdown', () => ({
  default: ({ children, remarkPlugins }: { children: string; remarkPlugins: unknown }) => {
    capturedPluginArrays.push(remarkPlugins);
    return React.createElement('div', { 'data-testid': 'markdown' }, children);
  },
}));

vi.mock('remark-gfm', () => ({ default: vi.fn() }));
vi.mock('@/lib/api', () => ({
  api: { post: vi.fn(), get: vi.fn(), stream: vi.fn() },
}));
vi.mock('sonner', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

// Import ChatMessage AFTER mocks are in place.
import { ChatMessage } from '@/components/chat/ChatMessage';

// ── Helpers ────────────────────────────────────────────────────────────────

const makeMsg = (overrides: Partial<Message> = {}): Message => ({
  id: 'msg-1',
  role: 'assistant',
  content: 'Hello world',
  timestamp: new Date('2024-01-01T00:00:00Z'),
  status: 'sent',
  ...overrides,
});

const resetStore = () =>
  useChatStore.setState({
    messages: [],
    isThinking: false,
    conversationId: null,
    queuedMessage: null,
    abortController: null,
  });

// ── Tests ──────────────────────────────────────────────────────────────────

describe('Frontend performance optimizations', () => {
  beforeEach(() => {
    resetStore();
    capturedPluginArrays.length = 0;
    vi.clearAllMocks();
  });

  afterEach(cleanup);

  // ══════════════════════════════════════════════════════════════════════════
  // 1. ChatMessage — React.memo
  // ══════════════════════════════════════════════════════════════════════════
  describe('ChatMessage — React.memo', () => {
    it('export is wrapped with React.memo', () => {
      // $$typeof === Symbol.for('react.memo') is set by React on every memo'd component.
      // This directly verifies the `memo()` wrapper is present.
      expect((ChatMessage as any).$$typeof).toBe(Symbol.for('react.memo'));
    });

    it('does NOT re-render when parent re-renders but message prop is unchanged', () => {
      /**
       * Strategy: patch ChatMessage.type (the inner function wrapped by memo) with
       * a spy BEFORE mounting.  React reads Component.type from the memo wrapper at
       * reconciliation time to create the inner fiber, so the spy is stored in the
       * fiber and invoked on every actual render of ChatMessage's body.
       *
       * Note: React.Profiler cannot reliably distinguish a memo bailout from a
       * normal render because its onRender fires whenever the Profiler boundary
       * commits an update (even when all children bailed out).  Direct function
       * interception is the only approach that counts actual render-function
       * invocations with certainty.
       */
      const origType = (ChatMessage as any).type;
      let bodyCallCount = 0;

      // Replace inner function with spy BEFORE mounting so React stores it in
      // the fiber.  We forward all calls to the original function so hooks work.
      (ChatMessage as any).type = function ChatMessageSpy(props: any) {
        bodyCallCount++;
        return origType(props);
      };

      try {
        const msg = makeMsg();

        function Parent({ tick }: { tick: number }) {
          void tick;
          return <ChatMessage message={msg} />;
        }

        const { rerender } = render(<Parent tick={0} />);
        expect(bodyCallCount).toBe(1); // initial mount calls the body once

        rerender(<Parent tick={1} />); // parent re-renders, ChatMessage props unchanged
        expect(bodyCallCount).toBe(1); // memo: body NOT invoked again

        rerender(<Parent tick={2} />);
        expect(bodyCallCount).toBe(1); // still exactly 1 execution total
      } finally {
        (ChatMessage as any).type = origType; // restore for other tests
      }
    });

    it('DOES re-render when message content changes (memo is not over-aggressive)', () => {
      const innerFires: string[] = [];

      const { rerender } = render(
        <Profiler id="inner" onRender={() => innerFires.push('render')}>
          <ChatMessage message={makeMsg({ content: 'v1' })} />
        </Profiler>,
      );

      const afterMount = innerFires.length;

      rerender(
        <Profiler id="inner" onRender={() => innerFires.push('render')}>
          <ChatMessage message={makeMsg({ content: 'v2' })} />
        </Profiler>,
      );

      // New prop object → memo must let the render through.
      expect(innerFires.length).toBeGreaterThan(afterMount);
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // 2. REMARK_PLUGINS — module-level constant (reference stability)
  // ══════════════════════════════════════════════════════════════════════════
  describe('REMARK_PLUGINS — module-level constant', () => {
    it('passes the SAME remarkPlugins array reference on every ChatMessage render', () => {
      /**
       * Before: `remarkPlugins={[remarkGfm]}` inside the component → new array each render.
       * After:  `remarkPlugins={REMARK_PLUGINS}` where REMARK_PLUGINS is a module constant
       *         → same array reference across all renders.
       *
       * ReactMarkdown uses referential equality to decide whether to re-process
       * its plugin list, so a stable reference avoids redundant plugin setup.
       */
      const msg = makeMsg();
      const { rerender } = render(<ChatMessage message={msg} />);

      // Force two more renders by passing a new object with the same content.
      rerender(<ChatMessage message={{ ...msg, content: 'updated once' }} />);
      rerender(<ChatMessage message={{ ...msg, content: 'updated twice' }} />);

      expect(capturedPluginArrays.length).toBeGreaterThanOrEqual(2);

      // Every captured reference must be the same object.
      const first = capturedPluginArrays[0];
      for (let i = 1; i < capturedPluginArrays.length; i++) {
        expect(capturedPluginArrays[i]).toBe(first);
      }
    });

    it('inline [remarkGfm] pattern would produce a new array on every render', () => {
      /**
       * Negative control: demonstrate that an inline array produces distinct references.
       * This is the BEFORE state — each render creates a new array object.
       */
      const inlineCaptures: unknown[] = [];
      const remark = {};

      function InlineComponent({ tick }: { tick: number }) {
        void tick;
        // Simulate the old pattern: new array literal on every render
        const plugins = [remark];
        inlineCaptures.push(plugins);
        return React.createElement('div');
      }

      const { rerender } = render(<InlineComponent tick={0} />);
      rerender(<InlineComponent tick={1} />);
      rerender(<InlineComponent tick={2} />);

      expect(inlineCaptures.length).toBe(3);
      // Each render produces a new array reference.
      expect(inlineCaptures[0]).not.toBe(inlineCaptures[1]);
      expect(inlineCaptures[1]).not.toBe(inlineCaptures[2]);
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // 3. Narrow Zustand selectors — re-render isolation
  // ══════════════════════════════════════════════════════════════════════════
  describe('Narrow Zustand selectors', () => {
    it('narrow selector (s => s.messages) does NOT re-render when abortController changes', () => {
      /**
       * Before: `const { messages, isThinking, … } = useChatStore()` — subscribes to
       *         the entire store object; ANY state change triggers a re-render.
       *
       * After:  `const messages = useChatStore(s => s.messages)` — Zustand compares only
       *         `s.messages`; unrelated fields changing no longer cause a re-render.
       */
      let renders = 0;

      function NarrowSubscriber() {
        useChatStore(s => s.messages); // narrow slice
        renders++;
        return React.createElement('div');
      }

      render(React.createElement(NarrowSubscriber));
      const afterMount = renders;

      act(() => {
        useChatStore.setState({ abortController: new AbortController() });
      });

      // abortController changed — but messages didn't — no re-render expected.
      expect(renders).toBe(afterMount);
    });

    it('wide subscription (useChatStore()) DOES re-render when abortController changes', () => {
      /**
       * Demonstrates the old (before) behaviour: a wholesale store subscription
       * re-renders on ANY state change, including unrelated fields.
       */
      let renders = 0;

      function WideSubscriber() {
        useChatStore(); // subscribe to the whole store object
        renders++;
        return React.createElement('div');
      }

      render(React.createElement(WideSubscriber));
      const afterMount = renders;

      act(() => {
        useChatStore.setState({ abortController: new AbortController() });
      });

      // Whole-store subscription → re-rendered even though messages didn't change.
      expect(renders).toBeGreaterThan(afterMount);
    });

    it('quantifies the render-count difference: narrow = 0 extra renders, wide = 1+ extra renders', () => {
      let narrowRenders = 0;
      let wideRenders = 0;

      function Narrow() {
        useChatStore(s => s.messages);
        narrowRenders++;
        return React.createElement('div');
      }

      function Wide() {
        useChatStore();
        wideRenders++;
        return React.createElement('div');
      }

      render(React.createElement(Narrow));
      render(React.createElement(Wide));

      narrowRenders = 0; // reset counters to zero after mount
      wideRenders = 0;

      // Simulate rapid streaming: abortController set/cleared on every message send.
      act(() => { useChatStore.setState({ abortController: new AbortController() }); });
      act(() => { useChatStore.setState({ abortController: null }); });
      act(() => { useChatStore.setState({ abortController: new AbortController() }); });

      // Narrow: messages never changed → 0 extra renders.
      expect(narrowRenders).toBe(0);
      // Wide: re-rendered 3× (once per setState call).
      expect(wideRenders).toBe(3);
    });

    it('narrow selector only fires when its own slice changes', () => {
      let renders = 0;

      function MessagesOnly() {
        const messages = useChatStore(s => s.messages);
        renders++;
        return React.createElement('div', null, String(messages.length));
      }

      render(React.createElement(MessagesOnly));
      const afterMount = renders;

      // Unrelated changes — should NOT trigger re-render.
      act(() => { useChatStore.setState({ isThinking: true }); });
      expect(renders).toBe(afterMount);

      act(() => { useChatStore.setState({ abortController: new AbortController() }); });
      expect(renders).toBe(afterMount);

      act(() => { useChatStore.setState({ conversationId: 'conv-abc' }); });
      expect(renders).toBe(afterMount);

      // Related change — SHOULD trigger re-render.
      act(() => { useChatStore.setState({ messages: [makeMsg()] }); });
      expect(renders).toBe(afterMount + 1);
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // 4. Module-level static arrays (navGroups / themeOptions pattern)
  // ══════════════════════════════════════════════════════════════════════════
  describe('Module-level static array pattern', () => {
    it('module-level constant gives a stable reference across renders', () => {
      /**
       * navGroups (Sidebar) and themeOptions (TopBar) were moved outside their
       * components.  This test demonstrates the general benefit: the same object
       * identity is seen on every render, so child components that receive these
       * arrays as props (or iterate them) don't see phantom prop changes.
       */
      const OUTSIDE = [{ id: 1 }, { id: 2 }]; // simulates module-level constant

      const capturedRefs: unknown[] = [];

      function ConsumerOutside({ tick }: { tick: number }) {
        void tick;
        capturedRefs.push(OUTSIDE); // reference captured each render
        return React.createElement('div');
      }

      const { rerender } = render(React.createElement(ConsumerOutside, { tick: 0 }));
      rerender(React.createElement(ConsumerOutside, { tick: 1 }));
      rerender(React.createElement(ConsumerOutside, { tick: 2 }));

      // All renders see the same array reference.
      expect(capturedRefs[0]).toBe(capturedRefs[1]);
      expect(capturedRefs[1]).toBe(capturedRefs[2]);
    });

    it('inline array literal creates a new reference on every render (the before state)', () => {
      const capturedRefs: unknown[] = [];

      function ConsumerInline({ tick }: { tick: number }) {
        void tick;
        const INSIDE = [{ id: 1 }, { id: 2 }]; // simulates old inline definition
        capturedRefs.push(INSIDE);
        return React.createElement('div');
      }

      const { rerender } = render(React.createElement(ConsumerInline, { tick: 0 }));
      rerender(React.createElement(ConsumerInline, { tick: 1 }));
      rerender(React.createElement(ConsumerInline, { tick: 2 }));

      // Each render produces a distinct array → unstable reference.
      expect(capturedRefs[0]).not.toBe(capturedRefs[1]);
      expect(capturedRefs[1]).not.toBe(capturedRefs[2]);
    });
  });
});
