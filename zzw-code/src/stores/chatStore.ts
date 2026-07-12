import { create } from 'zustand';
import { set as idbSet, get as idbGet } from 'idb-keyval';
import type { ChatMessage, TerminalEntry } from '@/types';
import { useConfigStore } from './configStore';

const HSHARP_SYSTEM_PROMPT = `你是一个精通 H#（H-sharp）语言的 AI 编程助手，集成在 ZZW Code IDE 中。

## H# 语言概述
H# 是一门动态类型的脚本语言，支持函数式编程、面向对象编程和并发编程。

## 语法规则

### 变量声明
\`\`\`h#
let x = 42;
let name = "hello";
let arr = [1, 2, 3];
let obj = {};
let fn_ref = myFunc;
\`\`\`

### 函数定义
\`\`\`h#
fn add(a, b) {
    return a + b;
}

fn outer() {
    fn inner(x) {
        return x * 2;
    }
    return inner(5);
}
\`\`\`

### 控制流
\`\`\`h#
if (x > 0) {
    return "positive";
} else if (x < 0) {
    return "negative";
} else {
    return "zero";
}

for (let i = 0; i < n; i = i + 1) {
    print(i);
}

while (cond) {
    doSomething();
}
\`\`\`

### 字典和列表
\`\`\`h#
let d = {};
d["key"] = "value";
d["nested"] = {};
d["nested"]["deep"] = 42;
let v = d["key"];

let arr = [1, 2, 3];
arr[0] = 99;
let x = arr[1];
let len = len(arr);
\`\`\`

### 类与对象
\`\`\`h#
class Person {
    fn Person(name) {
        this.name = name;
    }
    fn greet() {
        return "Hello, " + this.name;
    }
}
let p = new Person("World");
print(p.greet());
\`\`\`

### 模块导入
\`\`\`h#
import "other.hto";
\`\`\`

### 注释
\`\`\`h#
// 单行注释
/* 多行
   注释 */
\`\`\`

## 数据类型
- int: 整数 (1, 42, -7)
- float: 浮点数 (3.14, -0.5)
- bool: 布尔值 (true, false)
- str: 字符串 ("hello")
- list: 列表 ([1, 2, 3])
- dict: 字典 ({"key": "value"})
- function: 函数引用
- class: 类定义
- instance: 类实例
- nil: 空值 (nullptr)

## 运算符
- 算术: +, -, *, /, %
- 比较: ==, !=, <, >, <=, >=
- 逻辑: &&, ||, !
- 赋值: =, +=, -=, *=

## 标准库函数

### 输入输出
- print(value): 打印值到控制台

### 类型转换
- str(value): 转为字符串
- int(value): 转为整数
- float(value): 转为浮点数
- typeof(value): 返回类型字符串 ("int", "str", "list", "dict", "function", "nil", etc.)

### 数据结构
- len(arr): 返回列表或字符串长度
- push(arr, value): 向列表追加元素并返回新长度
- pop(arr, index): 移除并返回指定位置元素（默认末尾）

### JSON
- json_serialize(value): 将任意值序列化为 JSON 字符串
- json_parse(json_str): 将 JSON 字符串解析为 H# 值

## DZZW 并发编程

DZZW 是 H# 的并发运行时，提供线程池和异步任务支持：

- dzzw_spawn(fn, args_list): 异步执行函数，返回 future 句柄（整数）
- dzzw_await(handle): 等待 future 完成并返回结果
- dzzw_parallel_map(fn, list): 并行对列表中每个元素执行函数，返回结果列表
- dzzw_worker_count(): 返回线程池中工作线程数量
- dzzw_pending_count(): 返回待处理任务数量

### 管道 (Channel)
- dzzw_channel_create(capacity): 创建有界管道，返回句柄
- dzzw_channel_send(handle, value): 向管道发送值
- dzzw_channel_recv(handle): 从管道接收值（阻塞直到有值）
- dzzw_channel_free(handle): 释放管道

### 互斥锁 (Mutex)
- dzzw_mutex_create(): 创建互斥锁，返回句柄
- dzzw_mutex_lock(handle): 加锁
- dzzw_mutex_unlock(handle): 解锁
- dzzw_mutex_free(handle): 释放互斥锁

## 代码风格
- 使用 4 空格缩进
- 函数名和变量名使用驼峰命名（camelCase）
- 类名使用 PascalCase
- 常量使用大写蛇形命名（UPPER_SNAKE_CASE）

## 回答原则
1. 你正在帮助用户编写 H# 代码。所有代码示例必须使用 H# 语法。
2. 当用户提供代码时，分析并指出语法错误、逻辑问题或改进建议。
3. 解释复杂的 H# 概念时，使用具体代码示例。
4. H# 不需要分号结尾（虽然分号是可选的）。
5. H# 使用 \`nullptr\` 表示空值，不要使用 \`null\` 或 \`None\`。
6. 函数定义使用 \`fn\` 关键字，不是 \`function\` 或 \`def\`。
7. 回答简洁、专业，直接解决用户的问题。`;

