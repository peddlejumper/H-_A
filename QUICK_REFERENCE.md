# H# 快速参考

**当前版本**: v0.4.1（2026-06-20）
**最后更新**: 2026-07-03
**状态**: Kotlin HVM 主运行时，821+ 测试用例全部通过

---

## 🚀 快速开始

### 双运行时架构

| 运行时 | 用途 | 入口 |
|--------|------|------|
| **Python VM** | 开发、调试、自举编译 | `python3 hsharp.py` |
| **Kotlin HVM** | 发布、跨平台打包、生产运行 | `java -jar hsharp-kotlin-compiler.jar` |

### 运行 H# 程序

```bash
# 方式 1: Python VM 直接运行 .hto
python3 hsharp.py app.hto

# 方式 2: Python VM 编译 + 运行 .hbc
python3 hsharp.py --emit-bc app.hto    # 生成 app.hbc
python3 hsharp.py --run-bc app.hbc     # 运行

# 方式 3: Kotlin HVM 运行 .hbc（推荐生产用）
java -jar hsharp-kotlin-compiler/build/libs/hsharp-runtime.jar app.hbc

# 方式 4: Kotlin HVM CLI
java -jar hsharp-kotlin-compiler/build/libs/hsharp-kotlin-compiler.jar run app.hbc
```

### 打包为原生应用

```bash
java -jar hsharp-kotlin-compiler/build/libs/hsharp-kotlin-compiler.jar compile \
    app.hbc --name MyApp --target mac --output dist/ --app-version 1.0.0
# 产出 dist/MyApp-app/MyApp.app
```

### 运行测试

```bash
cd hsharp-kotlin-compiler
bash scripts/test.sh                    # 35 个编译器测试
python3 lib-tests/run_lib_tests.py      # 8 个算法/OO 测试
python3 zzwui-tests/run_zzwui_tests.py  # 14 个 zzwui 测试（521 cases）
```

---

## 📝 语言语法速览

### 变量与基础

```h#
let x = 42;              # 可变变量
let s = "hello";         # 字符串
let arr = [1, 2, 3];     # 列表
let d = {"a": 1, "b": 2};  # 字典
let n = null;            # null
let b = true;            # 布尔
let [a, b2, _] = arr;    # 解构赋值（_ 跳过该槽位）
```

### 控制流

```h#
# if/else
if (x > 5) {
    print("big");
} else {
    print("small");
}

# for-in（支持 list/string/dict）
for i in [1, 2, 3] { print(i); }
for c in "abc" { print(c); }
for k, v in {"a": 1} { print(k, v); }

# while
let i = 0;
while (i < 5) {
    print(i);
    i = i + 1;
    if (i == 3) { break; }
}
```

### 函数与 lambda

```h#
fn square(n) { return n * n; }
print(square(7));  # 49

let add = fn(a, b) { return a + b; };
print(add(3, 4));  # 7

# 默认参数（Python 风格，尾部对齐，仅字面量）
fn greet(name, greeting = "Hello") { return greeting + ", " + name; }
print(greet("World"));          # Hello, World
print(greet("H#", "Hi"));       # Hi, H#

# 变长参数（最后一个参数收集剩余实参为 list）
fn sum_all(...nums) {
    let total = 0;
    for n in nums { total = total + n; }
    return total;
}
print(sum_all(1, 2, 3, 4));     # 10

# 字符串格式化（位置占位符 {0} {1} ...）
print(fmt("{0} + {1} = {2}", 1, 2, 3));  # 1 + 2 = 3
```

### 类与继承

```h#
class Animal {
    let name;
    fn init(n) { name = n; }
    fn speak() { return "animal sound"; }
}

class Dog extends Animal {
    fn speak() { return "bark"; }
    fn super_speak() { return super.speak(); }
}

let d = new Dog("Rex");
print(d.speak());        # bark
print(d.super_speak());  # animal sound
```

### 泛型（v0.4.1）

