export interface ProjectFile {
  id: string;
  name: string;
  content: string;
  language: 'hsharp';
  createdAt: number;
  updatedAt: number;
  /** 本地文件路径（如果从文件系统加载） */
  fsPath?: string;
  /** 来源：local = localStorage, fs = 本地文件系统 */
  source: 'local' | 'fs';
  /** 是否有未保存的修改 */
  dirty?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface ApiConfig {
  endpoint: string;
  apiKey: string;
  model: string;
}

export interface TerminalEntry {
  id: string;
  type: 'info' | 'output' | 'error' | 'success';
  text: string;
  timestamp: number;
}

export interface FsEntry {
  name: string;
  isDirectory: boolean;
  path: string;
  extension: string;
}

export interface ToastItem {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
  duration?: number;
}

export interface ContextMenuItem {
  label: string;
  shortcut?: string;
  action: () => void;
  separator?: boolean;
  disabled?: boolean;
  danger?: boolean;
}

export interface ContextMenuState {
  x: number;
  y: number;
  items: ContextMenuItem[];
}

export interface CommandItem {
  id: string;
  label: string;
  category: 'file' | 'edit' | 'view' | 'run';
  shortcut?: string;
  action: () => void;
}