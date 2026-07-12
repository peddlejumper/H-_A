# H# IDE — 初始骨架

> **最后更新**: 2026-07-03
> **当前版本**: H# v0.4.1 (2026-06-20) / VS Code 扩展 0.4.1
> **主运行时**: Kotlin HVM 栈机解释器（位于 `hsharp-kotlin-compiler/`），同时保留 Python `hsharp.py` 路径作为回退

这是一个为 H#（H Sharp）语言构建的 IDE 原型工程。目标是用 C#（跨平台）实现一个强大的桌面 IDE，分阶段迭代：先实现编辑/编译/运行/REPL/调试与版本控制集成。

> **v0.4.1 更新**：本节标题保留"初始骨架"作为历史描述。实际上 `src/IDE.UI/` 已从最初的 Avalonia 模板扩展为包含启动器、主窗口、3D 查看器、环境检查等功能的完整 UI 工程（详见下方"IDE.UI 当前结构"）。运行时方面，IDE 现在支持**双运行时**：既可调用 `hsharp.py`，也可通过 **Kotlin HVM** 运行 `.hbc`（JSON 容器格式，顶层结构 `{version, modules:{name:{instructions,consts}}, built_at}`）。

当前目录结构（初始）：

- `src/IDE.Tools`：辅助控制台工具，用于通过子进程调用现有的 `hsharp.py`（快速集成）。

### IDE.UI 当前结构（v0.4.1）

`src/IDE.UI/` 已从初始 Avalonia 模板扩展，当前包含以下源文件：

- `App.axaml` / `App.axaml.cs` — Avalonia 应用入口与样式
- `Program.cs` — `Main` 入口，启动 Avalonia 应用
- `MainWindow.axaml` / `MainWindow.axaml.cs` — 主编辑器窗口（打开/保存文件、Run/Build/Run BC/REPL 工具栏）
- `LauncherWindow.axaml` / `LauncherWindow.axaml.cs` — 启动器窗口（项目/示例选择入口）
- `LauncherConfig.cs` — 启动器配置模型
- `D3ViewerWindow.cs` — 3D / D3 查看器窗口（用于查看 D3 情感系统与 3D 场景输出）
- `EnvironmentChecker.cs` — 环境检查（检测 .NET / Python / Kotlin HVM / `hsharp.py` 是否可用）
- `IDE.UI.csproj` — 工程文件（Avalonia + Skia/HarfBuzz，目标框架 net6.0/net7.0）

> 双运行时支持：UI 中的 `Run` / `Build` / `Run BC` 按钮优先调用已编译的 `IDE.Tools`（若存在），否则回退到直接调用 `hsharp.py`；`Run BC` 路径下 `.hbc` 可由 **Kotlin HVM** 执行（推荐）或由 Python 端执行。

先决条件
- 安装 .NET 7+ SDK（macOS / Windows）
- 安装 Python 3（用于运行仓库中的 `hsharp.py`，编译 `.hto` → `.hbc`）
- （可选，推荐）Kotlin HVM 运行时（位于 `hsharp-kotlin-compiler/`，用于以栈机执行 `.hbc`）

快速开始

1. 在仓库根目录（包含 `hsharp.py`）下运行：

```bash
cd hsharp-ide
dotnet build src/IDE.Tools
dotnet run --project src/IDE.Tools -- run ../example.hto
```

2. 常用命令（`IDE.Tools`）：
- `repl` — 启动 H# 的交互式 REPL（通过 `hsharp.py`）
- `run <file.hto>` — 直接使用 H# 解释器运行源文件
- `emit-bc <file.hto>` — 生成字节码文件 `file.hbc`
- `run-bc <file.hbc>` — 运行字节码

扩展路线图
- [x] 添加 `IDE.UI`（Avalonia）实现编辑器界面 ✅ (已实现，见上方"IDE.UI 当前结构")
- [x] 把 `IDE.Tools` 与 UI 集成以便从 GUI 调用构建/运行 ✅
- [x] 双运行时支持：`hsharp.py` + Kotlin HVM（运行 `.hbc`） ✅ (v0.4.1)
- [ ] 添加 `IDE.Lsp`（Language Server）用于代码补全、跳转、诊断
- [ ] 添加调试适配（DAP）项目，与现有 VM/bytecode 集成
- [ ] 集成 Git（版本控制）与项目模板

下一个动作：实现 `IDE.Lsp` 语言服务器以支持代码补全 / 跳转 / 诊断，并与 Kotlin HVM 调试适配（DAP）集成。

运行 IDE.UI（示例）

```bash
dotnet run --project src/IDE.UI
```

在 GUI 中可以：
- 打开/保存文件
- 使用右上工具栏的 `Run` / `Build` / `Run BC` / `REPL` 按钮调用已编译的 `IDE.Tools`（如果存在）或回退到直接调用 `hsharp.py`。

注意：要让 `IDE.Tools` 被 UI 发现，请先在仓库根目录运行 `dotnet build src/IDE.Tools`，或直接将 `hsharp.py` 放在仓库根目录供 UI 直接调用。