```h#
class Box<T> {
    let value;
    fn init(v) { value = v; }
    fn get() { return value; }
}

fn identity<T>(x) { return x; }

let b = new Box<int>(42);
print(b.get());              # 42
print(identity<string>("hi"));  # hi
```

### Union 类型

```h#
union Result {
    Ok(int),
    Err(string)
}

let r = Result.Ok(42);
print(r);  # Ok(42)
```

### 异常处理

```h#
try {
    let x = 1 / 0;
} catch (e) {
    print("caught: " + str(e));
}
```

### async/await（v0.4.1）

```h#
async fn fetch_data() {
    return 42;
}

let result = await fetch_data();
print(result);  # 42
```

### 多线程并行（v0.4.1）

```h#
parallel fn work(n) {
    return n * n;
}

let f = work(7);       # 返回 HFuture
let r = await f;       # 49
print(r);
```

### Channel（v0.4.1）

```h#
let ch = chan int(10);     # 有缓冲 channel
chan_send(ch, 1);
chan_send(ch, 2);
print(chan_recv(ch));      # 1
print(chan_size(ch));      # 1
chan_close(ch);
```

### 结构化并发（v0.4.1）

```h#
concurrent {
    let a = await work(1);
    let b = await work(2);
    # 块结束时所有子任务必须完成
}
```

### 模式匹配（v0.4.1）

```h#
let x = 42;
match x {
    0 => print("zero"),
    n if n < 0 => print("negative"),
    n => print("positive: " + str(n)),
}
```

### 错误传播（v0.4.1）

```h#
fn risky() {
    throw "boom";
}

let result = risky()?;  # result == "boom"（异常被解包为值）
```

### 模块导入

```h#
import string_utils;
let s = str_trim("  hello  ");
print(s);  # "hello"
```

---

## 📦 标准库模块

### v0.4.1 新增模块

| 模块 | 函数数 | 说明 |
|------|--------|------|
| `assert_module` | 15 | assert_eq/ne/true/false/lt/gt/in/raises/... |
| `path_module` | 40+ | path_join/dirname/basename/glob/walk/... |
| `regex_module` | 13 | regex_test/first/all/sub/split/captures/... |
| `crypto_module` | 30+ | sha256/hmac/pbkdf2/base64/uuid/crc32/... |

### v0.4 自举模块（bootstrap/）

| 模块 | 函数数 | 说明 |
|------|--------|------|
| `string_utils` | 22 | str_trim/upper/lower/split/join/contains/... |
| `array_utils` | 27 | arr_sum/map/filter/reduce/sort/reverse/... |
| `math_utils` | 29+8常量 | is_prime/fibonacci/gcd/lcm/sqrt/abs/... |
| `datetime_module` | - | 时间日期 |
| `io_module` | - | IO 操作 |
| `net_module` | - | 网络请求 |
| `db_module` | - | 数据库 |
| `json_serializer` | - | JSON 序列化 |
| `formatter` | - | 代码格式化 |
| `linter` | - | 静态分析 |
| `perf_monitor` | - | 性能监控 |
| `env_optimized` | - | O(1) 环境变量查找 |

---

## 🔧 宿主函数（HNativeBridge.kt）

### 基础

```h#
print(x)              # 打印
len(x)                # 长度（list/dict/string）
type(x)               # 类型名
str(x)                # 转字符串
int(x)                # 转整数
push(arr, v)          # 列表追加
pop(arr)              # 列表弹出
range(n)              # 生成范围
has_key(d, k)         # 字典是否含 key
keys(d)               # 字典 keys
values(d)             # 字典 values
```

### 数学

```h#
fdiv(a, b)            # IEEE-754 真除法（区别于 / 的 floor 除法）
```

### 文件

```h#
file_write(path, content)
file_read(path)
file_delete(path)
file_info(path)             # 返回 {path, size, is_dir, is_file, mtime}
file_read_bytes(path)       # 返回 [0..255] int 列表
temp_file(prefix)
io_append_bytes(path, bytes)
```

