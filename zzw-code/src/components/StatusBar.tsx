import { useUIStore } from '@/stores/uiStore';
import { AlignLeft, Circle } from 'lucide-react';

export default function StatusBar() {
  const { statusBar } = useUIStore();

  return (
    <div className="h-6 bg-zzw-surface border-t border-zzw-border flex items-center px-3 justify-between text-[10px] select-none shrink-0">
      <div className="flex items-center gap-4">
        <span className="text-zzw-text-dim">
          Ln {statusBar.line}, Col {statusBar.col}
        </span>
        <span className="text-zzw-text-dim">
          {statusBar.language}
        </span>
        <span className="text-zzw-text-dim">
          UTF-8
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-zzw-text-dim">
          共 {statusBar.totalLines} 行
        </span>
        <span className="text-zzw-text-dim">
          LF
        </span>
      </div>
    </div>
  );
}