function makeId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  terminalEntries: TerminalEntry[];
  showTerminal: boolean;
  sendMessage: (content: string, codeContext: string) => Promise<void>;
  clearChat: () => void;
  toggleTerminal: () => void;
  addTerminalEntry: (type: TerminalEntry['type'], text: string) => void;
  clearTerminal: () => void;
  loadChatFromStorage: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  terminalEntries: [],
  showTerminal: false,

  sendMessage: async (content: string, codeContext: string) => {
    const { config, isConfigured } = useConfigStore.getState();
    if (!isConfigured || !config) return;

    const userMsg: ChatMessage = {
      id: makeId(),
      role: 'user',
      content,
      timestamp: Date.now(),
    };

    const assistantMsg: ChatMessage = {
      id: makeId(),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    };

    set((s) => ({
      messages: [...s.messages, userMsg, assistantMsg],
      isLoading: true,
    }));

    const contextBlock = codeContext
      ? `\n\n以下是当前编辑器中的代码上下文：\n\`\`\`h#\n${codeContext}\n\`\`\``
      : '';

    const messages = [
      { role: 'system' as const, content: HSHARP_SYSTEM_PROMPT },
      ...get().messages
        .filter((m) => m.role !== 'system')
        .slice(-20)
        .map((m) => ({ role: m.role, content: m.content })),
      { role: 'user' as const, content: content + contextBlock },
    ];

    try {
      const response = await fetch(config.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${config.apiKey}`,
        },
        body: JSON.stringify({
          model: config.model,
          messages,
          stream: true,
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`API ${response.status}: ${errText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            try {
              const parsed = JSON.parse(data);
              const delta = parsed.choices?.[0]?.delta?.content;
              if (delta) {
                fullContent += delta;
                set((s) => {
                  const msgs = [...s.messages];
                  const last = msgs[msgs.length - 1];
                  if (last && last.role === 'assistant') {
                    msgs[msgs.length - 1] = { ...last, content: fullContent };
                  }
                  return { messages: msgs };
                });
              }
            } catch {
              // skip malformed lines
            }
          }
        }
      }

      const ms = get().messages;
      await idbSet('zzw-chat-history', ms);
    } catch (error: unknown) {
      const errMsg = error instanceof Error ? error.message : 'Unknown error';
      set((s) => {
        const msgs = [...s.messages];
        const last = msgs[msgs.length - 1];
        if (last && last.role === 'assistant') {
          msgs[msgs.length - 1] = {
            ...last,
            content: `**错误**: ${errMsg}\n\n请检查 API 配置是否正确。`,
          };
        }
        return { messages: msgs };
      });
    } finally {
      set({ isLoading: false });
    }
  },

  clearChat: () => {
    set({ messages: [] });
    idbSet('zzw-chat-history', []).catch(() => {});
  },

  toggleTerminal: () => set((s) => ({ showTerminal: !s.showTerminal })),

  addTerminalEntry: (type, text) => {
    const entry: TerminalEntry = {
      id: makeId(),
      type,
      text,
      timestamp: Date.now(),
    };
    set((s) => ({
      terminalEntries: [...s.terminalEntries, entry].slice(-100),
    }));
  },

  clearTerminal: () => set({ terminalEntries: [] }),

  loadChatFromStorage: async () => {
    try {
      const msgs = await idbGet('zzw-chat-history') as ChatMessage[] | undefined;
      if (msgs && Array.isArray(msgs)) {
        set({ messages: msgs });
      }
    } catch {
      // ignore
    }
  },
}));