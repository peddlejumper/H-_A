# H# Kotlin 编译器集成指南

**当前版本**: v0.4.1（2026-06-20）
**最后更新**: 2026-07-03

> ⚠️ 本文档已重写。历史版本描述的 `KotlinCodeGenerator` 源到源转译方案已废弃，实际采用 HVM 栈机解释器架构。详见 [`.project_context/PROJECT_CONTEXT.md`](file:///Users/peddlejumper/H#/v0.4/.project_context/PROJECT_CONTEXT.md) 的"架构真相"章节。

---

## 概述

H# Kotlin 编译器（`hsharp-kotlin-compiler/`）是 H# 的**主运行时**，将 Python 编译器生成的 `.hbc` JSON 字节码容器通过 HVM 栈式虚拟机解释执行，并通过 jpackage 打包为跨平台原生应用。

## 工作流程

### 开发阶段（Python VM）

开发者使用 Python VM 进行热重载开发与调试：

```bash
# 编写 H# 源码
vim myapp.hto

# 用 Python VM 直接运行（树遍历解释器）
python3 hsharp.py myapp.hto

# 或编译为字节码后用 Python 栈机运行
python3 hsharp.py --emit-bc myapp.hto     # 生成 myapp.hbc
python3 hsharp.py --run-bc myapp.hbc      # 运行 .hbc
python3 hsharp.py --opt myapp.hto         # 优化模式
```

### 发布阶段（Kotlin HVM）

需要发布独立原生应用时，使用 Kotlin HVM：

```bash
cd hsharp-kotlin-compiler

# 构建（首次会从 Maven Central 下载 kotlinc jars）
./scripts/build.sh
# 产出: build/libs/hsharp-kotlin-compiler.jar + hsharp-runtime.jar

# 验证字节码
java -jar build/libs/hsharp-kotlin-compiler.jar validate myapp.hbc

# 直接运行（不打包）
java -jar build/libs/hsharp-kotlin-compiler.jar run myapp.hbc

# 打包为原生应用
java -jar build/libs/hsharp-kotlin-compiler.jar compile \
    myapp.hbc --name MyApp --target mac --output dist/ --app-version 1.0.0
# 产出: dist/MyApp-app/MyApp.app（macOS）
```

## 架构设计

### 执行流水线

```
        ┌─────────────┐
        │   app.hbc   │   JSON 容器（非二进制）
        └──────┬──────┘
               ↓
        ┌──────────────┐
        │  HbcReader   │   MiniJson 解析 + fixForLoopJumps 字节码自愈
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │  HbcRunner   │   预加载非 entry 模块的 STORE_NAME 到 globals
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │     HVM      │   栈机：frame / stack / handlers
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │ HNativeBridge│   print/len/push/pop/range/gui_*/regex_*/file_*/fdiv/...
        └──────┬───────┘
               ↓
            stdout
```

打包阶段：`runtime jar + app.hbc 资源 → jpackage --type app-image → .app/.exe/ELF`

### 架构变更说明

| 旧方案（已废弃） | 实际方案（当前） |
|------------------|------------------|
| `.hbc → KotlinCodeGenerator → Kotlin 源码 → kotlinc → JVM 应用` | `.hbc → HbcReader → HVM 栈机 → jpackage → 原生应用` |
| 生成 `Generated.kt` 源码 | 不生成源码，HVM 直接解释执行 JSON 字节码 |
| 使用 Gradle 构建 | 使用 `scripts/build.sh` + kotlinc（无 Gradle）|
| 34 个 opcode 转译 | HVM 实现全部 40+ opcode |

**理由**：H# 是动态类型语言，转译成静态 Kotlin 源码需大量运行时类型擦除，收益有限；栈机方案直接复用 Python VM 已验证的 opcode 语义，风险更低；jpackage 仍能产出真原生应用。

## 关键模块

| 模块 | 文件 | 职责 |
|------|------|------|
| HbcReader | `compiler/HbcReader.kt` | `.hbc` JSON 解析 + `fixForLoopJumps` 字节码自愈 + MiniJson 零依赖解析器 |
| CLI | `compiler/Main.kt` | 命令行入口（info/validate/run/compile/version）|
| HVM | `runtime/HVM.kt` | 栈式虚拟机（frame/stack/handlers，全部 opcode）|
| HValue | `runtime/HValue.kt` | HValue 类型层级（HNull/HBool/HNumber/HString/HList/HDict/HClass/HFunction/HUnion/HChannel/HFuture）|
| HNativeBridge | `runtime/HNativeBridge.kt` | 原生函数绑定（40+ natives：基础/数学/文件/正则/GUI/Channel）|
| HbcRunner | `runtime/HbcRunner.kt` | 模块预加载（非 entry 模块的 STORE_NAME 到 globals）|
| HbcLauncher | `runtime/HbcLauncher.kt` | 应用入口（jpackage 打包后的 main class）|
| WorkerPool | `runtime/WorkerPool.kt` | 多线程工作池（N 个 OS 线程 + work-stealing，用于 @parallel fn）|
| Packager | `platform/Packager.kt` | jpackage 包装器（跨平台打包）|

## .hbc 文件格式

`.hbc` 是**标准 JSON 容器**（非二进制）。详见 [HBC_FORMAT_SPEC.md](file:///Users/peddlejumper/H#/v0.4/.project_context/HBC_FORMAT_SPEC.md)。

```json
{
  "version": "v0.4",
  "modules": {
    "main": {
      "instructions": [
        ["LOAD_CONST", 0],
        ["PRINT", null],
        ["HALT", null]
      ],
      "consts": ["Hello, H#!"]
    }
  },
  "built_at": 1719500000
}
```

- 顶层 = `{version, modules:{name:{instructions,consts}}, built_at}`
- 指令 = `[opname, arg]` 二元组数组（arg 可为 null/int/string/2-tuple）
- 常量池支持：标量、函数对象、类对象、union、tuple

## CLI 命令

| 子命令 | 说明 |
|--------|------|
| `version` | 打印版本（`h# kotlin-compiler 0.1.0`，支持 .hbc v0.4）|
| `info <file.hbc>` | 列出 module / 常量池 / 指令流概览 |
| `validate <file.hbc>` | 校验 JSON 合法性 |
| `run <file.hbc>` | 直接用 HVM 跑（不打包）|
| `compile <file.hbc>` | 打 `.app` / `.exe` / Linux 镜像 |

### `compile` 参数

```
java -jar hsharp-kotlin-compiler.jar compile <file.hbc> \
    -o <out-dir> \
    --name <app-name> \
    --target mac|windows|linux \
    --app-version <v>      # 必须 ≥ 1.0.0（jpackage 限制）
    --type image|dmg|msi|deb|rpm|app|exe  # 默认 image
    --icon <path>          # .icns / .ico / .png
    --entry <module>       # 默认 'main' 或第一个模块
```

## 构建

```bash
cd hsharp-kotlin-compiler

# 构建（首次自动下载 kotlinc jars 到 .kotlin/）
./scripts/build.sh
```

**产物**：
- `build/libs/hsharp-kotlin-compiler.jar` — CLI 工具（fat jar，含 kotlin-stdlib）
- `build/libs/hsharp-runtime.jar` — 运行时（被打进 .app，自包含）

**特点**：
- 无 Gradle、无需预装 Kotlin
- 仅需 JDK 11+
- kotlinc jars 缓存在 `.kotlin/`（kotlin-stdlib 2.0.21, kotlinx-coroutines 1.7.3）
- runtime jar 自包含（kotlin-stdlib 解包进 jar，jpackage 兼容）

## 测试

```bash
cd hsharp-kotlin-compiler

# 35 个 Kotlin 编译器测试
bash scripts/test.sh

# 8 个算法/OO 测试
python3 lib-tests/run_lib_tests.py

# 7 个压力测试
python3 stress-tests/run_tests.py

# 14 个 zzwui 测试（521 cases）
python3 zzwui-tests/run_zzwui_tests.py
```

**当前状态**: 全部 821+ 用例通过。

## 支持的 H# 子集

### 已实现

- 字面量、变量、算术、位运算、比较
- list / dict 字面量与索引
- 函数定义与调用、lambda、闭包
- 类（继承、private 字段、static 方法、super()）
- 泛型（`<T>` 语法，class/function/type_args）
- Union 类型
- for-in 循环（HList / HString / HDict，含 k,v 解包）
- while 循环（含 break）
- try / catch
- 模块与导入
- async/await（`async fn` + `await expr`，基于 HFuture）
- 多线程并行（`@parallel fn` / `parallel fn` + WorkerPool）
- Channel（`chan T` / `chan T(n)` + chan_send/recv/close）
- 结构化并发（`concurrent { ... }` 块）
- 模式匹配（`match expr { pat => body, ... }`，7 种模式）
- 错误传播（`expr?` 后缀，Rust 风格）
- 解构赋值（`let [a, b, _] = expr;`，列表/元组解构，`_` 跳过槽位）
- 默认参数（`fn f(a, b=1, c=2)`，字面量默认值，尾部对齐）
- 变长参数（`fn f(...args)` / `fn f(a, b, ...rest)`，尾参收集为 HList）
- 字符串格式化（`fmt("{0} + {1}", a, b)` native 函数）

### 未完整实现

- 完整的协程调度（`coro fn` 保留为低层 API，`async fn` 是单线程 eagerly resolved 糖）
- 异步 I/O（await 当前是同步 unwrap）
- 一些边缘 host function

## 字节码自愈

Python 编译器 `compiler.py:321` 发出的 for-loop `JUMP` 指令跳到循环体起始（P+1）而非 `FOR_ITER`（P），会导致无限循环。Kotlin `HbcReader.fixForLoopJumps()` 自动检测并修正：

```kotlin
private fun fixForLoopJumps(instrs: List<Pair<String, Any?>>): List<Pair<String, Any?>> {
    val out = ArrayList<Pair<String, Any?>>(instrs.size)
    for (i in instrs.indices) {
        val (op, arg) = instrs[i]
        if (op == "JUMP" && arg is Number) {
            val target = arg.toInt()
            if (target in 1 until instrs.size && instrs[target - 1].first == "FOR_ITER") {
                out.add(op to (target - 1))
                continue
            }
        }
        out.add(op to arg)
    }
    return out
}
```

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `no kotlinc available` | 第一次跑没拉 jars | 让 `build.sh` 自己下 |
| `jpackage: invalid app-version "0.x.x"` | jpackage 不接受 0.x | 用 `--app-version 1.0.0` |
| `NoClassDefFoundError: kotlin/jvm/internal/Intrinsics` | jpackage 不认 Class-Path | 跑 `build.sh` 重新 repackage stdlib |
| for-loop 卡住 / 输出永远是第一个元素 | Python 编译器 for-loop JUMP bug | `HbcReader.fixForLoopJumps` 会自动修；如果是新加的模块格式，重新 build |
| `3.0 / 5.0` 结果是 `0` | HVM 的 `BINARY_DIV` 用 floor 除法 | 用 `fdiv(a, b)` native 做真除法 |

## 文档

- `.project_context/HBC_FORMAT_SPEC.md` — .hbc 格式规范（权威）
- `.project_context/PROJECT_CONTEXT.md` — 项目总览
- `hsharp-kotlin-compiler/README.md` — 编译器使用说明（架构权威）
- `H#_v0.4.1_Package/CHANGELOG/CHANGELOG.md` — 完整变更日志

---

**最后更新**: 2026-07-03
