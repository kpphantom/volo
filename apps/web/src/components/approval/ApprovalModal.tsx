'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { ShieldAlert, Check, X, AlertTriangle } from 'lucide-react';

interface ApprovalModalProps {
  isOpen: boolean;
  onApprove: () => void;
  onDeny: () => void;
  action: {
    tool: string;
    description: string;
    parameters?: Record<string, unknown>;
    risk?: 'low' | 'medium' | 'high';
  };
}

const riskColors = {
  low: 'text-green-400 bg-green-500/10 border-green-500/30',
  medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  high: 'text-red-400 bg-red-500/10 border-red-500/30',
};

export function ApprovalModal({ isOpen, onApprove, onDeny, action }: ApprovalModalProps) {
  const risk = action.risk || 'medium';

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onDeny}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative bg-[var(--bg-secondary)] border border-[var(--border)] rounded-2xl w-full max-w-md shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center gap-3 p-6 pb-4">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${riskColors[risk]}`}>
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                  Approval Required
                </h3>
                <p className="text-sm text-[var(--text-muted)]">
                  Volo wants to perform an action
                </p>
              </div>
            </div>

            {/* Action Details */}
            <div className="px-6 pb-4">
              <div className="bg-[var(--bg-primary)] border border-[var(--border)] rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded">
                    {action.tool}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded border ${riskColors[risk]}`}>
                    {risk} risk
                  </span>
                </div>
                <p className="text-sm text-[var(--text-primary)]">
                  {action.description}
                </p>
                {action.parameters && Object.keys(action.parameters).length > 0 && (
                  <div className="mt-3 space-y-1">
                    {Object.entries(action.parameters).map(([k, v]) => (
                      <div key={k} className="flex gap-2 text-xs">
                        <span className="text-[var(--text-muted)]">{k}:</span>
                        <span className="text-[var(--text-secondary)] font-mono">
                          {typeof v === 'string' ? v : JSON.stringify(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {risk === 'high' && (
                <div className="flex items-start gap-2 mt-3 text-xs text-yellow-400">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>This action may have significant consequences. Review carefully.</span>
                </div>
              )}
            </div>

            {/* Buttons */}
            <div className="flex gap-3 p-6 pt-2">
              <button
                onClick={onDeny}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[var(--border)] text-[var(--text-secondary)] rounded-lg hover:bg-[var(--bg-primary)] transition-colors"
              >
                <X className="w-4 h-4" /> Deny
              </button>
              <button
                onClick={onApprove}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                <Check className="w-4 h-4" /> Approve
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
