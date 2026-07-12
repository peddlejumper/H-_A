# H# 学习指南（初稿）

> **版本**: v0.4.1（2026-06-20）
> **最后更新**: 2026-07-03
> **双运行时**: Python VM（开发调试）+ Kotlin HVM（发布打包）
>
> 本指南覆盖 H# v0.4.1 语法。运行 .hto 的方式：
> - 开发：`python3 hsharp.py app.hto`
> - 生产：先编译 `.hto → .hbc`，再用 `java -jar hsharp-kotlin-compiler/build/libs/hsharp-runtime.jar app.hbc`
>
> 详见 `.project_context/PROJECT_CONTEXT.md` 与 `hsharp-kotlin-compiler/README.md`

本指南面向想快速上手并深入理解 H# 语言、运行时和自举流程的读者。内容包含快速开始、语言要点、例子、字节码与虚拟机解读，以及如何让 H# 自举自己（用 H# 编译器编译 H#）。

目录
- 快速开始
- 基本语法与数据类型
- 控制流与集合
- 函数、Lambda 与闭包
- 异常处理（try / catch / throw）
- 类与面向对象
- 标准库与内建函数
- 字节码与 VM 指令集
- 编译器与自举（self-hosting）
- 示例与练习
- 附录：常用 opcodes / AST 形状
- v0.4.1 新特性
  - 泛型
  - async / await
  - 多线程并行（@parallel / parallel）
  - Channel（chan T）
  - 结构化并发（concurrent{}）
  - 模式匹配（match）
  - 错误传播（expr?）
  - v0.4.1 标准库模块
  - Native Bridge 新增

---

**快速开始**

先决条件：Python 3.x

- 运行 Python 托管的 H# 解释器（开发时常用）

```
python3 hsharp.py path/to/file.hto
# 或者运行引导/测试脚本：
python3 bootstrap/run_bootstrap.py
python3 bootstrap/use_tokenize.py
```

示例程序（保存为 `sample.hto`）：

```
let x = 1;
print(x);
```

把上面保存后用 `python3 hsharp.py sample.hto` 运行，或者直接在 REPL/解释器中执行。

---

**基本语法与数据类型**

- 变量：`let name = expr;`（也支持 `auto`）
- 字面量：数字、字符串（双引号）、布尔 `true/false`、`null`
- 数组：`[1, 2, 3]`
- 字典：`{"k": "v"}`
- 函数声明：

```
fn add(a, b) {
    return a + b;
}
```

- 匿名函数 / Lambda：`let f = fn(x) { print(x); };`

**运算符**
- 算术：`+ - * /`
- 比较：`==, !=, >, <, >=, <=`
- 逻辑：`and, or, not`（短路逻辑）

---

**控制流与集合**

- 条件：

```
if (cond) { ... } else { ... }
```

- 循环：`while (cond) { ... }`, `for` 支持迭代语法
- 索引与成员访问：`a[0]`, `obj.field`

---

**函数、Lambda 与闭包**

- 函数可以作为值传递。Lambda 使用 `fn(...) { ... }`。
- 闭包：当前运行时支持将定义时的自由变量通过字节码常量或运行时父环境传递（实现细节见字节码/VM 章节）。

例：

```
let x = 42;
let f = fn() { print(x); };
f();  # 输出 42
```

---

**异常处理**

语法：

```
try {
    throw "oops";
} catch (e) {
    print(e);
}
```

编译器会生成 `SETUP_EXCEPT`/`POP_EXCEPT`/`RAISE` 等字节码，VM 会在运行时进行栈展开并跳转到异常处理器。

---

**类与面向对象**（概览）

- 定义类、方法、字段以及继承、接口（interface）语法均已在解析层提供。示例：

```
class Point {
    let x = 0;
    let y = 0;
    fn init(self, x, y) { self.x = x; self.y = y; }
}
```

运行时（VM）通过字典对象存储类/实例结构，并支持方法调用、私有字段检查等。

