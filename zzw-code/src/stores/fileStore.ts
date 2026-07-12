import { create } from 'zustand';
import type { ProjectFile, FsEntry } from '@/types';
import * as api from '@/utils/api';

interface FileState {
  files: ProjectFile[];
  activeFileId: string | null;
  openTabs: string[];
  // 本地文件系统模式
  fsMode: boolean;
  fsRootPath: string;
  fsTree: FsEntry[];
  fsLoading: boolean;
  // 操作
  addFile: (name: string, content?: string, fsPath?: string, source?: 'local' | 'fs') => void;
  updateFile: (id: string, content: string) => void;
  markFileClean: (id: string) => void;
  deleteFile: (id: string) => void;
  renameFile: (id: string, newName: string) => void;
  setActiveFile: (id: string) => void;
  closeTab: (id: string) => void;
  loadFromStorage: () => void;
  saveToStorage: () => void;
  // 本地文件系统操作
  openFsFolder: (dirPath?: string) => Promise<void>;
  refreshFsTree: () => Promise<void>;
  openFsFile: (entry: FsEntry) => Promise<void>;
  createFsFile: (parentPath: string, name: string) => Promise<void>;
  createFsDirectory: (parentPath: string, name: string) => Promise<void>;
  deleteFsEntry: (fsPath: string) => Promise<void>;
  renameFsEntry: (oldPath: string, newName: string) => Promise<void>;
  saveCurrentToFs: () => Promise<void>;
  exitFsMode: () => void;
}

function makeId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export const useFileStore = create<FileState>((set, get) => ({
  files: [],
  activeFileId: null,
  openTabs: [],
  fsMode: false,
  fsRootPath: '',
  fsTree: [],
  fsLoading: false,

  addFile: (name, content = '', fsPath, source = 'local') => {
    const file: ProjectFile = {
      id: makeId(),
      name,
      content,
      language: 'hsharp',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      fsPath,
      source,
    };
    set((s) => {
      const files = [...s.files, file];
      if (source === 'local') {
        localStorage.setItem('zzw-files', JSON.stringify(files));
      }
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
        f.id === id ? { ...f, content, updatedAt: Date.now(), dirty: true } : f
      );
      if (!s.fsMode) {
        localStorage.setItem('zzw-files', JSON.stringify(files));
      }
      return { files };
    });
  },

  markFileClean: (id: string) => {
    set((s) => ({
      files: s.files.map((f) =>
        f.id === id ? { ...f, dirty: false } : f
      ),
    }));
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
      if (!s.fsMode) {
        localStorage.setItem('zzw-files', JSON.stringify(files));
      }
      return { files, openTabs, activeFileId };
    });
  },

  renameFile: (id, newName) => {
    set((s) => {
      const files = s.files.map((f) =>
        f.id === id ? { ...f, name: newName, updatedAt: Date.now() } : f
      );
      if (!s.fsMode) {
        localStorage.setItem('zzw-files', JSON.stringify(files));
      }
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
        // 确保所有文件都有 source 字段
        const migrated = files.map(f => ({ ...f, source: f.source || 'local' }));
        set({ files: migrated });
      } catch {
        set({ files: [] });
      }
    }
  },

  saveToStorage: () => {
    localStorage.setItem('zzw-files', JSON.stringify(get().files));
  },

  // ──────────── 本地文件系统操作 ────────────

  openFsFolder: async (dirPath?: string) => {
    set({ fsLoading: true });
    try {
      const result = await api.browseDirectory(dirPath || '');
      set({
        fsMode: true,
        fsRootPath: result.currentPath,
        fsTree: result.entries,
        fsLoading: false,
      });
    } catch (err) {
      set({ fsLoading: false });
      throw err;
    }
  },

  refreshFsTree: async () => {
    const { fsRootPath } = get();
    set({ fsLoading: true });
    try {
      const result = await api.browseDirectory(fsRootPath);
      set({ fsTree: result.entries, fsLoading: false });
    } catch (err) {
      set({ fsLoading: false });
      throw err;
    }
  },

  openFsFile: async (entry: FsEntry) => {
    if (entry.isDirectory) {
      // 进入子目录
      set({ fsLoading: true });
      try {
        const result = await api.browseDirectory(entry.path);
        set({
          fsRootPath: result.currentPath,
          fsTree: result.entries,
          fsLoading: false,
        });
      } catch (err) {
        set({ fsLoading: false });
        throw err;
      }
      return;
    }

    // 检查是否已打开
    const existing = get().files.find((f) => f.fsPath === entry.path);
    if (existing) {
      set({ activeFileId: existing.id });
      return;
    }

    // 从服务器读取文件内容
    try {
      const result = await api.readFile(entry.path);
      const file: ProjectFile = {
        id: makeId(),
        name: result.name,
        content: result.content,
        language: 'hsharp',
        createdAt: result.modified,
        updatedAt: result.modified,
        fsPath: entry.path,
        source: 'fs',
      };
      set((s) => ({
        files: [...s.files, file],
        activeFileId: file.id,
        openTabs: [...s.openTabs, file.id],
      }));
    } catch (err) {
      console.error('Failed to read file:', err);
    }
  },

  createFsFile: async (parentPath: string, name: string) => {
    const filePath = parentPath ? `${parentPath}/${name}` : name;
    await api.createFile(filePath);
    await get().refreshFsTree();
  },

  createFsDirectory: async (parentPath: string, name: string) => {
    const dirPath = parentPath ? `${parentPath}/${name}` : name;
    await api.createDirectory(dirPath);
    await get().refreshFsTree();
  },

  deleteFsEntry: async (fsPath: string) => {
    // 先检查是文件还是目录（通过 fsTree 判断）
    const entry = get().fsTree.find(e => e.path === fsPath);
    if (!entry) return;

    if (entry.isDirectory) {
      await api.deleteDirectory(fsPath);
    } else {
      await api.deleteFile(fsPath);
      // 关闭已打开的标签
      const openFile = get().files.find(f => f.fsPath === fsPath);
      if (openFile) {
        get().deleteFile(openFile.id);
      }
    }
    await get().refreshFsTree();
  },

  renameFsEntry: async (oldPath: string, newName: string) => {
    const parentDir = oldPath.includes('/') ? oldPath.substring(0, oldPath.lastIndexOf('/')) : '';
    const newPath = parentDir ? `${parentDir}/${newName}` : newName;
    await api.renameFile(oldPath, newPath);
    await get().refreshFsTree();
  },

  saveCurrentToFs: async () => {
    const { activeFileId, files } = get();
    const file = files.find(f => f.id === activeFileId);
    if (file && file.source === 'fs' && file.fsPath) {
      await api.saveFile(file.fsPath, file.content);
    }
  },

  exitFsMode: () => {
    set({ fsMode: false, fsTree: [], fsRootPath: '' });
  },
}));