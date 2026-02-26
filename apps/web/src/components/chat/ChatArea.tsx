'use client';

import { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react';
import { Mic, Paperclip, ArrowUp, ArrowDown, Square, AudioLines } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatMessage, Message } from './ChatMessage';
import { WelcomeScreen } from './WelcomeScreen';
import { ThinkingIndicator } from './ThinkingIndicator';
import { VoiceMode } from './VoiceMode';
import { useChatStore } from '@/stores/chatStore';
import { toast } from 'sonner';

export function ChatArea() {
  const messages         = useChatStore(s => s.messages);
  const isThinking       = useChatStore(s => s.isThinking);
  const sendMessage      = useChatStore(s => s.sendMessage);
  const queuedMessage    = useChatStore(s => s.queuedMessage);
  const setQueuedMessage = useChatStore(s => s.setQueuedMessage);
  const stopGenerating   = useChatStore(s => s.stopGenerating);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [showScrollDown, setShowScrollDown] = useState(false);
  const [isKeyboardOpen, setIsKeyboardOpen] = useState(false);
  const [voiceModeOpen, setVoiceModeOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // ─── Scroll management (Telegram-style) ───
  const scrollToBottom = useCallback((instant = false) => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: instant ? 'instant' : 'smooth',
      });
    }
  }, []);

  // Auto-scroll on new messages (only if already near bottom)
  useEffect(() => {
    if (!messagesContainerRef.current) return;
    const el = messagesContainerRef.current;
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150;
    if (isNearBottom) {
      scrollToBottom();
    }
  }, [messages, isThinking, scrollToBottom]);

  // Initial scroll to bottom when messages first load
  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom(true);
    }
  }, [messages.length, scrollToBottom]);

  // Track scroll position for "scroll to bottom" button
  useEffect(() => {
    // Process queued messages from other pages (e.g. Dashboard quick actions)
    if (queuedMessage) {
      sendMessage(queuedMessage);
      setQueuedMessage(null);
    }
  }, [queuedMessage, sendMessage, setQueuedMessage]);

  useEffect(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const handleScroll = () => {
      const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      setShowScrollDown(distFromBottom > 200);
    };
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  // ─── Mobile keyboard detection via visualViewport ───
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;

    const onResize = () => {
      const keyboardUp = vv.height < window.innerHeight * 0.75;
      setIsKeyboardOpen(keyboardUp);
      // On iOS, scroll the input into view when keyboard opens
      if (keyboardUp && textareaRef.current) {
        requestAnimationFrame(() => {
          textareaRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        });
      }
    };

    vv.addEventListener('resize', onResize);
    return () => vv.removeEventListener('resize', onResize);
  }, []);

  // ─── Auto-resize textarea ───
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const maxH = window.innerWidth < 640 ? 120 : 200;
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, maxH)}px`;
    }
  }, [input]);

  // ─── Speech recognition ───
  const toggleRecording = useCallback(() => {
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
        const base = prev.replace(/\[listening\.\.\.\]$/, '').trim();
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

  // ─── File attachment ───
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;

    const file = files[0];
    const maxSize = 10 * 1024 * 1024;

    if (file.size > maxSize) {
      toast.error('File too large (max 10MB)');
      return;
    }

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
      setInput((prev) => prev + `\n\n📎 Attached: **${file.name}** (${(file.size / 1024).toFixed(1)}KB, ${file.type || 'unknown type'})`);
      toast.success(`Referenced: ${file.name}`);
    }

    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  // ─── Send ───
  const handleSend = useCallback(() => {
    if (!input.trim() || isThinking) return;
    sendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    // Scroll to bottom after sending
    requestAnimationFrame(() => scrollToBottom());
  }, [input, isThinking, sendMessage, scrollToBottom]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const showWelcome = messages.length === 0;

  return (
    <div
      ref={chatContainerRef}
      className="flex-1 flex flex-col min-h-0 relative"
    >
      {/* Messages Area */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto overscroll-contain scroll-smooth-touch scrollbar-hide"
      >
        {showWelcome ? (
          <WelcomeScreen onSuggestionClick={(text) => {
            setInput(text);
            textareaRef.current?.focus();
          }} />
        ) : (
          <div className="max-w-3xl mx-auto px-3 sm:px-4 py-4 sm:py-6 space-y-1">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isThinking && <ThinkingIndicator />}
            <div ref={messagesEndRef} className="h-1" />
          </div>
        )}
      </div>

      {/* Scroll to bottom FAB */}
      {showScrollDown && !showWelcome && (
        <button
          onClick={() => scrollToBottom()}
          className="absolute bottom-24 sm:bottom-28 right-4 sm:right-6 z-10 w-10 h-10 rounded-full bg-surface-dark-2 border border-white/10 flex items-center justify-center shadow-lg shadow-black/30 hover:bg-surface-dark-3 transition-all animate-fade-in tap-none active:scale-95"
          aria-label="Scroll to bottom"
        >
          <ArrowDown className="w-4 h-4 text-zinc-400" />
        </button>
      )}

      {/* Input Area — sticky bottom, above keyboard */}
      <div className={cn(
        'chat-input-container border-t border-white/5 bg-surface-dark-1/80 backdrop-blur-xl',
        isKeyboardOpen && 'pb-0'
      )}>
        {/* Stop generating button */}
        {isThinking && (
          <div className="flex justify-center pt-2">
            <button
              onClick={() => stopGenerating()}
              className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 transition-colors text-xs text-zinc-400 hover:text-zinc-200 active:scale-95"
            >
              <Square className="w-3 h-3 fill-current" />
              Stop generating
            </button>
          </div>
        )}

        <div className="max-w-3xl mx-auto px-2 sm:px-4 py-2 sm:py-3">
          <div className="relative flex items-end gap-1 sm:gap-2 rounded-2xl bg-surface-dark-2 border border-white/10 focus-within:border-brand-500/50 transition-colors">
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
              className="p-2.5 sm:p-3 text-zinc-500 hover:text-zinc-300 active:text-zinc-200 transition-colors tap-none flex-shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center"
              title="Attach file"
              aria-label="Attach file"
            >
              <Paperclip className="w-5 h-5 sm:w-4 sm:h-4" />
            </button>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => {
                // On mobile, scroll to bottom when input is focused
                if (window.innerWidth < 640) {
                  requestAnimationFrame(() => scrollToBottom());
                }
              }}
              placeholder="Message Volo..."
              rows={1}
              className="flex-1 py-2.5 sm:py-3 bg-transparent text-zinc-200 placeholder-zinc-600 resize-none outline-none text-[16px] sm:text-sm leading-relaxed max-h-[120px] sm:max-h-[200px]"
              style={{ fontSize: '16px' }} // Prevents iOS zoom on focus
              enterKeyHint="send"
              autoComplete="off"
            />

            {/* Right side buttons */}
            <div className="flex items-center gap-0.5 p-1.5 sm:p-2 flex-shrink-0">
              {/* Voice / Send / Dictate */}
              {!input.trim() ? (
                <>
                  {/* Dictate (speech-to-text) */}
                  <button
                    onClick={toggleRecording}
                    className={cn(
                      'p-2.5 sm:p-2 rounded-full transition-all tap-none active:scale-95 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 flex items-center justify-center',
                      isRecording
                        ? 'bg-red-500/20 text-red-400 animate-pulse-soft'
                        : 'text-zinc-500 hover:text-zinc-300 active:text-zinc-200'
                    )}
                    title={isRecording ? 'Stop recording' : 'Dictate'}
                    aria-label={isRecording ? 'Stop recording' : 'Dictate — type with your voice'}
                  >
                    <Mic className="w-5 h-5 sm:w-4 sm:h-4" />
                  </button>

                  {/* Voice Chat (full-screen voice mode) */}
                  <button
                    onClick={() => setVoiceModeOpen(true)}
                    className="p-2.5 sm:p-2 rounded-full bg-brand-600/10 text-brand-400 hover:bg-brand-600/20 active:bg-brand-600/30 transition-all tap-none active:scale-95 flex min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 items-center justify-center"
                    title="Voice Chat"
                    aria-label="Open voice chat — talk hands-free"
                  >
                    <AudioLines className="w-5 h-5 sm:w-4 sm:h-4" />
                  </button>
                </>
              ) : (
                /* Send — show when input has text */
                <button
                  onClick={handleSend}
                  disabled={isThinking}
                  className={cn(
                    'p-2.5 sm:p-2 rounded-full transition-all tap-none active:scale-90 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 flex items-center justify-center',
                    !isThinking
                      ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/20 hover:bg-brand-500'
                      : 'bg-zinc-700 text-zinc-500 cursor-not-allowed'
                  )}
                  aria-label="Send message"
                >
                  <ArrowUp className="w-5 h-5 sm:w-4 sm:h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Bottom hint — desktop only */}
          <p className="hidden sm:block text-[10px] text-zinc-600 text-center mt-1.5">
            Press{' '}
            <kbd className="px-1 py-0.5 rounded bg-white/5 font-mono text-[9px]">Enter</kbd> to send,{' '}
            <kbd className="px-1 py-0.5 rounded bg-white/5 font-mono text-[9px]">Shift+Enter</kbd> for new line
          </p>
        </div>
      </div>

      {/* Voice Mode Overlay */}
      <VoiceMode isOpen={voiceModeOpen} onClose={() => setVoiceModeOpen(false)} />
    </div>
  );
}
