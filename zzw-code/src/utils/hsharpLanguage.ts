import type { languages } from 'monaco-editor';

export const HSHARP_LANGUAGE_ID = 'hsharp';

export const hsharpLanguageConfig: languages.IMonarchLanguage = {
  keywords: [
    'fn', 'let', 'if', 'else', 'for', 'while', 'return', 'break',
    'continue', 'import', 'class', 'new', 'this', 'super', 'nullptr',
    'true', 'false', 'in', 'dzzw_spawn', 'dzzw_await', 'dzzw_parallel_map',
    'dzzw_worker_count', 'dzzw_pending_count',
    'dzzw_channel_create', 'dzzw_channel_send', 'dzzw_channel_recv', 'dzzw_channel_free',
    'dzzw_mutex_create', 'dzzw_mutex_lock', 'dzzw_mutex_unlock', 'dzzw_mutex_free',
  ],

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
};

export const hsharpEditorTheme: languages.IMonarchLanguage = {
  ...hsharpLanguageConfig,
};