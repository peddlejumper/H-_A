import { useState, useRef, useEffect } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { useFileStore } from '@/stores/fileStore';
import { useConfigStore } from '@/stores/configStore';
import { Bot, Send, User, Sparkles, Trash2, Loader2, Code, PanelRightClose, PanelRightOpen } from 'lucide-react';

export default function AiPanel() {
  const { messages, isLoading, sendMessage, clearChat } = useChatStore();
  const { files, activeFileId } = useFileStore();
  const { isConfigured, config } = useConfigStore();
  const [input, setInput] = useState('');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const activeFile = files.find((f) => f.id === activeFileId);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!isLoading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isLoading]);

  const handleSend = async () => {
    const content = input.trim();
    if (!content || isLoading || !isConfigured) return;
    setInput('');
    await sendMessage(content, activeFile?.content || '');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isCollapsed) {
    return (
      <div className="w-10 bg-zzw-surface border-l border-zzw-border flex flex-col items-center py-3 shrink-0">
        <button
          onClick={() => setIsCollapsed(false)}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-zzw-text-dim hover:text-zzw-cyan hover:bg-zzw-surface2 transition-all"
          title="展开 AI 面板"
        >
          <PanelRightOpen className="w-4 h-4" />
        </button>
        <div className="mt-2 w-2 h-2 rounded-full bg-zzw-cyan animate-pulse" />
      </div>
    );
  }

  return (
    <div className="w-96 bg-zzw-surface border-l border-zzw-border flex flex-col shrink-0">
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-zzw-border">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-zzw-cyan to-zzw-purple flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold text-white">ZZW AI</span>
          {!isConfigured && (
            <span className="text-xs text-zzw-yellow bg-zzw-yellow/10 px-1.5 py-0.5 rounded">未配置</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="w-6 h-6 rounded-md flex items-center justify-center text-zzw-text-dim hover:text-zzw-red hover:bg-zzw-surface2 transition-all"
              title="清空对话"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={() => setIsCollapsed(true)}
            className="w-6 h-6 rounded-md flex items-center justify-center text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2 transition-all"
            title="收起面板"
          >
            <PanelRightClose className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {activeFile && (
        <div className="px-3 py-1.5 bg-zzw-cyan/5 border-b border-zzw-border flex items-center gap-1.5 text-xs text-zzw-text-dim">
          <Code className="w-3 h-3" />
          <span className="truncate">上下文: {activeFile.name}</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <Bot className="w-10 h-10 text-zzw-text-dim mb-3 opacity-20" />
            <p className="text-sm text-zzw-text-dim mb-1">H# AI 编程助手</p>
            <p className="text-xs text-zzw-text-dim/60">
              我可以帮你编写 H# 代码、解释语法、调试问题
            </p>
            <div className="mt-4 space-y-1.5 w-full">
              {[
                '如何定义一个函数？',
                '帮我写一个斐波那契数列',
                '如何使用 DZZW 并行计算？',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => { setInput(q); inputRef.current?.focus(); }}
                  className="w-full text-left px-3 py-2 text-xs text-zzw-text-dim bg-zzw-surface2 border border-zzw-border rounded-lg hover:border-zzw-cyan/30 hover:text-zzw-text transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-2.5 animate-fade-in ${
              msg.role === 'user' ? 'flex-row-reverse' : ''
            }`}
          >
            <div
              className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                msg.role === 'user'
                  ? 'bg-zzw-purple/20'
                  : 'bg-zzw-cyan/20'
              }`}
            >
              {msg.role === 'user' ? (
                <User className="w-3.5 h-3.5 text-zzw-purple" />
              ) : (
                <Bot className="w-3.5 h-3.5 text-zzw-cyan" />
              )}
            </div>
            <div
              className={`flex-1 min-w-0 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'text-right'
                  : 'text-zzw-text'
              }`}
            >
              {msg.role === 'user' ? (
                <div className="inline-block px-3 py-2 bg-zzw-purple/10 border border-zzw-purple/20 rounded-2xl rounded-tr-md text-zzw-text text-left whitespace-pre-wrap">
                  {msg.content}
                </div>
              ) : msg.content ? (
                <div className="text-zzw-text whitespace-pre-wrap markdown-body">
                  <MarkdownRenderer content={msg.content} />
                </div>
              ) : (
                <div className="flex items-center gap-2 text-zzw-text-dim">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span className="text-xs">思考中...</span>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && messages[messages.length - 1]?.content && (
          <div className="flex items-center gap-2 px-9 text-zzw-text-dim">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span className="text-xs">继续生成...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="px-3 py-3 border-t border-zzw-border">
        <div className="flex items-end gap-2 bg-zzw-bg border border-zzw-border rounded-xl focus-within:border-zzw-cyan/50 transition-all">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isConfigured ? '向 AI 提问... (Enter 发送)' : '请先在设置中配置 API Key'}
            disabled={isLoading || !isConfigured}
            rows={1}
            className="flex-1 px-3 py-2.5 bg-transparent text-zzw-text text-sm placeholder-zzw-text-dim resize-none focus:outline-none disabled:opacity-50"
            style={{ maxHeight: '120px' }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = Math.min(target.scrollHeight, 120) + 'px';
            }}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim() || !isConfigured}
            className="m-1.5 w-8 h-8 rounded-lg bg-gradient-to-r from-zzw-cyan to-zzw-purple flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90 transition-all active:scale-95"
          >
            <Send className="w-3.5 h-3.5 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  const renderContent = () => {
    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, i) => {
      if (part.startsWith('```')) {
        const lines = part.split('\n');
        const lang = lines[0].replace('```', '').trim();
        const code = lines.slice(1, -1).join('\n');
        return (
          <div key={i} className="my-2 rounded-lg overflow-hidden border border-zzw-border">
            {lang && (
              <div className="px-3 py-1 bg-zzw-surface2 text-xs text-zzw-text-dim font-mono">
                {lang}
              </div>
            )}
            <pre className="px-3 py-2 bg-zzw-bg text-xs font-mono text-zzw-text overflow-x-auto">
              <code>{code}</code>
            </pre>
          </div>
        );
      }
      return (
        <span key={i} className="whitespace-pre-wrap">
          {part
            .replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 bg-zzw-surface2 text-zzw-cyan text-xs rounded font-mono">$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-white">$1</strong>')
            .split('\n')
            .map((line, j) => (
              <span key={j}>
                {j > 0 && <br />}
                <span dangerouslySetInnerHTML={{ __html: line }} />
              </span>
            ))}
        </span>
      );
    });
  };

  return <>{renderContent()}</>;
}