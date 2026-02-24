import { create } from 'zustand';
import { generateId } from '@/lib/utils';
import type { Message, ToolCall } from '@/components/chat/ChatMessage';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ChatState {
  messages: Message[];
  isThinking: boolean;
  conversationId: string | null;

  // Actions
  sendMessage: (content: string) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  setThinking: (thinking: boolean) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isThinking: false,
  conversationId: null,

  sendMessage: async (content: string) => {
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
      status: 'sent',
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isThinking: true,
    }));

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          conversation_id: get().conversationId,
          messages: get().messages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      if (!response.ok) throw new Error('Failed to get response');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      const assistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        status: 'streaming',
        toolCalls: [],
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isThinking: false,
      }));

      if (reader) {
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') continue;
              try {
                const parsed = JSON.parse(data);

                // Handle text content
                if (parsed.content) {
                  set((state) => ({
                    messages: state.messages.map((m) =>
                      m.id === assistantMessage.id
                        ? { ...m, content: m.content + parsed.content }
                        : m
                    ),
                  }));
                }

                // Handle tool call events
                if (parsed.tool_call) {
                  const tc = parsed.tool_call as ToolCall;
                  set((state) => ({
                    messages: state.messages.map((m) => {
                      if (m.id !== assistantMessage.id) return m;
                      const existing = (m.toolCalls || []).find(
                        (t) => t.id === tc.id
                      );
                      if (existing) {
                        // Update existing tool call status
                        return {
                          ...m,
                          toolCalls: (m.toolCalls || []).map((t) =>
                            t.id === tc.id ? { ...t, ...tc } : t
                          ),
                        };
                      } else {
                        // Add new tool call
                        return {
                          ...m,
                          toolCalls: [...(m.toolCalls || []), tc],
                        };
                      }
                    }),
                  }));
                }

                // Handle conversation ID
                if (parsed.conversation_id) {
                  set({ conversationId: parsed.conversation_id });
                }
              } catch {
                // Skip malformed JSON
              }
            }
          }
        }
      }

      // Mark as sent
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === assistantMessage.id ? { ...m, status: 'sent' } : m
        ),
      }));
    } catch (error) {
      const errorMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content:
          "I'm having trouble connecting to the server. Make sure the API is running on port 8000.",
        timestamp: new Date(),
        status: 'error',
      };

      set((state) => ({
        messages: [...state.messages, errorMessage],
        isThinking: false,
      }));
    }
  },

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  clearMessages: () => set({ messages: [], conversationId: null }),

  setThinking: (thinking) => set({ isThinking: thinking }),
}));
