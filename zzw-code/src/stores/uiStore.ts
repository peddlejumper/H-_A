import { create } from 'zustand';
import type { ToastItem, ContextMenuState } from '@/types';

interface StatusBarInfo {
  line: number;
  col: number;
  language: string;
  totalLines: number;
  encoding: string;
}

interface UIState {
  // 状态栏
  statusBar: StatusBarInfo;
  setStatusBar: (info: Partial<StatusBarInfo>) => void;
  // Toast 通知
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, 'id'>) => void;
  removeToast: (id: string) => void;
  // 命令面板
  commandPaletteOpen: boolean;
  toggleCommandPalette: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  // 搜索面板
  searchPanelOpen: boolean;
  toggleSearchPanel: () => void;
  setSearchPanelOpen: (open: boolean) => void;
  // 右键菜单
  contextMenu: ContextMenuState | null;
  setContextMenu: (menu: ContextMenuState | null) => void;
  // 大纲面板
  outlineOpen: boolean;
  toggleOutline: () => void;
  setOutlineOpen: (open: boolean) => void;
}

let toastId = 0;

export const useUIStore = create<UIState>((set, get) => ({
  statusBar: {
    line: 1,
    col: 1,
    language: 'H#',
    totalLines: 0,
    encoding: 'UTF-8',
  },

  setStatusBar: (info) => {
    set((s) => ({ statusBar: { ...s.statusBar, ...info } }));
  },

  toasts: [],

  addToast: (toast) => {
    const id = `toast-${++toastId}`;
    const item: ToastItem = { ...toast, id };
    set((s) => ({ toasts: [...s.toasts, item] }));
    const duration = toast.duration ?? 3000;
    if (duration > 0) {
      setTimeout(() => {
        get().removeToast(id);
      }, duration);
    }
  },

  removeToast: (id) => {
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
  },

  commandPaletteOpen: false,
  toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

  searchPanelOpen: false,
  toggleSearchPanel: () => set((s) => ({ searchPanelOpen: !s.searchPanelOpen })),
  setSearchPanelOpen: (open) => set({ searchPanelOpen: open }),

  contextMenu: null,
  setContextMenu: (menu) => set({ contextMenu: menu }),

  outlineOpen: false,
  toggleOutline: () => set((s) => ({ outlineOpen: !s.outlineOpen })),
  setOutlineOpen: (open) => set({ outlineOpen: open }),
}));