---

**标准库与内建函数**

常用内建函数示例：`len()`, `push`, `pop`, `read_file`, `write_file`。在 Python 托管环境中还会暴露一些主机函数用于 I/O 与打包。

---

**字节码与 VM 指令集（摘录）**

> **主运行时**：Kotlin HVM 栈机解释器（位于 `hsharp-kotlin-compiler/`，核心为 `HVM.kt`），实现了 40+ opcode，是 v0.4.1 的发布运行时。Python 端 `bytecode.py` 作为开发调试用 VM，与 HVM 在指令语义上保持一致。

常见字节码指令（非穷举）：
- `LOAD_CONST`, `LOAD_NAME`, `STORE_NAME`
- `PRINT`, `POP_TOP`
- `MAKE_LIST`, `MAKE_DICT`, `GET_ITEM`, `SET_ITEM`
- `LOAD_ATTR`, `STORE_ATTR`
- `BINARY_ADD`, `BINARY_SUB`, `BINARY_MUL`, `BINARY_DIV`
- `UNARY_NOT`, `COMPARE_OP`
- `JUMP_IF_FALSE`, `JUMP`
- `CALL_FUNCTION`, `CALL_METHOD`, `CALL_VALUE`, `RETURN_VALUE`
- `SETUP_EXCEPT`, `POP_EXCEPT`, `RAISE`
- `CALL_NEW`, `HALT`, `IMPORT_NAME`, `IMPORT_FILE`
- v0.4.1 新增：`SETUP_PROPAGATE` / `POP_PROPAGATE`（`?` 错误传播）、async/await 与 channel 相关 opcode（见 HVM.kt）

`.hbc` 是 **JSON 容器格式**（非二进制），包含 `instructions`、`consts` 等字段，可被 Kotlin HVM 与 Python VM 共同加载。开发调试用 VM 实现位于 `bytecode.py`，该文件描述了运算语义、调用模型（新 VM 实例或 Python 可调用）、异常展开与类实例化逻辑；生产环境使用 Kotlin HVM。

---

**编译器与自举（Self-hosting）**

自举目标：用 H# 本身实现编译器，使 H# 能编译出 H# 的字节码并运行。实现路线：

1. 在 `bootstrap/` 中实现 H# 版本的 `tokenize`, `parse`, `interpret` 与 `compile`（示例：`bootstrap/compiler.hto`）。
2. 使用 Python 托管的解释器加载并执行这些 H# 模块（已有 `bootstrap/use_tokenize.py` 用于桥接）。
3. 调用 H# `compile(ast)`，将返回 `{"instructions": [...], "consts": [...]}`，然后在 Python VM 上运行。
4. 逐步替换 Python 端编译器，直到完整自举完成；之后可以扩展到生成原生二进制或更紧凑的包。

**v0.4.1 编译/运行管线（更新）**：

```
.hto 源码  ──[ Python 编译器: lexer.py / parser.py / compiler.py ]──▶  .hbc (JSON 容器)
                                                                         │
                                          ┌──────────────────────────────┴──────────────────────────────┐
                                          ▼                                                             ▼
                            python3 hsharp.py app.hbc                            java -jar hsharp-kotlin-compiler/build/libs/hsharp-runtime.jar app.hbc
                            （Python VM，开发调试）                              （Kotlin HVM，发布打包，主运行时）
```

- `.hto` 源码由 **Python 编译器**（`lexer.py` + `parser.py` + `compiler.py`）编译为 `.hbc`（JSON 容器格式）。
- `.hbc` 最终由 **Kotlin HVM** 运行（`HVM.kt` 栈机解释器，40+ opcode）。
- Python VM（`bytecode.py`）仅用于开发调试与自举阶段，与 HVM 在字节码语义上保持一致。

---

**示例与练习**

练习：
- 写一个递归的 factorial 函数并测试性能。
- 用 lambda 实现 map/filter 的小例子。
- 实现一个小模块并用 `import` 将其载入。
- 扩展 `bootstrap/compiler.hto`，让它支持更多 AST 节点并通过 `use_tokenize.py` 验证。

