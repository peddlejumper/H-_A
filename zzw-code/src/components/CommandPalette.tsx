import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useFileStore } from '@/stores/fileStore';
import { useUIStore } from '@/stores/uiStore';
import { useChatStore } from '@/stores/chatStore';
import {
  Search, File, Play, Settings, Terminal, Code2, PanelRight,
  FilePlus, FolderOpen, X, ChevronRight, Zap,
} from 'lucide-react';
import type { CommandItem } from '@/types';

export default function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen, toggleSearchPanel } = useUIStore();
  const { files, setActiveFile, activeFileId, addFile, fsMode, openFsFolder } = useFileStore();
  const { showTerminal, toggleTerminal } = useChatStore();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (commandPaletteOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [commandPaletteOpen]);

  const fileCommands: CommandItem[] = useMemo(() => {
    if (!query.trim()) return files.map((f) => ({
      id: f.id,
      label: f.name,
      category: 'file' as const,
      action: () => {
        setActiveFile(f.id);
        setCommandPaletteOpen(false);
      },
    }));

    const q = query.toLowerCase();
    return files
      .filter((f) => f.name.toLowerCase().includes(q))
      .map((f) => ({
        id: f.id,
        label: f.name,
        category: 'file' as const,
        action: () => {
          setActiveFile(f.id);
          setCommandPaletteOpen(false);
        },
      }));
  }, [files, query, setActiveFile, setCommandPaletteOpen]);

  const actionCommands: CommandItem[] = useMemo(() => {
    const all: CommandItem[] = [
      {
        id: 'new-file',
        label: '新建文件',
        category: 'file',
        shortcut: 'Ctrl+N',
        action: () => {
          const name = `untitled-${Date.now().toString(36)}.hto`;
          addFile(name);
          setCommandPaletteOpen(false);
        },
      },
      {
        id: 'open-folder',
        label: '打开文件夹',
        category: 'file',
        action: async () => {
          setCommandPaletteOpen(false);
          try { await openFsFolder(''); } catch { /* ignore */ }
        },
      },
      {
        id: 'run-code',
        label: '运行代码',
        category: 'run',
        shortcut: 'F5',
        action: () => {
          setCommandPaletteOpen(false);
          document.querySelector<HTMLButtonElement>('[data-action="run"]')?.click();
        },
      },
      {
        id: 'toggle-terminal',
        label: '切换终端',
        category: 'view',
        shortcut: 'Ctrl+`',
        action: () => {
          toggleTerminal();
          setCommandPaletteOpen(false);
        },
      },
      {
        id: 'toggle-search',
        label: '搜索',
        category: 'edit',
        shortcut: 'Ctrl+F',
        action: () => {
          toggleSearchPanel();
          setCommandPaletteOpen(false);
        },
      },
      {
        id: 'toggle-settings',
        label: '打开设置',
        category: 'view',
        action: () => {
          setCommandPaletteOpen(false);
          document.querySelector<HTMLButtonElement>('[data-action="settings"]')?.click();
        },
      },
    ];

    if (!query.trim()) return all;
    const q = query.toLowerCase();
    return all.filter((c) => c.label.toLowerCase().includes(q));
  }, [query, addFile, setCommandPaletteOpen, openFsFolder, toggleTerminal, toggleSearchPanel]);

  const allItems = useMemo(() => {
    const items: CommandItem[] = [];
    if (fileCommands.length > 0) {
      items.push(...fileCommands);
    }
    if (actionCommands.length > 0) {
      if (items.length > 0) items.push({ id: '__sep__', label: '─ 命令 ─', category: 'file', action: () => {} });
      items.push(...actionCommands);
    }
    return items;
  }, [fileCommands, actionCommands]);

  const selectedItem = allItems[selectedIndex];

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, allItems.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedItem && selectedItem.id !== '__sep__') {
        selectedItem.action();
      }
    } else if (e.key === 'Escape') {
      setCommandPaletteOpen(false);
    }
  }, [allItems, selectedIndex, selectedItem, setCommandPaletteOpen]);

  useEffect(() => {
    if (listRef.current && selectedIndex >= 0) {
      const el = listRef.current.children[selectedIndex] as HTMLElement;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'file': return <File className="w-3.5 h-3.5" />;
      case 'edit': return <Search className="w-3.5 h-3.5" />;
      case 'view': return <PanelRight className="w-3.5 h-3.5" />;
      case 'run': return <Play className="w-3.5 h-3.5" />;
      default: return <Code2 className="w-3.5 h-3.5" />;
    }
  };

  if (!commandPaletteOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm animate-fade-in"
      onClick={() => setCommandPaletteOpen(false)}>
      <div className="w-full max-w-lg bg-zzw-surface border border-zzw-border rounded-2xl shadow-2xl overflow-hidden animate-slide-right"
        onClick={(e) => e.stopPropagation()}>
        {/* 搜索框 */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-zzw-border">
          <Search className="w-4 h-4 text-zzw-text-dim shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={handleKeyDown}
            placeholder="搜索文件或命令..."
            className="flex-1 bg-transparent text-zzw-text text-sm placeholder-zzw-text-dim focus:outline-none"
          />
          <div className="flex items-center gap-1">
            <span className="text-xs text-zzw-text-dim bg-zzw-bg px-1.5 py-0.5 rounded border border-zzw-border">
              ↑↓
            </span>
            <span className="text-xs text-zzw-text-dim bg-zzw-bg px-1.5 py-0.5 rounded border border-zzw-border">
              Enter
            </span>
            <button
              onClick={() => setCommandPaletteOpen(false)}
              className="ml-1 w-6 h-6 rounded flex items-center justify-center text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* 结果列表 */}
        <div ref={listRef} className="max-h-72 overflow-y-auto py-2">
          {allItems.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <Zap className="w-6 h-6 text-zzw-text-dim mx-auto mb-2 opacity-30" />
              <p className="text-xs text-zzw-text-dim">没有找到匹配项</p>
            </div>
          ) : (
            allItems.map((item, index) => {
              if (item.id === '__sep__') {
                return (
                  <div key={item.id} className="px-4 py-1.5 text-[10px] text-zzw-text-dim/50 font-medium uppercase tracking-wider">
                    {item.label}
                  </div>
                );
              }
              return (
                <button
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors ${
                    index === selectedIndex
                      ? 'bg-zzw-cyan/10 text-zzw-cyan'
                      : 'text-zzw-text hover:bg-zzw-surface2'
                  }`}
                >
                  <span className={`shrink-0 ${index === selectedIndex ? 'text-zzw-cyan' : 'text-zzw-text-dim'}`}>
                    {getCategoryIcon(item.category)}
                  </span>
                  <span className="flex-1 text-sm truncate">{item.label}</span>
                  {item.shortcut && (
                    <span className="text-[10px] text-zzw-text-dim bg-zzw-bg px-1.5 py-0.5 rounded border border-zzw-border">
                      {item.shortcut}
                    </span>
                  )}
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}