import { create } from 'zustand';
import type { ProjectFile } from '@/types';

interface FileState {
  files: ProjectFile[];
  activeFileId: string | null;
  openTabs: string[];
  addFile: (name: string, content?: string) => void;
  updateFile: (id: string, content: string) => void;
  deleteFile: (id: string) => void;
  renameFile: (id: string, newName: string) => void;
  setActiveFile: (id: string) => void;
  closeTab: (id: string) => void;
  loadFromStorage: () => void;
  saveToStorage: () => void;
}

function makeId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export const useFileStore = create<FileState>((set, get) => ({
  files: [],
  activeFileId: null,
  openTabs: [],

  addFile: (name, content = '') => {
    const file: ProjectFile = {
      id: makeId(),
      name,
      content,
      language: 'hsharp',
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    set((s) => {
      const files = [...s.files, file];
      localStorage.setItem('zzw-files', JSON.stringify(files));
      return {
        files,
        activeFileId: file.id,
        openTabs: [...s.openTabs, file.id],
      };
    });
  },

  updateFile: (id, content) => {
    set((s) => {
      const files = s.files.map((f) =>
        f.id === id ? { ...f, content, updatedAt: Date.now() } : f
      );
      localStorage.setItem('zzw-files', JSON.stringify(files));
      return { files };
    });
  },

  deleteFile: (id) => {
    set((s) => {
      const files = s.files.filter((f) => f.id !== id);
      const openTabs = s.openTabs.filter((t) => t !== id);
      const activeFileId =
        s.activeFileId === id
          ? openTabs.length > 0
            ? openTabs[openTabs.length - 1]
            : null
          : s.activeFileId;
      localStorage.setItem('zzw-files', JSON.stringify(files));
      return { files, openTabs, activeFileId };
    });
  },

  renameFile: (id, newName) => {
    set((s) => {
      const files = s.files.map((f) =>
        f.id === id ? { ...f, name: newName, updatedAt: Date.now() } : f
      );
      localStorage.setItem('zzw-files', JSON.stringify(files));
      return { files };
    });
  },

  setActiveFile: (id) => {
    set((s) => {
      const openTabs = s.openTabs.includes(id) ? s.openTabs : [...s.openTabs, id];
      return { activeFileId: id, openTabs };
    });
  },

  closeTab: (id) => {
    set((s) => {
      const openTabs = s.openTabs.filter((t) => t !== id);
      const activeFileId =
        s.activeFileId === id
          ? openTabs.length > 0
            ? openTabs[openTabs.length - 1]
            : null
          : s.activeFileId;
      return { openTabs, activeFileId };
    });
  },

  loadFromStorage: () => {
    const stored = localStorage.getItem('zzw-files');
    if (stored) {
      try {
        const files = JSON.parse(stored) as ProjectFile[];
        set({ files });
      } catch {
        set({ files: [] });
      }
    }
  },

  saveToStorage: () => {
    localStorage.setItem('zzw-files', JSON.stringify(get().files));
  },
}));