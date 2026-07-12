import { useMemo } from 'react';
import { useFileStore } from '@/stores/fileStore';
import { useUIStore } from '@/stores/uiStore';
import { X, Function, ListTree, Variable, Hash, Type } from 'lucide-react';

interface OutlineItem {
  type: 'function' | 'class' | 'variable' | 'import';
  name: string;
  line: number;
}

export default function OutlinePanel() {
  const { files, activeFileId } = useFileStore();
  const { outlineOpen, setOutlineOpen } = useUIStore();
  const activeFile = files.find((f) => f.id === activeFileId);

  const outline = useMemo(() => {
    if (!activeFile) return [];
    const items: OutlineItem[] = [];
    const lines = activeFile.content.split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // 函数定义
      const fnMatch = line.match(/^\s*fn\s+(\w+)\s*\(/);
      if (fnMatch) {
        items.push({ type: 'function', name: fnMatch[1], line: i + 1 });
        continue;
      }

      // 类定义
      const classMatch = line.match(/^\s*class\s+(\w+)/);
      if (classMatch) {
        items.push({ type: 'class', name: classMatch[1], line: i + 1 });
        continue;
      }

      // import 语句
      const importMatch = line.match(/^\s*import\s+["']([^"']+)["']/);
      if (importMatch) {
        items.push({ type: 'import', name: importMatch[1], line: i + 1 });
        continue;
      }

      // let 声明
      const letMatch = line.match(/^\s*let\s+(\w+)\s*=/);
      if (letMatch) {
        items.push({ type: 'variable', name: letMatch[1], line: i + 1 });
      }
    }

    return items;
  }, [activeFile]);

  if (!outlineOpen) return null;

  const getIcon = (type: OutlineItem['type']) => {
    switch (type) {
      case 'function': return <Function className="w-3 h-3 text-zzw-purple" />;
      case 'class': return <Type className="w-3 h-3 text-zzw-yellow" />;
      case 'variable': return <Variable className="w-3 h-3 text-zzw-cyan" />;
      case 'import': return <Hash className="w-3 h-3 text-zzw-text-dim" />;
    }
  };

  const handleGoToLine = (line: number) => {
    // 通过 DOM 事件触发 editor 跳转
    const event = new CustomEvent('goto-line', { detail: { line } });
    window.dispatchEvent(event);
  };

  return (
    <div className="w-48 bg-zzw-surface border-l border-zzw-border flex flex-col shrink-0 animate-fade-in">
      <div className="flex items-center justify-between px-3 py-2 border-b border-zzw-border">
        <div className="flex items-center gap-2">
          <ListTree className="w-3.5 h-3.5 text-zzw-text-dim" />
          <span className="text-xs font-medium text-zzw-text">大纲</span>
        </div>
        <button
          onClick={() => setOutlineOpen(false)}
          className="w-5 h-5 rounded flex items-center justify-center text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2 transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-1">
        {outline.length === 0 ? (
          <div className="px-3 py-6 text-center">
            <p className="text-xs text-zzw-text-dim">无结构信息</p>
          </div>
        ) : (
          outline.map((item, i) => (
            <button
              key={i}
              onClick={() => handleGoToLine(item.line)}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-zzw-surface2 transition-colors group"
            >
              {getIcon(item.type)}
              <span className="text-xs text-zzw-text-dim truncate flex-1">{item.name}</span>
              <span className="text-[10px] text-zzw-text-dim/50 opacity-0 group-hover:opacity-100 transition-opacity">
                L{item.line}
              </span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}