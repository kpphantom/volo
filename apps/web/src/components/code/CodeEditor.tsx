'use client';

import { useState, useRef, useEffect } from 'react';
import { Copy, Check, Download, Maximize2, Minimize2 } from 'lucide-react';

interface CodeEditorProps {
  code: string;
  language?: string;
  onChange?: (code: string) => void;
  readOnly?: boolean;
  filename?: string;
}

const LANGUAGE_COLORS: Record<string, string> = {
  python: 'text-yellow-400',
  javascript: 'text-yellow-300',
  typescript: 'text-blue-400',
  rust: 'text-orange-400',
  go: 'text-cyan-400',
  java: 'text-red-400',
  html: 'text-orange-500',
  css: 'text-blue-300',
  json: 'text-green-400',
  yaml: 'text-red-300',
  bash: 'text-green-300',
  sql: 'text-purple-400',
};

export function CodeEditor({
  code,
  language = 'text',
  onChange,
  readOnly = false,
  filename,
}: CodeEditorProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lines = code.split('\n');

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadFile = () => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `code.${language}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current && !readOnly) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [code, readOnly]);

  // Escape key exits fullscreen
  useEffect(() => {
    if (!expanded) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setExpanded(false);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [expanded]);

  return (
    <div
      className={`bg-[#0d1117] border border-[var(--border)] rounded-xl overflow-hidden ${
        expanded ? 'fixed inset-4 z-50' : ''
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[#161b22]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/60" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
            <div className="w-3 h-3 rounded-full bg-green-500/60" />
          </div>
          <span className={`text-xs font-mono ml-2 ${LANGUAGE_COLORS[language] || 'text-[var(--text-muted)]'}`}>
            {filename || language}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={copyToClipboard}
            className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            title="Copy"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={downloadFile}
            className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            title="Download"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            title={expanded ? 'Minimize' : 'Maximize'}
          >
            {expanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Code area */}
      <div className="flex overflow-auto" style={{ maxHeight: expanded ? '100%' : '400px' }}>
        {/* Line numbers */}
        <div className="flex flex-col py-3 px-3 text-right select-none border-r border-[var(--border)] bg-[#0d1117]">
          {lines.map((_, i) => (
            <span key={i} className="text-xs text-[#484f58] leading-6 font-mono">
              {i + 1}
            </span>
          ))}
        </div>

        {/* Code content */}
        <div className="flex-1 relative">
          {readOnly ? (
            <pre className="p-3 text-sm font-mono text-[#c9d1d9] leading-6 whitespace-pre overflow-x-auto">
              {code}
            </pre>
          ) : (
            <textarea
              ref={textareaRef}
              value={code}
              onChange={(e) => onChange?.(e.target.value)}
              className="w-full p-3 bg-transparent text-sm font-mono text-[#c9d1d9] leading-6 resize-none focus:outline-none"
              spellCheck={false}
            />
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t border-[var(--border)] bg-[#161b22] text-[10px] text-[var(--text-muted)]">
        <span>{lines.length} lines</span>
        <span>{code.length} chars</span>
      </div>
    </div>
  );
}
