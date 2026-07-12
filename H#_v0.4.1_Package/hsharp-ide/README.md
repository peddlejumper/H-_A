# H# IDE — 初始骨架

这是一个为 H#（H Sharp）语言构建的 IDE 原型工程。目标是用 C#（跨平台）实现一个强大的桌面 IDE，分阶段迭代：先实现编辑/编译/运行/REPL/调试与版本控制集成。

当前目录结构（初始）：

- `src/IDE.Tools`：辅助控制台工具，用于通过子进程调用现有的 `hsharp.py`（快速集成）。

先决条件
- 安装 .NET 7+ SDK（macOS / Windows）
- 安装 Python 3（用于运行仓库中的 `hsharp.py`）

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
- 添加 `IDE.UI`（Avalonia）实现编辑器界面
- 添加 `IDE.Lsp`（Language Server）用于代码补全、跳转、诊断
- 添加调试适配（DAP）项目，与现有 VM/bytecode 集成
- 集成 Git（版本控制）与项目模板

下一个动作：实现 `IDE.UI` 模板并把 `IDE.Tools` 与 UI 集成以便从 GUI 调用构建/运行。

运行 IDE.UI（示例）

```bash
dotnet run --project src/IDE.UI
```

在 GUI 中可以：
- 打开/保存文件
- 使用右上工具栏的 `Run` / `Build` / `Run BC` / `REPL` 按钮调用已编译的 `IDE.Tools`（如果存在）或回退到直接调用 `hsharp.py`。

注意：要让 `IDE.Tools` 被 UI 发现，请先在仓库根目录运行 `dotnet build src/IDE.Tools`，或直接将 `hsharp.py` 放在仓库根目录供 UI 直接调用。
