import { useState } from 'react';
import { useConfigStore } from '@/stores/configStore';
import { Key, Shield, Zap } from 'lucide-react';

export default function ApiKeySetup() {
  const { setConfig } = useConfigStore();
  const [endpoint, setEndpoint] = useState('https://api.openai.com/v1/chat/completions');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('gpt-4o');
  const [showKey, setShowKey] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!endpoint.trim() || !apiKey.trim() || !model.trim()) return;
    setConfig({
      endpoint: endpoint.trim(),
      apiKey: apiKey.trim(),
      model: model.trim(),
    });
  };

  return (
    <div className="h-full flex items-center justify-center bg-zzw-bg p-8">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-zzw-cyan to-zzw-purple mb-6">
            <Zap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">ZZW Code</h1>
          <p className="text-zzw-text-dim text-sm">
            H# AI IDE — 配置 API 密钥以开始使用
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-zzw-text mb-2">
              API Endpoint
            </label>
            <input
              type="text"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder="https://api.openai.com/v1/chat/completions"
              className="w-full px-4 py-3 bg-zzw-surface border border-zzw-border rounded-xl text-zzw-text text-sm placeholder-zzw-text-dim focus:outline-none focus:border-zzw-cyan focus:ring-1 focus:ring-zzw-cyan/30 transition-all"
            />
            <p className="mt-1.5 text-xs text-zzw-text-dim">
              支持 OpenAI 兼容 API（如 DeepSeek、Qwen 等）
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-zzw-text mb-2">
              API Key
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full px-4 py-3 pr-10 bg-zzw-surface border border-zzw-border rounded-xl text-zzw-text text-sm placeholder-zzw-text-dim focus:outline-none focus:border-zzw-cyan focus:ring-1 focus:ring-zzw-cyan/30 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zzw-text-dim hover:text-zzw-text transition-colors"
              >
                <Key className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-zzw-text mb-2">
              Model
            </label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="gpt-4o"
              className="w-full px-4 py-3 bg-zzw-surface border border-zzw-border rounded-xl text-zzw-text text-sm placeholder-zzw-text-dim focus:outline-none focus:border-zzw-cyan focus:ring-1 focus:ring-zzw-cyan/30 transition-all"
            />
          </div>

          <button
            type="submit"
            className="w-full py-3 px-4 bg-gradient-to-r from-zzw-cyan to-zzw-purple text-white font-semibold rounded-xl hover:opacity-90 transition-all duration-200 active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-zzw-cyan/50"
          >
            开始使用 ZZW Code
          </button>
        </form>

        <div className="mt-8 flex items-center gap-3 text-xs text-zzw-text-dim justify-center">
          <Shield className="w-3.5 h-3.5" />
          <span>API Key 仅存储在本地浏览器中，不会上传到任何服务器</span>
        </div>
      </div>
    </div>
  );
}