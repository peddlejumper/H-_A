import { useRef, useEffect } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { Terminal as TerminalIcon, ChevronDown, ChevronUp, Trash2 } from 'lucide-react';

export default function TerminalPanel() {
  const { terminalEntries, showTerminal, toggleTerminal, clearTerminal } = useChatStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [terminalEntries, showTerminal]);

  if (!showTerminal) {
    return (
      <div className="bg-zzw-surface border-t border-zzw-border">
        <button
          onClick={toggleTerminal}
          className="w-full flex items-center gap-2 px-4 py-1.5 text-xs text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2 transition-all"
        >
          <ChevronUp className="w-3.5 h-3.5" />
          <TerminalIcon className="w-3.5 h-3.5" />
          <span>终端</span>
        </button>
      </div>
    );
  }

  return (
    <div className="h-52 bg-zzw-bg border-t border-zzw-border flex flex-col shrink-0 animate-fade-in">
      <div className="flex items-center justify-between px-4 py-1.5 bg-zzw-surface border-b border-zzw-border">
        <button
          onClick={toggleTerminal}
          className="flex items-center gap-2 text-xs text-zzw-text-dim hover:text-zzw-text transition-colors"
        >
          <ChevronDown className="w-3.5 h-3.5" />
          <TerminalIcon className="w-3.5 h-3.5" />
          <span>终端</span>
        </button>
        <div className="flex items-center gap-2">
          {terminalEntries.length > 0 && (
            <button
              onClick={clearTerminal}
              className="text-xs text-zzw-text-dim hover:text-zzw-red transition-colors"
              title="清空终端"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-2 font-mono text-xs">
        {terminalEntries.length === 0 ? (
          <div className="text-zzw-text-dim/40 py-2">
            <span className="text-zzw-cyan">zzw-code ~ </span>
            <span>终端就绪。点击运行按钮执行 H# 代码。</span>
          </div>
        ) : (
          terminalEntries.map((entry) => (
            <div
              key={entry.id}
              className={`py-0.5 ${
                entry.type === 'error' ? 'text-zzw-red' :
                entry.type === 'success' ? 'text-zzw-green' :
                entry.type === 'info' ? 'text-zzw-text-dim' :
                'text-zzw-text'
              }`}
            >
              {entry.type === 'info' && (
                <span className="text-zzw-cyan mr-2">$</span>
              )}
              {entry.type === 'error' && (
                <span className="text-zzw-red mr-2">✗</span>
              )}
              {entry.type === 'success' && (
                <span className="text-zzw-green mr-2">✓</span>
              )}
              {entry.text}
            </div>
          ))
        )}
      </div>
    </div>
  );
}