---

**附录：参考**
- 源码入口：`lexer.py`, `parser.py`, `compiler.py`, `bytecode.py`, `interpreter.py`
- 引导实现：`bootstrap/` 目录下的 `.hto` 文件（H# 实现）
- 若要深入字节码与 VM，请阅读 `bytecode.py` 中的 `VM.run()` 实现。

---

下一步
- 我可以把上面每一章扩展成完整章节（示例、习题、实现细节）。你希望我先扩展哪一章？

---

## 详细语法与实战示例

下面给出更具体的语法要点、运行示例与常见调试技巧，方便教学与课堂演示。

### 字面量、变量与注释（回顾）

- 注释以 `#` 开头。
- 数字和布尔直接作为常量；字符串使用双引号。
- 变量用 `let` 声明；`auto` 也可用于类型推断。

示例：

```hto
# 变量与字面量
let n = 10;
let s = "hello";
let ok = true;
```

### 表达式优先级（简要）

- 乘除优先于加减；比较运算在逻辑运算之前。
- 使用括号显式控制求值顺序：`(a + b) * c`。

示例：

```hto
let v = 1 + 2 * 3;   # v == 7
let w = (1 + 2) * 3; # w == 9
```

### 函数与闭包（教学重点）

- 函数能作为值传递；函数对象在运行时作为字节码常量存在。
- 闭包可以捕获外部变量：教学时可演示编译器如何把自由变量列表加入函数对象，或通过运行时 parent 环境查找。

练习示例：实现计数器生成器

```hto
fn make_counter() {
    let i = 0;
    let inc = fn() { i = i + 1; return i; };
    return inc;
}

let c = make_counter();
print(c()); # 1
print(c()); # 2
```

教学要点：解释为什么 `i` 的值在 `inc` 多次调用间保持。

### 异常与错误处理（教学提示）

- 使用 `try { ... } catch (e) { ... }` 演示抛出与捕获。
- 结合 `SETUP_EXCEPT`/`RAISE`解释编译器生成的字节码以及 VM 的栈展开。

示例：

```hto
try {
    throw "bad";
} catch (e) {
    print("caught: " + e);
}
```

### 调试与运行技巧

- 在开发编译器/解释器时，可把 AST 序列化打印，或直接在 Python 层运行 `use_tokenize.py` 做端到端调试。
- 常用命令：

```bash
python3 bootstrap/use_tokenize.py   # 调试 tokenize/parse/compile 的端到端桥接
python3 hsharp.py some_file.hto     # 运行 H# 程序
```

### 教学练习建议（逐步递进）

1. Hello world → 变量与打印 → 条件语句
2. 数组/字典练习：实现 map/filter
3. 函数与递归：实现 factorial，并比较递归/循环版本
4. 闭包练习：计数器与简单状态机
5. 扩展练习：在 `bootstrap/compiler.hto` 中添加对 `Lambda` 的编译支持并验证输出字节码

---

如果你确认要我把某一章写成完整教学材料（含讲义、示例代码与习题），请告诉我优先级（例如：先写“函数与闭包”章节）。

---

# v0.4.1 新特性

本章节覆盖 H# v0.4.1（2026-06-20）引入的全部新特性。所有特性均已在 Kotlin HVM（主运行时）与 Python VM（开发调试）中实现，语义保持一致。

## 泛型（Generics）

H# v0.4.1 引入参数化类型，支持类与函数的泛型声明。泛型在运行时通过反射字段 `__type_args__` / `__type_params__` 暴露。

### 类泛型

```hto
class Box<T> {
    let value = null;
    fn init(self, v) { self.value = v; }
    fn get(self) { return self.value; }
}

let b = new Box<int>(42);
print(b.get());           # 42
print(b.__type_args__);   # ["int"]
```

### 函数泛型

