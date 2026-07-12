# H# 学习指南（初稿）

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

VM 的实现位于 `bytecode.py`，该文件描述了运算语义、调用模型（新 VM 实例或 Python 可调用）、异常展开与类实例化逻辑。

---

**编译器与自举（Self-hosting）**

自举目标：用 H# 本身实现编译器，使 H# 能编译出 H# 的字节码并运行。实现路线：

1. 在 `bootstrap/` 中实现 H# 版本的 `tokenize`, `parse`, `interpret` 与 `compile`（示例：`bootstrap/compiler.hto`）。
2. 使用 Python 托管的解释器加载并执行这些 H# 模块（已有 `bootstrap/use_tokenize.py` 用于桥接）。
3. 调用 H# `compile(ast)`，将返回 `{"instructions": [...], "consts": [...]}`，然后在 Python VM 上运行。
4. 逐步替换 Python 端编译器，直到完整自举完成；之后可以扩展到生成原生二进制或更紧凑的包。

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
