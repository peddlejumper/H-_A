import { useState } from 'react';
import { useConfigStore } from '@/stores/configStore';
import { Zap, Play, Terminal, Settings, X } from 'lucide-react';

interface TopNavbarProps {
  onRun?: () => void;
}

export default function TopNavbar({ onRun }: TopNavbarProps) {
  const { config } = useConfigStore();
  const [showSettings, setShowSettings] = useState(false);

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
          <span className="text-zzw-text-dim text-xs">H# AI IDE</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onRun}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zzw-cyan/10 border border-zzw-cyan/30 rounded-lg text-zzw-cyan text-xs font-medium hover:bg-zzw-cyan/20 hover:border-zzw-cyan/50 transition-all duration-200 active:scale-95"
          >
            <Play className="w-3.5 h-3.5" />
            <span>运行</span>
          </button>

          <button
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zzw-surface2 border border-zzw-border rounded-lg text-zzw-text-dim text-xs font-medium hover:text-zzw-text hover:border-zzw-text-dim/30 transition-all duration-200 active:scale-95"
            title="终端"
          >
            <Terminal className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setShowSettings(true)}
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