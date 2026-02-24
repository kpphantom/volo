'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { GripVertical } from 'lucide-react';

interface SplitPaneProps {
  left: React.ReactNode;
  right: React.ReactNode;
  defaultSplit?: number; // 0-100 percentage
  minLeft?: number;
  minRight?: number;
}

export function SplitPane({
  left,
  right,
  defaultSplit = 50,
  minLeft = 20,
  minRight = 20,
}: SplitPaneProps) {
  const [split, setSplit] = useState(defaultSplit);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const newSplit = ((e.clientX - rect.left) / rect.width) * 100;
      setSplit(Math.max(minLeft, Math.min(100 - minRight, newSplit)));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, minLeft, minRight]);

  return (
    <div
      ref={containerRef}
      className="flex h-full w-full overflow-hidden"
      style={{ cursor: isDragging ? 'col-resize' : undefined }}
    >
      {/* Left pane */}
      <div style={{ width: `${split}%` }} className="overflow-auto">
        {left}
      </div>

      {/* Divider */}
      <div
        onMouseDown={handleMouseDown}
        className={`w-1.5 flex-shrink-0 cursor-col-resize flex items-center justify-center hover:bg-blue-500/20 transition-colors ${
          isDragging ? 'bg-blue-500/30' : 'bg-[var(--border)]'
        }`}
      >
        <GripVertical className="w-3 h-3 text-[var(--text-muted)]" />
      </div>

      {/* Right pane */}
      <div style={{ width: `${100 - split}%` }} className="overflow-auto">
        {right}
      </div>
    </div>
  );
}
