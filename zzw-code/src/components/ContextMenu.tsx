import { useEffect, useRef } from 'react';
import { useUIStore } from '@/stores/uiStore';

export default function ContextMenu() {
  const { contextMenu, setContextMenu } = useUIStore();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!contextMenu) return;

    const handleClick = () => setContextMenu(null);
    const handleScroll = () => setContextMenu(null);
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setContextMenu(null);
    };

    document.addEventListener('click', handleClick);
    document.addEventListener('scroll', handleScroll, true);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('click', handleClick);
      document.removeEventListener('scroll', handleScroll, true);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [contextMenu, setContextMenu]);

  if (!contextMenu) return null;

  return (
    <div
      ref={menuRef}
      className="fixed z-50 min-w-[160px] bg-zzw-surface border border-zzw-border rounded-lg shadow-2xl py-1 animate-fade-in overflow-hidden"
      style={{ left: contextMenu.x, top: contextMenu.y }}
    >
      {contextMenu.items.map((item, index) => {
        if (item.separator) {
          return <div key={`sep-${index}`} className="my-1 border-t border-zzw-border" />;
        }
        return (
          <button
            key={`${item.label}-${index}`}
            onClick={() => {
              item.action();
              setContextMenu(null);
            }}
            disabled={item.disabled}
            className={`w-full flex items-center justify-between px-3 py-1.5 text-xs text-left transition-colors ${
              item.disabled
                ? 'text-zzw-text-dim/50 cursor-not-allowed'
                : item.danger
                  ? 'text-zzw-red hover:bg-zzw-red/10'
                  : 'text-zzw-text hover:bg-zzw-surface2'
            }`}
          >
            <span>{item.label}</span>
            {item.shortcut && (
              <span className="text-[10px] text-zzw-text-dim ml-4">{item.shortcut}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}