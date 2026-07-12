# H# v0.4 — Self-Contained Distribution Package

## 快速开始

```bash
# 运行 H# 解释器
python3 interpreter.py program.hto

# 运行 bootstrap 自举编译器
python3 interpreter.py bootstrap/hsharp_selfhost.hto program.hto

# 构建完整 bundle
python3 bootstrap/build_bundle.py

# 运行测试
python3 interpreter.py bootstrap/test_union.hto
python3 interpreter.py bootstrap/test_hwdui_cpp.hto
```

## 目录结构

```
HSharp_v0.4_Package/
├── *.py                  # H# 编译器、解释器、词法/语法分析器 (核心)
├── *.c, *.h, hsvm        # C VM 实现 (hsvm.c, dzzw.c)
├── *.hto                 # H# 示例程序
├── benchmark.py          # 性能基准测试
├── QUICK_REFERENCE.md    # 快速参考
├── benchmarks/           # 跨语言基准对比 (H#, C, C++, Python, JS, TS, Java)
├── docs/
│   └── HSharp-Guide.md   # 详细指南
└── bootstrap/            # 自举编译器与标准库
    ├── *.hto             # H# 标准库源码
    ├── *.py              # 构建脚本
    ├── *.hbc             # 预编译字节码
    └── hsvm, hsharp-vm   # C 编译的 VM 二进制
```

## 核心组件

| 文件 | 作用 |
|------|------|
| lexer.py | 词法分析器 |
| parser.py | 语法分析器 (含 union 类型) |
| ast.py | AST 节点定义 |
| tokens.py | Token 类型 |
| bytecode.py | 字节码定义 |
| compiler.py | 字节码编译器 |
| compiler_optimizations.py | 编译优化 (寄存器分配) |
| register_allocation.py | 寄存器分配器 |
| enhanced_compiler.py | 增强编译器 |
| interpreter.py | 字节码解释器 |
| type_system.py | 类型系统 |
| host_functions.py | 宿主函数 |
| hsvm.c | C VM (B 模式) |
| dzzw.c, dzzw.h | dzzw 渲染引擎 |

## 标准库 (bootstrap/*.hto)

- **hwdui.hto** — zzwUI 基础库
- **hwdui_dotnet.hto** — H# ↔ .NET 协同开发库 (48 类)
- **hwdui_java.hto** — H# ↔ Java 协同开发库 (48 类)
- **hwdui_cpp.hto** — H# ↔ C++ 协同开发库 (48 类)
- **hsharpmyl.hto** — H#ML 机器学习库
- **hsharpmyl_v4_types.hto** — 200 高级 ML 类型
- **union** — 联合类型支持