```hto
fn identity<T>(x) {
    return x;
}

let s = identity<string>("hi");
let n = identity<int>(7);
```

### 反射字段

- `class.__type_params__`：类的类型参数列表（如 `["T"]`）。
- `instance.__type_args__`：实例化时绑定的具体类型列表（如 `["int"]`）。
- `fn.__type_params__`：函数的类型参数列表。

> 泛型类型检查在 v0.4.1 中为可选/弱检查，主要用于反射与文档化；运行时不强制擦除或实例化代码生成。

---

## async / await

v0.4.1 引入异步函数与 await 表达式，底层基于 `HFuture` 对象。**顶层 await 被允许**（top-level await），无需包装在 async 块中。

### 声明与调用

```hto
async fn fetch_data(url) {
    # ... 异步操作 ...
    return result;
}

let data = await fetch_data("https://example.com");
print(data);
```

### 反射

- 异步函数对象带有 `is_async = true` 标志。
- 调用 async fn 返回 `HFuture` 实例；`await` 触发其执行并阻塞等待结果。

```hto
async fn task() { return 1; }
let f = task();          # HFuture
print(f.is_async);       # true
let r = await f;         # 1
```

> 顶层 await 允许在模块顶层直接写 `let x = await expr;`，编译器会自动将模块入口视为异步上下文。

---

## 多线程并行（@parallel / parallel）

v0.4.1 提供两种声明并行函数的语法，底层由 `WorkerPool` 调度线程执行。

### 声明方式

```hto
# 装饰器风格
@parallel
fn heavy_compute(x) {
    return x * x;
}

# 关键字风格
parallel fn heavy_compute2(x) {
    return x * x;
}
```

### 调用与调度

- 调用 parallel fn 会将任务提交到 `WorkerPool`，立即返回句柄；结果通过 `await` 或 channel 取回。
- `parallelism()` 内建函数返回当前 WorkerPool 线程数。

```hto
print(parallelism());   # 例如 8

@parallel
fn square(x) { return x * x; }

let h1 = square(10);
let h2 = square(20);
let r1 = await h1;      # 100
let r2 = await h2;      # 400
```

### 反射

- parallel fn 对象带有 `is_parallel = true` 标志。

---

## Channel（chan T）

v0.4.1 引入 Go 风格的 Channel，用于线程间通信。

### 创建

```hto
let c1 = chan int;        # 无缓冲通道
let c2 = chan int(4);     # 容量为 4 的有缓冲通道
```

### 操作（内建函数）

| 函数 | 说明 |
|------|------|
| `chan_send(c, v)` | 向通道发送值；无缓冲时阻塞直到对方接收，有缓冲时缓冲满则阻塞 |
| `chan_recv(c)` | 从通道接收值并返回；缓冲空时阻塞 |
| `chan_close(c)` | 关闭通道 |
| `chan_size(c)` | 返回当前缓冲区中元素数量 |
| `try_send(c, v)` | 非阻塞发送；成功返回 true，否则 false |
| `try_recv(c)` | 非阻塞接收；返回 `{ok: true, value: v}` 或 `{ok: false}` |

### Go 风格语义

- 对已关闭通道 `chan_recv` 在缓冲耗尽后返回零值/EOF 信号。
- 对已关闭通道 `chan_send` 抛出异常。
- `chan_close` 可重复调用（幂等或抛出，依实现）。

```hto
let c = chan int(2);
chan_send(c, 1);
chan_send(c, 2);
print(chan_size(c));     # 2
print(chan_recv(c));     # 1
print(try_recv(c));      # {ok: true, value: 2}
chan_close(c);
```

---

## 结构化并发（concurrent{}）

v0.4.1 引入 `concurrent { ... }` 块，建立父-子任务层级，提供异常传播与取消传播语义（类似 Trio / Swift Structured Concurrency）。

### 基本用法

```hto
concurrent {
    let r1 = await task_a();
    let r2 = await task_b();
}
```

