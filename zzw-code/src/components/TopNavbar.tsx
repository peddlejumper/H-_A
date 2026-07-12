import { useState } from 'react';
import { useConfigStore } from '@/stores/configStore';
import { useFileStore } from '@/stores/fileStore';
import { useChatStore } from '@/stores/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { runCode, healthCheck } from '@/utils/api';
import { Zap, Play, FolderOpen, Folder, Terminal, Settings, X, Loader2, CheckCircle, AlertCircle, ListTree } from 'lucide-react';

export default function TopNavbar() {
  const { config } = useConfigStore();
  const { files, activeFileId, fsMode, openFsFolder, exitFsMode, saveCurrentToFs } = useFileStore();
  const { addTerminalEntry, toggleTerminal, showTerminal } = useChatStore();
  const { toggleOutline } = useUIStore();
  const [showSettings, setShowSettings] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [serverStatus, setServerStatus] = useState<'unknown' | 'online' | 'offline'>('unknown');

  // 检查服务器状态
  const checkServer = async () => {
    try {
      await healthCheck();
      setServerStatus('online');
    } catch {
      setServerStatus('offline');
    }
  };

  // 运行代码
  const handleRun = async () => {
    const activeFile = files.find(f => f.id === activeFileId);
    if (!activeFile) {
      addTerminalEntry('error', '没有打开的文件。请先选择一个文件。');
      if (!showTerminal) toggleTerminal();
      return;
    }

    // 如果是 FS 模式，先保存当前文件
    if (fsMode && activeFile.source === 'fs') {
      await saveCurrentToFs();
    }

    setIsRunning(true);
    if (!showTerminal) toggleTerminal();

    addTerminalEntry('info', `运行: ${activeFile.name}`);
    addTerminalEntry('info', '──────────────────────────────');

    try {
      const result = await runCode(activeFile.content);
      if (result.output) {
        // 分行输出
        const lines = result.output.split('\n');
        for (const line of lines) {
          if (line.trim()) {
            addTerminalEntry('output', line);
          }
        }
      }
      if (result.success) {
        addTerminalEntry('success', `✓ 运行成功 (退出码: ${result.exitCode})`);
      } else {
        addTerminalEntry('error', `✗ 运行失败 (退出码: ${result.exitCode})`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '未知错误';
      addTerminalEntry('error', `✗ 运行错误: ${msg}`);
      addTerminalEntry('error', '  请确保 ZZW Code 后端服务器已启动 (cd zzw-code/server && npm start)');
    } finally {
      setIsRunning(false);
    }
  };

  // 打开文件夹
  const handleOpenFolder = async () => {
    try {
      await openFsFolder('');
      addTerminalEntry('info', '已打开项目文件夹');
    } catch (err) {
      const msg = err instanceof Error ? err.message : '未知错误';
      addTerminalEntry('error', `打开文件夹失败: ${msg}`);
      addTerminalEntry('error', '  请确保 ZZW Code 后端服务器已启动');
      if (!showTerminal) toggleTerminal();
    }
  };

  return (
    <>
      <div className="h-12 bg-zzw-surface border-b border-zzw-border flex items-center justify-between px-4 shrink-0 select-none">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-zzw-cyan to-zzw-purple flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white text-sm tracking-wide">ZZW Code</span>
          </div>
          <div className="w-px h-5 bg-zzw-border" />
          <span className="text-zzw-text-dim text-xs">
            {fsMode ? '本地项目' : 'H# AI IDE'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* 打开文件夹按钮 */}
          {!fsMode ? (
            <button
              onClick={handleOpenFolder}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zzw-surface2 border border-zzw-border rounded-lg text-zzw-text-dim text-xs font-medium hover:text-zzw-text hover:border-zzw-text-dim/30 transition-all duration-200 active:scale-95"
              title="打开本地文件夹"
            >
              <FolderOpen className="w-3.5 h-3.5" />
              <span>打开文件夹</span>
            </button>
          ) : (
            <button
              onClick={exitFsMode}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zzw-cyan/10 border border-zzw-cyan/20 rounded-lg text-zzw-cyan text-xs font-medium hover:bg-zzw-cyan/20 transition-all duration-200 active:scale-95"
              title="退出文件夹模式"
            >
              <Folder className="w-3.5 h-3.5" />
              <span>文件夹模式</span>
            </button>
          )}

          {/* 运行按钮 */}
          <button
            onClick={handleRun}
            data-action="run"
            disabled={isRunning || !activeFileId}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 active:scale-95 ${
              isRunning
                ? 'bg-zzw-cyan/20 border border-zzw-cyan/40 text-zzw-cyan cursor-wait'
                : !activeFileId
                  ? 'bg-zzw-surface2 border border-zzw-border text-zzw-text-dim/50 cursor-not-allowed'
                  : 'bg-zzw-cyan/10 border border-zzw-cyan/30 text-zzw-cyan hover:bg-zzw-cyan/20 hover:border-zzw-cyan/50'
            }`}
          >
            {isRunning ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}
            <span>{isRunning ? '运行中' : '运行'}</span>
          </button>

          {/* 服务器状态 */}
          <button
            onClick={checkServer}
            className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs transition-all duration-200"
            title={`服务器状态: ${serverStatus}`}
          >
            {serverStatus === 'online' ? (
              <CheckCircle className="w-3.5 h-3.5 text-zzw-green" />
            ) : serverStatus === 'offline' ? (
              <AlertCircle className="w-3.5 h-3.5 text-zzw-red" />
            ) : (
              <div className="w-3.5 h-3.5 rounded-full border border-zzw-text-dim" />
            )}
          </button>

          {/* 终端按钮 */}
          <button
            onClick={toggleTerminal}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 active:scale-95 ${
              showTerminal
                ? 'bg-zzw-cyan/10 border border-zzw-cyan/20 text-zzw-cyan'
                : 'bg-zzw-surface2 border border-zzw-border text-zzw-text-dim hover:text-zzw-text hover:border-zzw-text-dim/30'
            }`}
            title="终端"
          >
            <Terminal className="w-3.5 h-3.5" />
          </button>

          {/* 设置按钮 */}
          <button
            onClick={() => setShowSettings(true)}
            data-action="settings"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zzw-surface2 border border-zzw-border rounded-lg text-zzw-text-dim text-xs font-medium hover:text-zzw-text hover:border-zzw-text-dim/30 transition-all duration-200 active:scale-95"
            title="设置"
          >
            <Settings className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {showSettings && <SettingsDialog onClose={() => setShowSettings(false)} />}
    </>
  );
}

function SettingsDialog({ onClose }: { onClose: () => void }) {
  const { config, setConfig, clearConfig } = useConfigStore();
  const [endpoint, setEndpoint] = useState(config?.endpoint || '');
  const [apiKey, setApiKey] = useState(config?.apiKey || '');
  const [model, setModel] = useState(config?.model || '');

  const handleSave = () => {
    if (endpoint.trim() && apiKey.trim() && model.trim()) {
      setConfig({ endpoint: endpoint.trim(), apiKey: apiKey.trim(), model: model.trim() });
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md bg-zzw-surface border border-zzw-border rounded-2xl shadow-2xl p-6 animate-slide-right">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">API 设置</h2>
          <button onClick={onClose} className="text-zzw-text-dim hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zzw-text mb-1.5">Endpoint</label>
            <input type="text" value={endpoint} onChange={(e) => setEndpoint(e.target.value)}
              className="w-full px-3 py-2 bg-zzw-bg border border-zzw-border rounded-lg text-zzw-text text-sm focus:outline-none focus:border-zzw-cyan/50 transition-all" />
          </div>
          <div>
            <label className="block text-xs font-medium text-zzw-text mb-1.5">API Key</label>
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
              className="w-full px-3 py-2 bg-zzw-bg border border-zzw-border rounded-lg text-zzw-text text-sm focus:outline-none focus:border-zzw-cyan/50 transition-all" />
          </div>
          <div>
            <label className="block text-xs font-medium text-zzw-text mb-1.5">Model</label>
            <input type="text" value={model} onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 bg-zzw-bg border border-zzw-border rounded-lg text-zzw-text text-sm focus:outline-none focus:border-zzw-cyan/50 transition-all" />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={clearConfig}
            className="px-4 py-2 text-xs text-zzw-red hover:bg-zzw-red/10 rounded-lg transition-colors">
            清除配置
          </button>
          <div className="flex-1" />
          <button onClick={onClose}
            className="px-4 py-2 text-xs text-zzw-text-dim bg-zzw-surface2 border border-zzw-border rounded-lg hover:text-zzw-text transition-colors">
            取消
          </button>
          <button onClick={handleSave}
            className="px-4 py-2 text-xs font-medium text-white bg-gradient-to-r from-zzw-cyan to-zzw-purple rounded-lg hover:opacity-90 transition-opacity">
            保存
          </button>
        </div>
      </div>
    </div>
  );
}