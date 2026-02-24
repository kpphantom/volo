'use client';

import { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react';
import { Send, Mic, Paperclip, Sparkles, Brain, ArrowUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatMessage, Message } from './ChatMessage';
import { WelcomeScreen } from './WelcomeScreen';
import { ThinkingIndicator } from './ThinkingIndicator';
import { useChatStore } from '@/stores/chatStore';
import { toast } from 'sonner';

export function ChatArea() {
  const { messages, isThinking, sendMessage } = useChatStore();
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  // Speech recognition setup
  const toggleRecording = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    const SpeechRecognition = w.SpeechRecognition || w.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      toast.error('Speech recognition not supported in this browser');
      return;
    }

    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      let transcript = '';
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setInput((prev) => {
        // Replace interim results, keep any existing text
        const base = prev.replace(/\[listening...\]$/, '').trim();
        return base ? `${base} ${transcript}` : transcript;
      });
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      toast.error(`Mic error: ${event.error}`);
      setIsRecording(false);
    };

    recognition.onend = () => {
      setIsRecording(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsRecording(true);
    toast.info('Listening... speak now');
  }, [isRecording]);

  // File attachment handler
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;

    const file = files[0];
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (file.size > maxSize) {
      toast.error('File too large (max 10MB)');
      return;
    }

    // For text files, read and insert content
    if (file.type.startsWith('text/') || file.name.match(/\.(json|md|csv|yaml|yml|xml|html|css|js|ts|py|sh|sql)$/i)) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const content = ev.target?.result as string;
        const attachment = `\n\n📎 **${file.name}** (${(file.size / 1024).toFixed(1)}KB):\n\`\`\`\n${content.slice(0, 5000)}${content.length > 5000 ? '\n... (truncated)' : ''}\n\`\`\``;
        setInput((prev) => prev + attachment);
        toast.success(`Attached: ${file.name}`);
      };
      reader.readAsText(file);
    } else {
      // For non-text files, just reference them
      setInput((prev) => prev + `\n\n📎 Attached: **${file.name}** (${(file.size / 1024).toFixed(1)}KB, ${file.type || 'unknown type'})`);
      toast.success(`Referenced: ${file.name}`);
    }

    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const handleSend = () => {
    if (!input.trim() || isThinking) return;
    sendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const showWelcome = messages.length === 0;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        {showWelcome ? (
          <WelcomeScreen onSuggestionClick={(text) => {
            setInput(text);
            textareaRef.current?.focus();
          }} />
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isThinking && <ThinkingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-white/5 bg-surface-dark-1/30 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="relative flex items-end gap-2 rounded-2xl bg-surface-dark-2 border border-white/10 focus-within:border-brand-500/50 transition-colors">
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileSelect}
              accept=".txt,.md,.json,.csv,.yaml,.yml,.xml,.html,.css,.js,.ts,.py,.sh,.sql,.pdf,.png,.jpg,.jpeg,.gif,.webp,.svg"
            />

            {/* Attach */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-3 text-zinc-500 hover:text-zinc-300 transition-colors"
              title="Attach file"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Talk to Volo..."
              rows={1}
              className="flex-1 py-3 bg-transparent text-zinc-200 placeholder-zinc-600 resize-none outline-none text-sm leading-relaxed max-h-[200px]"
            />

            {/* Right side buttons */}
            <div className="flex items-center gap-1 p-2">
              {/* Voice */}
              <button
                onClick={toggleRecording}
                className={cn(
                  'p-2 rounded-lg transition-colors',
                  isRecording
                    ? 'bg-red-500/20 text-red-400 animate-pulse-soft'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
                )}
                title={isRecording ? 'Stop recording' : 'Voice input'}
              >
                <Mic className="w-4 h-4" />
              </button>

              {/* Send */}
              <button
                onClick={handleSend}
                disabled={!input.trim() || isThinking}
                className={cn(
                  'p-2 rounded-lg transition-all',
                  input.trim() && !isThinking
                    ? 'bg-brand-600 text-white hover:bg-brand-500'
                    : 'text-zinc-600 cursor-not-allowed'
                )}
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Bottom hint */}
          <p className="text-[10px] text-zinc-600 text-center mt-2">
            Volo can make mistakes. Verify important actions. Press{' '}
            <kbd className="px-1 py-0.5 rounded bg-white/5 font-mono">Enter</kbd> to send,{' '}
            <kbd className="px-1 py-0.5 rounded bg-white/5 font-mono">Shift+Enter</kbd> for new line.
          </p>
        </div>
      </div>
    </div>
  );
}