### 语义

- **父-子层级**：块内启动的所有任务都是该 concurrent 块的子任务；父任务在块结束前等待所有子任务完成。
- **异常传播**：任一子任务抛出未捕获异常时，异常向上传播到父 concurrent 块。
- **取消传播**：父块异常退出时，所有未完成的子任务收到取消信号。
- **嵌套**：concurrent 块可嵌套，形成任务树；取消与异常逐层传播。

```hto
concurrent {
    concurrent {
        # 子任务 ...
    }
    # 兄弟任务 ...
}
```

---

## 模式匹配（match）

v0.4.1 引入 `match` 表达式，支持 7 种模式与可选 guard。

### 语法

```hto
match expr {
    pattern => body;
    pattern if guard => body;
    ...
}
```

### 7 种模式

| # | 模式 | 示例 | 说明 |
|---|------|------|------|
| 1 | 通配 `_` | `_ => "any"` | 匹配任意值，不绑定 |
| 2 | 名称绑定 | `x => print(x)` | 匹配任意值并绑定到 `x` |
| 3 | 字面量 | `42 => "forty-two"` | 精确匹配字面量（数字/字符串/布尔/null） |
| 4 | 类型 `is T as x` | `is int as n => ...` | 类型匹配并绑定 |
| 5 | 变体 `Variant(x, y)` | `Some(v) => v` | 匹配 union 变体并解构字段 |
| 6 | 通道发送 `chan send(_)` | `chan send(v) => ...` | 匹配通道发送事件 |
| 7 | 通道接收 `chan recv(v)` | `chan recv(v) => print(v)` | 匹配通道接收事件 |
| — | 通道关闭 `chan close` | `chan close => ...` | 匹配通道关闭事件（常与 6/7 配合） |

### 示例

```hto
match value {
    0 => print("zero");
    is int as n => print("int: " + n);
    Some(v) => print("some: " + v);
    chan recv(v) => print("got: " + v);
    chan close => print("closed");
    _ => print("other");
}
```

### Guard（守卫）

```hto
match x {
    n if n > 0 => print("positive");
    n if n < 0 => print("negative");
    _ => print("zero");
}
```

### 非穷尽处理

- 若没有任何模式匹配且无 `_` 兜底，运行时抛出 `MatchError` 异常。

---

## 错误传播（expr?）

v0.4.1 引入 `?` 后缀操作符，用于简洁的错误传播。语义等价于 `try { expr } catch (e) { return e; }`，即捕获异常并作为返回值向上传播。

### 语法

```hto
let result = risky_op()?;
# 或
fn load() {
    let data = read_file(path)?;   # 失败则立即 return 异常
    return parse(data);
}
```

### 字节码

- `expr?` 编译为 `SETUP_PROPAGATE` / `POP_PROPAGATE` 包裹的表达式求值。
- 与 `try/catch` 的区别：`?` 专用于"出错即返回"的早退路径，不进入 catch 块体。

```hto
fn divide(a, b) {
    let q = fdiv(a, b)?;     # 除零则传播异常
    return q;
}
```

---

## v0.4.1 标准库模块

v0.4.1 新增 4 个标准库模块，通过 `import` 加载。

### assert_module（15 函数）

断言与测试辅助函数集合，包括 `assert_true`, `assert_false`, `assert_eq`, `assert_ne`, `assert_gt`, `assert_lt`, `assert_ge`, `assert_le`, `assert_in`, `assert_not_in`, `assert_is`, `assert_is_not`, `assert_almost_eq`, `assert_raises`, `fail` 等。

```hto
import assert;
assert.assert_eq(1 + 1, 2);
assert.assert_raises(fn() { throw "x"; });
```

### path_module（40+ 函数）

跨平台路径操作，包括 `join`, `split`, `basename`, `dirname`, `extname`, `stem`, `normalize`, `resolve`, `relative`, `is_absolute`, `is_relative`, `exists`, `get_size`, `get_mtime`, `list_dir`, `walk`, `split_ext`, `common_prefix`, `expanduser`, `expandvars` 等。

