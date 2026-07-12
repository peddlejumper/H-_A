import { useState } from 'react';
import { useFileStore } from '@/stores/fileStore';
import {
  File, FilePlus, FolderOpen, Trash2, ChevronRight, ChevronDown, Edit2,
} from 'lucide-react';

export default function FileExplorer() {
  const { files, activeFileId, setActiveFile, addFile, deleteFile, renameFile } = useFileStore();
  const [showNewFileInput, setShowNewFileInput] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [editingFileId, setEditingFileId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleCreateFile = () => {
    const name = newFileName.trim();
    if (!name) return;
    const finalName = name.endsWith('.hto') ? name : name + '.hto';
    addFile(finalName);
    setNewFileName('');
    setShowNewFileInput(false);
  };

  const startRename = (id: string, name: string) => {
    setEditingFileId(id);
    setEditName(name);
  };

  const handleRename = (id: string) => {
    if (editName.trim()) {
      renameFile(id, editName.trim());
    }
    setEditingFileId(null);
    setEditName('');
  };

  if (isCollapsed) {
    return (
      <div className="w-10 bg-zzw-surface border-r border-zzw-border flex flex-col items-center py-3 shrink-0">
        <button
          onClick={() => setIsCollapsed(false)}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-zzw-text-dim hover:text-zzw-cyan hover:bg-zzw-surface2 transition-all"
          title="展开文件树"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        {files.map((f) => (
          <button
            key={f.id}
            onClick={() => setActiveFile(f.id)}
            className={`w-7 h-7 rounded-lg flex items-center justify-center mt-1 text-xs font-mono transition-all ${
              f.id === activeFileId
                ? 'text-zzw-cyan bg-zzw-cyan/10'
                : 'text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2'
            }`}
            title={f.name}
          >
            {f.name.charAt(0).toUpperCase()}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="w-64 bg-zzw-surface border-r border-zzw-border flex flex-col shrink-0">
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-zzw-border">
        <button
          onClick={() => setIsCollapsed(true)}
          className="flex items-center gap-2 text-xs text-zzw-text-dim hover:text-zzw-text transition-colors"
        >
          <ChevronDown className="w-3.5 h-3.5" />
          <span>文件浏览器</span>
        </button>
        <button
          onClick={() => setShowNewFileInput(true)}
          className="w-6 h-6 rounded-md flex items-center justify-center text-zzw-text-dim hover:text-zzw-cyan hover:bg-zzw-surface2 transition-all"
          title="新建文件"
        >
          <FilePlus className="w-3.5 h-3.5" />
        </button>
      </div>

      {showNewFileInput && (
        <div className="px-3 py-2 border-b border-zzw-border animate-fade-in">
          <input
            type="text"
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateFile();
              if (e.key === 'Escape') { setShowNewFileInput(false); setNewFileName(''); }
            }}
            onBlur={() => { if (newFileName.trim()) handleCreateFile(); else setShowNewFileInput(false); }}
            placeholder="文件名.hto"
            autoFocus
            className="w-full px-2 py-1.5 bg-zzw-bg border border-zzw-cyan/30 rounded-md text-zzw-text text-xs placeholder-zzw-text-dim focus:outline-none focus:border-zzw-cyan transition-all"
          />
        </div>
      )}

      <div className="flex-1 overflow-y-auto py-1">
        {files.map((file) => (
          <div
            key={file.id}
            onClick={() => setActiveFile(file.id)}
            className={`group flex items-center gap-2 px-3 py-2 cursor-pointer transition-all duration-150 border-l-2 ${
              file.id === activeFileId
                ? 'border-zzw-cyan bg-zzw-cyan/5 text-zzw-text'
                : 'border-transparent text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2'
            }`}
          >
            <File className="w-3.5 h-3.5 shrink-0" />

            {editingFileId === file.id ? (
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRename(file.id);
                  if (e.key === 'Escape') setEditingFileId(null);
                }}
                onBlur={() => handleRename(file.id)}
                autoFocus
                onClick={(e) => e.stopPropagation()}
                className="flex-1 min-w-0 bg-zzw-bg border border-zzw-cyan/30 rounded px-1.5 py-0.5 text-xs text-zzw-text focus:outline-none"
              />
            ) : (
              <span className="flex-1 text-xs truncate font-mono">{file.name}</span>
            )}

            <div className="hidden group-hover:flex items-center gap-0.5">
              <button
                onClick={(e) => { e.stopPropagation(); startRename(file.id, file.name); }}
                className="w-5 h-5 rounded flex items-center justify-center text-zzw-text-dim hover:text-zzw-cyan transition-colors"
                title="重命名"
              >
                <Edit2 className="w-3 h-3" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); deleteFile(file.id); }}
                className="w-5 h-5 rounded flex items-center justify-center text-zzw-text-dim hover:text-zzw-red transition-colors"
                title="删除"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          </div>
        ))}

        {files.length === 0 && (
          <div className="px-3 py-8 text-center">
            <FolderOpen className="w-6 h-6 text-zzw-text-dim mx-auto mb-2 opacity-30" />
            <p className="text-xs text-zzw-text-dim">暂无文件</p>
            <button
              onClick={() => setShowNewFileInput(true)}
              className="mt-3 text-xs text-zzw-cyan hover:text-zzw-cyan-dim transition-colors"
            >
              + 新建文件
            </button>
          </div>
        )}
      </div>
    </div>
  );
}