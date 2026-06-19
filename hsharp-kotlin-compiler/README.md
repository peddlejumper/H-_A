# hsharp-kotlin-compiler

把 H# Python VM 输出的 `.hbc` (JSON) 字节码打包成真正的跨平台原生应用。

## 工作流

```
.hto 源码  →  Python compiler.py  →  app.hbc  →  hsharp-kotlin-compiler  →  MyApp.app
              (开发阶段, 热重载)          (JSON)         (发布阶段, 一键打包)         (真原生)
```

开发用 Python VM，发布用本工具出 `.app` / `.exe` / Linux 可执行文件。

## 特性

- **零依赖** — 只需要 JDK 11+（`java` + `jpackage`），不用 Gradle，不用装 Kotlin
- **可移植** — 构建脚本自动从 Maven Central 拉 `kotlin-compiler-embeddable`
- **跨平台打包** — `jpackage` 在 macOS / Windows / Linux 上分别出 `.app` / `.exe` / ELF
- **字节码自愈** — `HbcReader.fixForLoopJumps` 自动修正 Python 编译器发出的
  for-loop 字节码 bug（不影响开发体验）

## 快速开始

### 1. 编译 .hto → .hbc

```bash
# 用 Python 编译器（开发时熟悉的工具链）
python3 -c "
import sys, json, time
sys.path.insert(0, '../HSharp_v0.4_Tests')
from lexer import Lexer
from parser import Parser
from compiler import Compiler
src = open('app.hto').read()
p = Parser(Lexer(src))
compiler = Compiler()
compiler.compile(p.parse())
hbc = {'version':'v0.4',
       'modules':{'main':{'instructions': compiler.instructions,
                          'consts': compiler.consts}},
       'built_at': int(time.time())}
json.dump(hbc, open('app.hbc','w'))
"
```

### 2. 打包成 macOS .app

```bash
./scripts/hsharp-kotlin-compiler compile app.hbc \
    --name MyApp --target mac --output dist/ --app-version 1.0.0
```

产出 `dist/MyApp-app/MyApp.app`，双击就能跑。

### 3. 直接跑（开发/调试）

```bash
./scripts/hsharp-kotlin-compiler run app.hbc
```

## CLI

| 子命令 | 说明 |
|--------|------|
| `version` | 打印工具版本 |
| `info <file.hbc>` | 列出 module / 常量池 / 指令流概览 |
| `validate <file.hbc>` | 校验 JSON 合法性 |
| `run <file.hbc>` | 直接用 HVM 跑（不打包） |
| `compile <file.hbc>` | 打 .app / .exe / Linux 镜像 |

`compile` 的参数：
- `--name <Name>`     应用名（必填）
- `--target mac|windows|linux`
- `--output <dir>`    输出目录
- `--app-version <v>` 至少 1.0.0（jpackage 限制）
- `--type embed|portable`  embed = 默认；portable = 不嵌 JRE
- `--main-class <fqcn>`  默认 `com.hsharp.runtime.HbcLauncher`

## 项目结构

```
hsharp-kotlin-compiler/
├── src/
│   ├── main/kotlin/com/hsharp/
│   │   ├── compiler/
│   │   │   ├── HbcReader.kt   ← JSON 解析 + 字节码修正
│   │   │   └── Main.kt        ← CLI
│   │   ├── runtime/
│   │   │   ├── HValue.kt      ← HNull / HNumber / HString / HList / HDict / ...
│   │   │   ├── HVM.kt         ← 栈机：全部 opcode
│   │   │   ├── HNativeBridge.kt
│   │   │   ├── HbcRunner.kt   ← 预加载模块
│   │   │   └── HbcLauncher.kt ← 应用入口
│   │   └── platform/
│   │       └── Packager.kt    ← jpackage 包装
│   └── test/kotlin/com/hsharp/compiler/
│       └── CompilerTests.kt   ← 8 个测试
├── scripts/
│   ├── build.sh
│   ├── test.sh
│   ├── hsharp-kotlin-compiler
│   └── hsharp-runtime
├── .kotlin/                   ← kotlinc jars 缓存
└── build/libs/
    ├── hsharp-kotlin-compiler.jar
    └── hsharp-runtime.jar
```

## 构建

```bash
# 第一次跑会从 Maven Central 下载 kotlinc jars 到 .kotlin/
./scripts/build.sh
```

产物：
- `build/libs/hsharp-kotlin-compiler.jar`  — CLI 工具
- `build/libs/hsharp-runtime.jar`          — 运行时（被打进 .app）

## 测试

```bash
./scripts/test.sh
```

8/8 通过：parser / 基础 runtime / 端到端编译并运行 / for-loop / 函数 / try-catch / 打包 .app。

## 架构

```
        ┌─────────────┐
        │   app.hbc   │   JSON
        └──────┬──────┘
               ↓
        ┌──────────────┐
        │  HbcReader   │   + fixForLoopJumps 字节码修正
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │  HbcRunner   │   预加载所有非 entry 模块的 STORE_NAME 到 globals
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │     HVM      │   栈机：frame / stack / handlers
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │ HNativeBridge│   print / len / push / pop / range / ...
        └──────┬───────┘
               ↓
        stdout
```

打包阶段：runtime jar + app.hbc 资源 → `jpackage --type app-image` → `.app`

## 支持的 H# 子集

当前 HVM 已经实现的：
- 字面量、变量、算术、位运算、比较
- list / dict 字面量与索引
- 函数定义与调用、lambda
- 类（继承、private 字段、static 方法、super()）
- Union 类型
- for-in 循环（HList / HString / HDict）
- try / catch
- 模块与导入
- 协程（语法占位，未完整实现）

还没实现的：
- 完整的协程调度
- 异步 / await
- 一些边缘的 host function

参考 `HNativeBridge.kt` 看目前可用的内置函数。

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `no kotlinc available` | 第一次跑没拉 jars | 让 `build.sh` 自己下 |
| `jpackage: invalid app-version "0.x.x"` | jpackage 不接受 0.x | 用 `--app-version 1.0.0` |
| `NoClassDefFoundError: kotlin/jvm/internal/Intrinsics` | jpackage 不认 Class-Path | 跑 `build.sh` 重新 repackage stdlib |
| for-loop 卡住 / 输出永远是第一个元素 | Python 编译器 bug | `HbcReader.fixForLoopJumps` 会自动修；如果是新加的模块格式，重新 build 一下 |

## 文档

- 项目上下文：`../.project_context/`
  - `PROJECT_CONTEXT.md`  — 完整项目说明
  - `PROGRESS.md`         — 进度跟踪
  - `NOTES.md`            — 开发笔记 + 问题解决日志
- 原 Python 编译器：`../HSharp_v0.4_Tests/`
- C VM 参考：`../hsvm.c`

## 许可证

(待定)
