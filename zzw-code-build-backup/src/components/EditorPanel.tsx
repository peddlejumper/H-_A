import { useRef, useCallback, useState } from 'react';
import { useFileStore } from '@/stores/fileStore';
import { X, Code2, ChevronRight } from 'lucide-react';

export default function EditorPanel() {
  const { files, activeFileId, openTabs, setActiveFile, closeTab, updateFile } = useFileStore();
  const activeFile = files.find((f) => f.id === activeFileId);
  const editorRef = useRef<HTMLDivElement>(null);
  const [editorLoaded, setEditorLoaded] = useState(false);

  const handleEditorDidMount = useCallback(
    async (editor: import('monaco-editor').editor.IStandaloneCodeEditor, monaco: typeof import('monaco-editor')) => {
      if (!monaco.languages.getLanguages().some((l) => l.id === 'hsharp')) {
        monaco.languages.register({ id: 'hsharp', extensions: ['.hto', '.hbc'], aliases: ['H#', 'HSharp', 'hsharp'] });
        monaco.languages.setMonarchTokensProvider('hsharp', {
          keywords: [
            'fn', 'let', 'if', 'else', 'for', 'while', 'return', 'break',
            'continue', 'import', 'class', 'new', 'this', 'super', 'nullptr',
            'true', 'false', 'in', 'dzzw_spawn', 'dzzw_await', 'dzzw_parallel_map',
            'dzzw_worker_count', 'dzzw_pending_count',
            'dzzw_channel_create', 'dzzw_channel_send', 'dzzw_channel_recv', 'dzzw_channel_free',
            'dzzw_mutex_create', 'dzzw_mutex_lock', 'dzzw_mutex_unlock', 'dzzw_mutex_free',
          ],
          typeKeywords: ['int', 'float', 'bool', 'str', 'list', 'dict', 'function', 'class', 'instance', 'nil'],
          operators: [
            '=', '>', '<', '!', '~', '?', ':',
            '==', '!=', '<=', '>=', '&&', '||', '++', '--',
            '+', '-', '*', '/', '%', '+=', '-=', '*=', '/=',
          ],
          symbols: /[=><!~?:&|+\-*\/\^%]+/,
          tokenizer: {
            root: [
              [/\/\*/, 'comment', '@comment'],
              [/\/\/.*$/, 'comment'],
              [/"([^"\\]|\\.)*$/, 'string.invalid'],
              [/"/, { token: 'string.quote', bracket: '@open', next: '@string' }],
              [/'[^']*'/, 'string'],
              [/[{}()\[\]]/, '@brackets'],
              [/[a-zA-Z_]\w*/, {
                cases: {
                  '@keywords': 'keyword',
                  '@typeKeywords': 'type',
                  '@default': 'identifier',
                }
              }],
              [/[+-]?\d+\.\d+([eE][+-]?\d+)?/, 'number.float'],
              [/[+-]?\d+/, 'number'],
              [/[;,.]/, 'delimiter'],
            ],
            comment: [
              [/[^\/*]+/, 'comment'],
              [/\*\//, 'comment', '@pop'],
              [/[\/*]/, 'comment'],
            ],
            string: [
              [/[^\\"]+/, 'string'],
              [/\\./, 'string.escape'],
              [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }],
            ],
          },
        });

        monaco.editor.defineTheme('zzw-dark', {
          base: 'vs-dark',
          inherit: true,
          rules: [
            { token: 'comment', foreground: '546E7A', fontStyle: 'italic' },
            { token: 'keyword', foreground: '7C3AED', fontStyle: 'bold' },
            { token: 'type', foreground: '00E5FF' },
            { token: 'string', foreground: '10B981' },
            { token: 'string.escape', foreground: 'F59E0B' },
            { token: 'number', foreground: 'F59E0B' },
            { token: 'number.float', foreground: 'F59E0B' },
            { token: 'identifier', foreground: 'E2E8F0' },
            { token: 'delimiter', foreground: '8899AA' },
          ],
          colors: {
            'editor.background': '#0A0E17',
            'editor.foreground': '#E2E8F0',
            'editor.lineHighlightBackground': '#111827',
            'editor.selectionBackground': '#1A2235',
            'editor.inactiveSelectionBackground': '#1A2235',
            'editorCursor.foreground': '#00E5FF',
            'editorLineNumber.foreground': '#334155',
            'editorLineNumber.activeForeground': '#8899AA',
          },
        });
      }

      editor.updateOptions({
        theme: 'zzw-dark',
        fontSize: 14,
        fontFamily: '"JetBrains Mono", monospace',
        lineNumbers: 'on',
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: 'off',
        tabSize: 4,
        insertSpaces: true,
        automaticLayout: true,
        padding: { top: 16 },
        smoothScrolling: true,
        cursorBlinking: 'smooth',
        cursorSmoothCaretAnimation: 'on',
        bracketPairColorization: { enabled: true },
        guides: { indentation: true },
        renderLineHighlight: 'all',
        overviewRulerBorder: false,
        hideCursorInOverviewRuler: true,
        scrollbar: {
          verticalScrollbarSize: 6,
          horizontalScrollbarSize: 6,
        },
      });

      editor.onDidChangeModelContent(() => {
        const content = editor.getValue();
        const activeFileId = useFileStore.getState().activeFileId;
        if (activeFileId) {
          useFileStore.getState().updateFile(activeFileId, content);
        }
      });

      setEditorLoaded(true);
    },
    []
  );

  if (!activeFileId || !activeFile) {
    return (
      <div className="flex-1 flex items-center justify-center bg-zzw-bg">
        <div className="text-center animate-fade-in">
          <Code2 className="w-12 h-12 text-zzw-text-dim mx-auto mb-4 opacity-20" />
          <p className="text-zzw-text-dim text-sm">选择文件开始编辑</p>
          <p className="text-zzw-text-dim/50 text-xs mt-1">Ctrl+N 新建文件</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-zzw-bg">
      <div className="flex items-center bg-zzw-surface border-b border-zzw-border shrink-0 overflow-x-auto">
        {openTabs.map((tabId) => {
          const file = files.find((f) => f.id === tabId);
          if (!file) return null;
          const isActive = tabId === activeFileId;
          return (
            <div
              key={tabId}
              onClick={() => setActiveFile(tabId)}
              className={`group flex items-center gap-1.5 px-3 py-2 text-xs cursor-pointer border-r border-zzw-border transition-all duration-150 shrink-0 ${
                isActive
                  ? 'bg-zzw-bg text-zzw-cyan border-t-2 border-t-zzw-cyan'
                  : 'text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2'
              }`}
            >
              <span className="font-mono max-w-40 truncate">{file.name}</span>
              <button
                onClick={(e) => { e.stopPropagation(); closeTab(tabId); }}
                className="w-4 h-4 rounded-sm flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-zzw-border transition-all"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          );
        })}
      </div>

      <div className="flex-1 relative" ref={editorRef}>
        <MonacoWrapper
          file={activeFile}
          onMount={handleEditorDidMount}
        />
      </div>
    </div>
  );
}

function MonacoWrapper({
  file,
  onMount,
}: {
  file: { id: string; name: string; content: string };
  onMount: (editor: import('monaco-editor').editor.IStandaloneCodeEditor, monaco: typeof import('monaco-editor')) => void;
}) {
  const [Editor, setEditor] = useState<React.ComponentType<{
    height: string;
    defaultLanguage: string;
    defaultValue: string;
    theme: string;
    onMount: typeof onMount;
    loading: React.ReactNode;
  }> | null>(null);
  const [error, setError] = useState(false);

  useState(() => {
    import('@monaco-editor/react').then((mod) => {
      setEditor(() => mod.default);
    }).catch(() => {
      setError(true);
    });
  });

  if (error) {
    return (
      <textarea
        value={file.content}
        readOnly
        className="w-full h-full bg-zzw-bg text-zzw-text font-mono text-sm p-4 resize-none focus:outline-none"
        style={{ tabSize: 4 }}
      />
    );
  }

  if (!Editor) {
    return (
      <div className="w-full h-full bg-zzw-bg flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-zzw-cyan/30 border-t-zzw-cyan rounded-full animate-spin mx-auto mb-3" />
          <p className="text-zzw-text-dim text-xs">加载编辑器...</p>
        </div>
      </div>
    );
  }

  return (
    <Editor
      height="100%"
      defaultLanguage="hsharp"
      defaultValue={file.content}
      theme="zzw-dark"
      onMount={onMount}
      loading={
        <div className="w-full h-full bg-zzw-bg flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-zzw-cyan/30 border-t-zzw-cyan rounded-full animate-spin mx-auto mb-3" />
          <p className="text-zzw-text-dim text-xs">加载编辑器...</p>
        </div>
      }
    />
  );
}