```hto
import path;
let p = path.join("a", "b", "c.hbc");
print(path.basename(p));   # c.hbc
print(path.extname(p));    # .hbc
```

### regex_module（13 函数）

正则表达式操作，包括 `compile`, `match`, `search`, `findall`, `sub`, `split`, `escape`, `fullmatch`, `finditer`, `groups`, `group`, `pattern`, `flags` 等。

```hto
import regex;
let r = regex.compile("\\d+");
let m = regex.match(r, "123");
print(regex.findall(r, "a1b22c333"));   # ["1", "22", "333"]
```

### crypto_module（30+ 函数）

加密/哈希/编码，包括 `md5`, `sha1`, `sha256`, `sha512`, `hmac_sha256`, `hmac_sha512`, `base64_encode`, `base64_decode`, `hex_encode`, `hex_decode`, `url_encode`, `url_decode`, `aes_encrypt`, `aes_decrypt`, `random_bytes`, `random_int`, `uuid4`, `crc32`, `argon2`, `pbkdf2`, `scrypt` 等。

```hto
import crypto;
print(crypto.sha256("hello"));
print(crypto.uuid4());
print(crypto.base64_encode("data"));
```

---

## Native Bridge 新增

v0.4.1 在 Native Bridge（主机函数桥）层新增以下原生函数，供 H# 程序通过 FFI 调用。

### 数学/除法

- `fdiv(a, b)`：真除法（浮点结果），与 `/`（整数除法当操作数为整数时）区分。

### 文件 I/O 扩展

- `file_delete(path)`：删除文件。
- `file_info(path)`：返回文件元信息（大小、mtime、类型等）。
- `file_read_bytes(path)`：以字节（字节数组）形式读取文件。
- `temp_file(suffix)`：创建临时文件并返回路径。
- `io_append_bytes(path, bytes)`：以字节方式追加写入文件。

### 正则（regex_*，7 函数）

- `regex_compile(pattern)`、`regex_match(re, s)`、`regex_search(re, s)`、`regex_findall(re, s)`、`regex_sub(re, repl, s)`、`regex_split(re, s)`、`regex_escape(s)`。

> 也可通过 `import regex` 标准库模块以更友好接口访问。

### GUI（gui_*，30+ 函数）

GUI 桥接函数集，覆盖窗口创建、控件、绘制、事件循环、对话框等，便于在 H# 中构建桌面应用原型。常用函数包括 `gui_init`, `gui_create_window`, `gui_create_button`, `gui_create_label`, `gui_create_input`, `gui_create_canvas`, `gui_draw_rect`, `gui_draw_text`, `gui_draw_line`, `gui_set_color`, `gui_run`, `gui_quit`, `gui_message_box`, `gui_file_dialog` 等（完整列表见 `hsharp-kotlin-compiler/README.md` 与 Native Bridge 实现）。

```hto
gui_init();
let w = gui_create_window("Demo", 640, 480);
gui_create_button(w, "Click me", 10, 10);
gui_run(w);
```

---

## 附：双运行时对照速查

| 维度 | Python VM | Kotlin HVM |
|------|-----------|------------|
| 位置 | `bytecode.py` | `hsharp-kotlin-compiler/`（`HVM.kt`） |
| 用途 | 开发调试 / 自举 | 发布打包 / 生产 |
| 入口 | `python3 hsharp.py app.hto` | `java -jar hsharp-runtime.jar app.hbc` |
| .hbc 格式 | JSON 容器 | JSON 容器（同一格式） |
| opcode 数 | 与 HVM 对齐 | 40+ |
| 并发 | 模拟 | 真实多线程（WorkerPool） |

> 详细 opcode 表、AST 节点形状与实现差异，请参阅 `.project_context/PROJECT_CONTEXT.md` 与 `hsharp-kotlin-compiler/README.md`。