### 正则

```h#
regex_test(pattern, str)
regex_first(pattern, str)
regex_all(pattern, str)
regex_sub(pattern, repl, str)
regex_split(pattern, str)
regex_captures(pattern, str)
regex_named_groups(pattern, str)
```

### GUI（zzwui 基础）

```h#
native_create_window(title, w, h)
native_draw_rect(x, y, w, h, color)
native_set_clip(x, y, w, h)
native_parse_color(str)
native_lerp_color(c1, c2, t)
native_get_events()
# ... 30+ gui_* natives
```

### Channel

```h#
chan_try_send(ch, v)    # 返回 bool，满则 false 不阻塞
chan_try_recv(ch)       # 返回值或 null，空则 null 不阻塞
chan_size(ch)           # 当前元素数
chan_close(ch)          # 关闭 channel
```

---

## 📁 项目结构

```
v0.4/
├── .project_context/          ← 项目文档（权威）
│   ├── README.md              ← 快速参考 + 文档地图
│   ├── PROJECT_CONTEXT.md     ← 项目总览
│   ├── HBC_FORMAT_SPEC.md     ← .hbc 格式规范
│   ├── PROGRESS.md            ← 进度跟踪
│   ├── NOTES.md               ← 开发笔记
│   └── SUMMARY.md             ← 文档清单
├── hsharp-kotlin-compiler/    ← Kotlin HVM 主运行时
│   ├── src/main/kotlin/com/hsharp/
│   │   ├── compiler/          ← HbcReader + Main(CLI)
│   │   ├── runtime/           ← HVM + HValue + HNativeBridge + WorkerPool
│   │   └── platform/          ← Packager(jpackage)
│   ├── src/test/.../CompilerTests.kt  ← 35 测试
│   ├── lib-tests/             ← 8 算法测试
│   ├── stress-tests/          ← 7 压力测试
│   ├── zzwui-tests/           ← 14 zzwui 测试（521 cases）
│   └── scripts/build.sh       ← 构建（无 Gradle）
├── H#_v0.4.1_Package/         ← v0.4.1 发布包（最权威入口）
├── bootstrap/                 ← 50+ H# 自举模块（.hto 源码）
├── hsharp-ide/                ← .NET/Avalonia IDE
├── compiler.py / interpreter.py / bytecode.py / hsharp.py  ← Python 编译器/VM
└── VERSION                    ← "0.4.1"
```

---

## 📊 测试结果

```
Kotlin 编译器测试:   35/35 ✅
lib-tests:            8/8 ✅
stress-tests:         7/7 ✅
zzwui-tests:        521/521 ✅
新特性测试(15-20): 154+/154+ ✅
─────────────────────────────
总计:               821+ 全部通过 ✅
```

---

## 📖 更多信息

- 项目总览: [`.project_context/PROJECT_CONTEXT.md`](file:///Users/peddlejumper/H#/v0.4/.project_context/PROJECT_CONTEXT.md)
- .hbc 格式: [`.project_context/HBC_FORMAT_SPEC.md`](file:///Users/peddlejumper/H#/v0.4/.project_context/HBC_FORMAT_SPEC.md)
- Kotlin 编译器: [`hsharp-kotlin-compiler/README.md`](file:///Users/peddlejumper/H#/v0.4/hsharp-kotlin-compiler/README.md)
- 完整变更日志: [`H#_v0.4.1_Package/CHANGELOG/CHANGELOG.md`](file:///Users/peddlejumper/H#/v0.4/H#_v0.4.1_Package/CHANGELOG/CHANGELOG.md)
- 语言指南: [`docs/HSharp-Guide.md`](file:///Users/peddlejumper/H#/v0.4/docs/HSharp-Guide.md)

---

**版本**: v0.4.1 | **最后更新**: 2026-07-03
