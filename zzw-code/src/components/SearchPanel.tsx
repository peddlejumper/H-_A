import { useState, useRef, useEffect, useCallback } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { X, Search, Replace, ChevronDown, ChevronUp, Check } from 'lucide-react';
import type { editor } from 'monaco-editor';

interface SearchPanelProps {
  editor: editor.IStandaloneCodeEditor | null;
}

export default function SearchPanel({ editor }: SearchPanelProps) {
  const { searchPanelOpen, setSearchPanelOpen } = useUIStore();
  const [searchText, setSearchText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [matchCount, setMatchCount] = useState(0);
  const [currentMatch, setCurrentMatch] = useState(0);
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [wholeWord, setWholeWord] = useState(false);
  const [regex, setRegex] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (searchPanelOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [searchPanelOpen]);

  const findNext = useCallback(() => {
    if (!editor || !searchText) return;
    const model = editor.getModel();
    if (!model) return;

    const findOptions: editor.FindOptions = {
      searchString: searchText,
      matchCase: caseSensitive,
      matchWholeWord: wholeWord,
      regex: regex,
    };

    const found = editor.findNext(findOptions);
    if (found) {
      const selections = editor.getSelections();
      if (selections && selections.length > 0) {
        const position = selections[0].getStartPosition();
        const count = model.findMatches(
          searchText,
          model.getFullModelRange(),
          !caseSensitive,
          regex ? null : new RegExp(
            regex ? searchText : searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
            caseSensitive ? 'g' : 'gi'
          ),
          false
        ).length;
        setMatchCount(count);
        setCurrentMatch(Math.min(count, currentMatch + 1));
      }
    }
  }, [editor, searchText, caseSensitive, wholeWord, regex, currentMatch]);

  const findPrev = useCallback(() => {
    if (!editor || !searchText) return;
    const found = editor.findPrevious({
      searchString: searchText,
      matchCase: caseSensitive,
      matchWholeWord: wholeWord,
      regex: regex,
    });
    if (found && currentMatch > 1) {
      setCurrentMatch(c => c - 1);
    }
  }, [editor, searchText, caseSensitive, wholeWord, regex, currentMatch]);

  const replace = useCallback(() => {
    if (!editor || !searchText) return;
    editor.executeEdits('', editor.getSelections()?.map(sel => {
      const range = sel;
      return {
        range,
        text: replaceText,
      };
    }) || []);
    findNext();
  }, [editor, searchText, replaceText, findNext]);

  const replaceAll = useCallback(() => {
    if (!editor || !searchText) return;
    const model = editor.getModel();
    if (!model) return;

    let text = model.getValue();
    const flags = `${caseSensitive ? '' : 'i'}g`;
    const pattern = regex ? new RegExp(searchText, flags) : new RegExp(
      searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
      flags
    );
    const newText = text.replace(pattern, replaceText);
    model.setValue(newText);
    const count = (newText.match(pattern) || []).length;
    setMatchCount(0);
    setCurrentMatch(0);
  }, [editor, searchText, replaceText, caseSensitive, regex]);

  if (!searchPanelOpen) return null;

  return (
    <div className="absolute top-2 right-2 z-20 bg-zzw-surface border border-zzw-border rounded-lg shadow-lg w-72 animate-fade-in">
      <div className="flex items-center justify-between px-3 py-2 border-b border-zzw-border">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-zzw-text-dim" />
          <span className="text-sm font-medium text-zzw-text">搜索</span>
          {matchCount > 0 && (
            <span className="text-xs text-zzw-text-dim bg-zzw-bg px-1.5 py-0.5 rounded">
              {currentMatch}/{matchCount}
            </span>
          )}
        </div>
        <button
          onClick={() => setSearchPanelOpen(false)}
          className="w-6 h-6 rounded flex items-center justify-center text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="p-2 space-y-2">
        {/* 搜索输入 */}
        <div className="flex items-center gap-1">
          <input
            ref={inputRef}
            type="text"
            value={searchText}
            onChange={(e) => {
              setSearchText(e.target.value);
              setCurrentMatch(0);
              setMatchCount(0);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') findNext();
              if (e.key === 'Escape') setSearchPanelOpen(false);
            }}
            placeholder="查找..."
            className="flex-1 px-2 py-1.5 bg-zzw-bg border border-zzw-border rounded text-zzw-text text-xs placeholder-zzw-text-dim focus:outline-none focus:border-zzw-cyan"
          />
          <button
            onClick={findPrev}
            className="w-7 h-7 rounded flex items-center justify-center text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2 transition-colors"
            title="上一个"
          >
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={findNext}
            className="w-7 h-7 rounded flex items-center justify-center text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2 transition-colors"
            title="下一个"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* 替换输入 */}
        <div className="flex items-center gap-1">
          <input
            type="text"
            value={replaceText}
            onChange={(e) => setReplaceText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') replace();
            }}
            placeholder="替换..."
            className="flex-1 px-2 py-1.5 bg-zzw-bg border border-zzw-border rounded text-zzw-text text-xs placeholder-zzw-text-dim focus:outline-none focus:border-zzw-cyan"
          />
          <button
            onClick={replace}
            className="px-2 py-1.5 rounded text-xs text-zzw-text-dim hover:text-zzw-text hover:bg-zzw-surface2 transition-colors"
            title="替换"
          >
            <Replace className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={replaceAll}
            className="px-2 py-1.5 rounded text-xs text-zzw-cyan hover:bg-zzw-cyan/10 transition-colors"
            title="全部替换"
          >
            全部
          </button>
        </div>

        {/* 选项 */}
        <div className="flex flex-wrap gap-2 pt-1">
          <label className="flex items-center gap-1 text-xs text-zzw-text-dim cursor-pointer">
            <input
              type="checkbox"
              checked={caseSensitive}
              onChange={(e) => setCaseSensitive(e.target.checked)}
              className="w-3 h-3 bg-zzw-bg border-zzw-border text-zzw-cyan rounded focus:ring-zzw-cyan"
            />
            <span>区分大小写</span>
          </label>
          <label className="flex items-center gap-1 text-xs text-zzw-text-dim cursor-pointer">
            <input
              type="checkbox"
              checked={wholeWord}
              onChange={(e) => setWholeWord(e.target.checked)}
              className="w-3 h-3 bg-zzw-bg border-zzw-border text-zzw-cyan rounded focus:ring-zzw-cyan"
            />
            <span>全词匹配</span>
          </label>
          <label className="flex items-center gap-1 text-xs text-zzw-text-dim cursor-pointer">
            <input
              type="checkbox"
              checked={regex}
              onChange={(e) => setRegex(e.target.checked)}
              className="w-3 h-3 bg-zzw-bg border-zzw-border text-zzw-cyan rounded focus:ring-zzw-cyan"
            />
            <span>正则</span>
          </label>
        </div>
      </div>
    </div>
  );
}