# H# Kotlin 编译器集成指南

## 概述

H# Kotlin 编译器是一个独立的工具，用于将 H# Python VM 生成的 .hbc 字节码文件编译为跨平台的原生应用程序。

## 工作流程

### 开发阶段（Python VM）

开发者继续使用现有的 H# Python VM 进行开发：

```bash
# 编写 H# 源代码
vim myapp.hto

# 使用 Python VM 编译为字节码
python3 hsharp.py --emit-bc myapp.hto
# 生成: myapp.hbc

# 使用 Python VM 测试运行
python3 hsharp.py --run-bc myapp.hbc
```

### 发布阶段（Kotlin 编译器）

当需要发布独立应用时，使用 Kotlin 编译器：

```bash
# 验证字节码
cd hsharp-kotlin-compiler
./gradlew run --args="validate --hbc ../myapp.hbc"

# 编译为原生应用
./gradlew run --args="compile --hbc ../myapp.hbc --output release --platform mac"

# 输出结构
release/
├── Generated.kt           # 生成的 Kotlin 源代码
├── myapp.app/            # macOS 应用包
│   └── Contents/MacOS/   # 可执行文件
└── myapp.exe             # Windows 可执行文件
```

## 架构设计

### 第一阶段：字节码加载和验证
- JSON 格式的 .hbc 文件加载
- 字节码合法性验证
- 错误报告

### 第二阶段：中间代码生成
- 34 个操作码 → Kotlin 代码转换
- 运行时值系统（HValue）
- 环境和作用域管理
- 生成可执行的 Kotlin 源代码

### 第三阶段：高级特性
- 函数定义和调用
- 对象系统（类、属性、方法）
- 异常处理（try/catch）
- 循环和条件分支

### 第四阶段：优化
- 死代码消除
- 常量折叠
- 栈操作优化

### 第五阶段：平台打包
- GraalVM Native Image 编译
- macOS .app 包生成
- Windows .exe 包装
- Linux 二进制生成

## 编译器入口点

```bash
# 项目位置
/Users/peddlejumper/hsharp-kotlin-compiler/

# 快速命令（来自项目目录）
./gradlew run --args="compile --hbc <file.hbc> --output <dir>"
./gradlew run --args="validate --hbc <file.hbc>"
./gradlew run --args="info --hbc <file.hbc>"
```

## 关键模块

| 模块 | 职责 |
|------|------|
| `BytecodeLoader` | 加载和解析 JSON .hbc 文件 |
| `BytecodeValidator` | 验证字节码合法性 |
| `KotlinCodeGenerator` | 生成 Kotlin 源代码 |
| `InstructionTranslator` | 转换个别指令 |
| `HValue` | H# 运行时值类型系统 |
| `Environment` | 变量和函数作用域 |

## 生成的代码示例

输入：`program.hbc` (H# 字节码)
```json
{
  "version": "v0.4",
  "modules": {
    "main": {
      "instructions": [
        {"opcode": "LOAD_CONST", "args": [0]},
        {"opcode": "PRINT", "args": []},
        {"opcode": "HALT", "args": []}
      ],
      "consts": ["Hello, H#!"]
    }
  }
}
```

输出：`Generated.kt`
```kotlin
import com.hsharp.runtime.*

fun main() {
    val stack = mutableListOf<HValue>()
    val consts = arrayOf(
        HValue.String("Hello, H#!")
    )
    val env = Environment()
    
    // [0] LOAD_CONST
    stack.add(consts[0])
    
    // [1] PRINT
    val print_val = stack.removeLast()
    println(print_val)
    
    // [2] HALT
    return
}
```

## 测试 .hbc 文件

项目中包含一个测试文件：

```bash
cd hsharp-kotlin-compiler

# 查看信息
./gradlew run --args="info --hbc test_simple.hbc"

# 编译
./gradlew run --args="compile --hbc test_simple.hbc --output out"

# 查看生成的代码
cat out/Generated.kt
```

## 与现有项目的关系

1. **独立构建**
   - Kotlin 编译器是独立的 Gradle 项目
   - 不修改 Python VM 代码
   - 利用现有的 .hbc 文件格式

2. **共享输出**
   - Python VM 生成 .hbc 文件
   - Kotlin 编译器消费 .hbc 文件
   - 生成独立的可执行应用

3. **工具链集成**
   - 开发时：使用 Python VM
   - 发布时：使用 Kotlin 编译器
   - 最终交付：原生应用

## 下一步工作

### 立即（第 1-2 周）
- ✓ 项目框架和基础设置
- ✓ 字节码加载和验证
- ✓ 基本指令转换
- ⏳ 增强代码生成

### 短期（第 3-4 周）
- 高级特性支持（函数、类、异常）
- 控制流优化
- 更多测试用例

### 中期（第 5-6 周）
- 代码优化传递
- GraalVM Native Image 集成
- 平台特定打包

### 长期
- 性能基准测试
- 文档完善
- 开源发布

## 文档

- `hsharp-kotlin-compiler/README.md` - 编译器使用指南
- `.../PLAN.md` - 完整的实现计划

## 联系

如有问题，参考计划文件或项目 README。
