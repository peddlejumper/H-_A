# H# Bootstrap Modules - Self-Hosting Progress

> **最后更新**: 2026-07-03
> **当前版本**: H# v0.4.1 (2026-06-20)
> **主运行时**: Kotlin HVM 栈机解释器（位于 `hsharp-kotlin-compiler/`），不再使用 Python VM 作为主运行时

This directory contains H# modules written in H# itself, demonstrating the language's self-hosting capabilities.

## Overview

The bootstrap modules represent a significant milestone in H#'s development toward self-sufficiency. These modules are written entirely in H# and can be parsed and executed by the H# interpreter.

> **注（v0.4.1 更新）**：本目录下 `.hto` 模块由 Python 编译器（`hsharp.py` / `build_bundle.py`）编译为 `.hbc` 字节码容器，最终由 **Kotlin HVM 栈机解释器** 加载并运行。`.hbc` 是 **JSON 容器格式**（非二进制），顶层结构为 `{version, modules:{name:{instructions,consts}}, built_at}`。下方第 1–8 节描述的原始 8 个模块的函数清单与用法说明仍然准确；目录实际内容已扩展至 **50+ 个 `.hto` 文件**，新增模块类别见下方"扩展模块清单（v0.4.1）"。

## Module Structure

### 扩展模块清单（v0.4.1）

下方第 1–8 节描述的是最初的 8 个核心 bootstrap 模块。v0.4.0 → v0.4.1 期间目录已大幅扩展，新增的 `.hto` 模块按类别归类如下（函数级清单请直接查阅对应 `.hto` 文件头部注释）：

**3D / D3 情感系统**
- `d3system.hto` / `d3system_ops.hto` / `d3system_demo.hto` — D3 情感系统核心与运算
- `d3_emotion.hto` — 情感建模
- `3d_advanced.hto` — 高级 3D 场景

**标准库扩展模块**
- `crypto_module.hto` — 加密 / 哈希（对应 v0.4.1 标准库 `crypto`）
- `datetime_module.hto` — 日期时间
- `db_module.hto` — 数据库访问
- `fs_module.hto` — 文件系统
- `net_module.hto` — 网络访问
- `io_module.hto` — I/O 抽象
- `json_serializer.hto` — JSON 序列化
- `math_advanced.hto` / `math_extended.hto` — 数学扩展
- `pkg_inspect.hto` — 包检查

**UI 渲染层（zzw / hwdui）**
- `zzw_render.hto` / `zzw_native.hto` / `zzw_demo_window.hto` / `zzw_ui_run.hto` — zzw UI 渲染与原生桥
- `dzzw.hto`（含 `dzzw.c` / `dzzw.h` C 绑定）
- `hwdui.hto` — HWDUI 核心
- `hwdui_java.hto` / `hwdui_cpp.hto` / `hwdui_dotnet.hto` — 多语言 UI 绑定（Java / C++ / .NET）

**类型系统扩展**
- `hsharpmyl.hto` — H# Myl 核心
- `hsharpmyl_v3_ext.hto` — v3 类型扩展
- `hsharpmyl_v4_types.hto` — v4 类型系统（含 union / 泛型支持）

**编译器 / 自举链**
- `bootstrap.hto` / `compiler.hto` / `executor.hto` / `interpreter.hto` / `parser.hto` / `tokenize.hto` — 自举工具链
- `hsharp_selfhost.hto` / `hsharp_builder.hto` / `selfhost_test.hto` / `selftest.hto` — 自宿主测试
- `demo_bootstrap.hto` / `demo_executor.hto` — 演示

**测试文件（`test_*.hto`，共 30+ 个）**
- 涵盖：3D、AST、bootstrap 全链、编译器链、crypto、D3、dzzw、hsharpmyl、hwdui（含 java/cpp/dotnet）、interp 链、math 扩展、嵌套闭包、net、parser 链、standard libs、ternary、tokenize、union、zzwui D3 性能等。

---

### 1. Performance Optimization (`env_optimized.hto`)

**Purpose**: Optimized environment management using hash-based lookups instead of linear search.

**Key Functions**:
- `_create_env()` - Create a new environment with O(1) lookup
- `_env_get(env, name)` - Fast variable retrieval
- `_env_set(env, name, val)` - Fast variable assignment
- `_env_has(env, name)` - Check if variable exists
- `_env_merge(parent_env, child_env)` - Merge environments for closures
- `_env_keys(env)` - Get all variable names
- `_env_to_list(env)` - Convert to list format

**Performance Improvement**: Variable access improved from O(n) to O(1) average case.

---

### 2. Performance Monitoring (`perf_monitor.hto`)

**Purpose**: Runtime performance profiling and benchmarking tools.

**Key Functions**:
- `perf_start_timer(name)` - Start a named timer
- `perf_stop_timer(name)` - Stop timer and get elapsed time
- `perf_elapsed(name)` - Get current elapsed time without stopping
- `perf_increment_counter(name, amount)` - Increment performance counter
- `perf_get_counter(name)` - Get counter value
- `perf_report()` - Print comprehensive performance report
- `perf_benchmark(fn_to_test, iterations)` - Benchmark a function

**Usage Example**:
```h#
perf_start_timer("my_operation");
# ... code to measure ...
let elapsed = perf_stop_timer("my_operation");
print("Operation took: " + str(elapsed) + " ms");
```

---

### 3. String Utilities (`string_utils.hto`)

**Purpose**: Comprehensive string manipulation library.

**Key Functions**:

**Basic Operations**:
- `str_length(s)` - Get string length
- `str_char_at(s, index)` - Get character at position
- `str_substring(s, start, length)` - Extract substring
- `str_to_array(s)` / `str_from_array(arr)` - Convert between string and char array

**Case Conversion**:
- `str_uppercase(s)` - Convert to uppercase
- `str_lowercase(s)` - Convert to lowercase

**Trimming**:
- `str_trim(s)` - Remove leading and trailing whitespace
- `str_trim_left(s)` - Remove leading whitespace
- `str_trim_right(s)` - Remove trailing whitespace

**Search & Find**:
- `str_contains(s, substr)` - Check if contains substring
- `str_index_of(s, substr)` - Find first occurrence
- `str_last_index_of(s, substr)` - Find last occurrence
- `str_starts_with(s, prefix)` - Check prefix
- `str_ends_with(s, suffix)` - Check suffix

**Modification**:
- `str_replace(s, old, new)` - Replace all occurrences
- `str_split(s, delimiter)` - Split into array
- `str_join(arr, separator)` - Join array into string
- `str_repeat(s, count)` - Repeat string n times
- `str_reverse(s)` - Reverse string

**Padding**:
- `str_pad_left(s, length, pad_char)` - Left-pad string
- `str_pad_right(s, length, pad_char)` - Right-pad string

---

### 4. Array Utilities (`array_utils.hto`)

**Purpose**: Functional programming-style array operations.

**Higher-Order Functions**:
- `arr_map(arr, fn)` - Transform each element
- `arr_filter(arr, predicate)` - Filter elements
- `arr_reduce(arr, reducer, initial_value)` - Reduce to single value
- `arr_for_each(arr, fn)` - Execute function for each element

**Search & Find**:
- `arr_find(arr, predicate)` - Find first matching element
- `arr_find_index(arr, predicate)` - Find index of first match
- `arr_includes(arr, value)` - Check if value exists
- `arr_index_of(arr, value)` - Find index of value
- `arr_last_index_of(arr, value)` - Find last index of value

**Predicate Tests**:
- `arr_every(arr, predicate)` - Check if all match
- `arr_some(arr, predicate)` - Check if any match

**Array Manipulation**:
- `arr_slice(arr, start, end)` - Extract portion
- `arr_splice(arr, start, delete_count, items)` - Remove/insert elements
- `arr_concat(arr1, arr2)` - Concatenate arrays
- `arr_flatten(arr, depth)` - Flatten nested arrays
- `arr_reverse(arr)` - Reverse in place
- `arr_unique(arr)` - Remove duplicates
- `arr_chunk(arr, size)` - Split into chunks
- `arr_zip(arrays)` - Zip multiple arrays

**Sorting & Statistics**:
- `arr_sort(arr, comparator)` - Sort array
- `arr_min(arr)` - Find minimum
- `arr_max(arr)` - Find maximum
- `arr_sum(arr)` - Calculate sum
- `arr_average(arr)` - Calculate average

**Utility**:
- `arr_range(start, end, step)` - Generate number range
- `arr_fill(arr, value, start, end)` - Fill with value
- `is_array(value)` - Check if value is array

---

### 5. Math Utilities (`math_utils.hto`)

**Purpose**: Mathematical functions and constants.

**Constants**:
- `MATH_PI` - π (3.14159...)
- `MATH_E` - e (2.71828...)
- `MATH_SQRT2` - √2
- `MATH_SQRT1_2` - 1/√2
- `MATH_LN2` - ln(2)
- `MATH_LN10` - ln(10)
- `MATH_LOG2E` - log₂(e)
- `MATH_LOG10E` - log₁₀(e)

**Basic Functions**:
- `math_abs(x)` - Absolute value
- `math_min(a, b)` / `math_max(a, b)` - Min/max of two numbers
- `math_clamp(value, min_val, max_val)` - Clamp to range
- `math_sign(x)` - Sign (-1, 0, or 1)

**Rounding**:
- `math_floor(x)` - Round down
- `math_ceil(x)` - Round up
- `math_round(x)` - Round to nearest
- `math_trunc(x)` - Truncate decimal

**Powers & Roots**:
- `math_pow(base, exponent)` - Power function
- `math_sqrt(x)` - Square root (Newton's method)
- `math_cbrt(x)` - Cube root (Newton's method)

**Number Theory**:
- `math_factorial(n)` - Factorial
- `math_gcd(a, b)` - Greatest common divisor
- `math_lcm(a, b)` - Least common multiple
- `math_is_prime(n)` - Primality test
- `math_primes_up_to(limit)` - Sieve of Eratosthenes

**Sequences**:
- `math_fibonacci(n)` - Nth Fibonacci number
- `math_fibonacci_sequence(n)` - First n Fibonacci numbers

**Statistics**:
- `math_average(numbers)` - Mean
- `math_median(numbers)` - Median
- `math_mode(numbers)` - Mode
- `math_variance(numbers)` - Variance
- `math_std_dev(numbers)` - Standard deviation

**Trigonometry Helpers**:
- `math_degrees_to_radians(degrees)` - Convert degrees to radians
- `math_radians_to_degrees(radians)` - Convert radians to degrees

**Geometry**:
- `math_distance(x1, y1, x2, y2)` - Distance between two points

**Random** (requires host support):
- `math_random_int(min_val, max_val)` - Random integer
- `math_random_float()` - Random float [0, 1)

---

### 6. Code Formatter (`formatter.hto`)

**Purpose**: Automatic code formatting for consistent style.

**Key Functions**:
- `format_code(source)` - Format H# source code
- `format_file(filepath)` - Format file content
- `format_and_save(filepath)` - Format and overwrite file
- `format_tokens(tokens)` - Format token stream
- `make_indent(level)` - Generate indentation string

**Formatting Rules**:
- Consistent indentation (4 spaces or tabs)
- Proper brace placement
- Spacing around operators
- Line breaks after statements
- Comment preservation

**Configuration**:
- `FORMAT_INDENT_SIZE` - Indentation width (default: 4)
- `FORMAT_USE_TABS` - Use tabs instead of spaces (default: false)

---

### 7. Static Analyzer/Linter (`linter.hto`)

**Purpose**: Static code analysis to find potential issues.

**Key Functions**:
- `lint_analyze(source)` - Analyze code and return results
- `lint_file(filepath)` - Lint a file
- `lint_report()` - Print lint report
- `lint_check_syntax(tokens)` - Syntax validation
- `lint_check_style(source)` - Style checking
- `lint_add_error(message)` - Register error
- `lint_add_warning(message)` - Register warning

**Checks Performed**:

**Syntax Checks**:
- Balanced braces `{}`
- Balanced parentheses `()`
- Balanced brackets `[]`

**Style Checks**:
- Line length (>120 characters warning)
- Trailing whitespace detection
- Tab vs spaces usage
- Empty line conventions

**Future Enhancements** (placeholders):
- Unused variable detection
- Undefined variable detection
- Type consistency checks
- Function call arity validation

**Output Format**:
```
=== H# Lint Report ===

ERRORS (2):
  ✗ Unmatched opening brace(s): 1
  ✗ Line 5 exceeds 120 characters (145 chars)

WARNINGS (1):
  ⚠ Line 3 has trailing whitespace

Summary: 2 errors, 1 warnings
=====================
```

---

### 8. Comprehensive Test Suite (`comprehensive_test.hto`)

**Purpose**: Validate all bootstrap modules work correctly.

**Test Coverage**:
1. Environment optimization (get/set operations)
2. String utilities (all major functions)
3. Array utilities (map, filter, reduce, statistics)
4. Math utilities (constants, functions, algorithms)
5. Performance monitoring (timers, counters)
6. Code formatting (basic formatting)
7. Static analysis (linting)
8. Integration tests (full pipeline)
9. Edge cases (empty inputs, boundary values)
10. Error handling (division, array access)

**Running Tests**:
```bash
python hsharp.py bootstrap/comprehensive_test.hto
```

---

## Integration with Host System

These bootstrap modules are designed to work with the Python-based H# compiler while progressively reducing dependency on Python builtins.

> **v0.4.1 注**：Python 端目前主要承担**编译**角色（`.hto` → `.hbc`），**运行时**已迁移至 Kotlin HVM 栈机解释器。下方"Required Host Functions"清单描述的是 Python 编译/解释路径所需的主机函数；在 Kotlin HVM 路径下，等价能力由 HVM 内置指令与标准库模块（`assert` / `path` / `regex` / `crypto` 等）提供。

### Required Host Functions

Some functions require host system support:
- `read_file(path)` - File reading
- `write_file(path, content)` - File writing
- `time_now()` - Current timestamp
- `substring(s, start, length)` - String slicing
- `ord(ch)` / `chr(code)` - Character code conversion
- `int(x)` / `str(x)` - Type conversion

These are currently provided by the Python interpreter but should be implemented in H# as the language matures.

---

## Self-Hosting Architecture

```
┌─────────────────────────────────────┐
│   Python 编译器 (hsharp.py)          │  ← 编译路径（.hto → .hbc）
└──────────────┬──────────────────────┘
               │ compiles to .hbc (JSON container)
               ↓
┌─────────────────────────────────────┐
│   Kotlin HVM 栈机解释器              │  ← 主运行时 (v0.4.1, hsharp-kotlin-compiler/)
│   加载 .hbc 并执行                   │
└──────────────┬──────────────────────┘
               │ loads & executes
               ↓
┌─────────────────────────────────────┐
│   H# Bootstrap Modules (.hto)       │  ← Self-hosted components (50+ files)
│   ├─ tokenizer.hto                  │
│   ├─ parser.hto                     │
│   ├─ interpreter.hto                │
│   ├─ env_optimized.hto              │
│   ├─ string_utils.hto               │
│   ├─ array_utils.hto                │
│   ├─ math_utils.hto                 │
│   ├─ formatter.hto                  │
│   ├─ linter.hto                     │
│   ├─ d3system.hto / d3system_ops.hto│
│   ├─ crypto_module.hto              │
│   ├─ datetime_module.hto            │
│   ├─ db_module.hto / fs_module.hto  │
│   ├─ net_module.hto / io_module.hto │
│   ├─ zzw_render.hto / zzw_native.hto│
│   ├─ hwdui_{java,cpp,dotnet}.hto    │
│   ├─ hsharpmyl{,_v3_ext,_v4_types}.hto │
│   └─ ... (test_*.hto, 等)            │
└─────────────────────────────────────┘
```

---

## Future Development Roadmap

> **v0.4.1 注**：以下路线图中标注为 ✅ 的条目已在 **Kotlin HVM 端**（`hsharp-kotlin-compiler/`）实现，**不在 Python 自举端**。bootstrap/ 目录的 `.hto` 自举模块尚未全部同步这些特性，自举端仍以原 8 个核心模块为主。

### Phase 1: Complete Self-Hosting ✅ (Current)
- [x] Tokenizer in H#
- [x] Parser in H#
- [x] Interpreter in H#
- [x] Standard libraries in H#

### Phase 2: Tool Chain (In Progress)
- [x] Code formatter
- [x] Static analyzer
- [ ] Debugger
- [ ] Package manager
- [ ] Build system

### Phase 3: Performance
- [ ] Bytecode compiler in H#
- [x] VM optimizations  ✅ (Kotlin HVM 栈机，v0.4.1 主运行时)
- [ ] JIT compilation support
- [ ] Native code generation

### Phase 4: Advanced Features
- [ ] Full type system
- [x] Generics `<T>`  ✅ (v0.4.1 已实现，Kotlin HVM 端)
- [x] Pattern matching (`match`)  ✅ (v0.4.1 已实现，Kotlin HVM 端)
- [x] Async/await  ✅ (v0.4.1 已实现，Kotlin HVM 端)
- [x] 多线程并行（`@parallel fn` / `parallel fn` + WorkerPool） ✅ (v0.4.1)
- [x] Channel（`chan T`）与结构化并发（`concurrent{}`） ✅ (v0.4.1)
- [x] `?` 错误传播 ✅ (v0.4.1)
- [x] 标准库模块：`assert` / `path` / `regex` / `crypto`（共 4 个） ✅ (v0.4.1)
- [x] raytracer pipeline ✅ (v0.4.1)
- [ ] Macro system

---

## Usage Examples

### Using String Utilities
```h#
import string_utils;

let text = "  Hello, World!  ";
let clean = str_trim(text);
let upper = str_uppercase(clean);
print(upper);  # "HELLO, WORLD!"
```

### Using Array Utilities
```h#
import array_utils;

let numbers = [1, 2, 3, 4, 5];
let doubled = arr_map(numbers, fn(x) { return x * 2; });
let evens = arr_filter(doubled, fn(x) { return x % 2 == 0; });
let sum = arr_sum(evens);
print(sum);  # 30
```

### Using Math Utilities
```h#
import math_utils;

let radius = 5;
let area = MATH_PI * math_pow(radius, 2);
print("Circle area: " + str(area));

if (math_is_prime(17)) {
    print("17 is prime!");
}
```

### Using Performance Monitor
```h#
import perf_monitor;

perf_start_timer("computation");
let result = some_expensive_function();
let elapsed = perf_stop_timer("computation");
print(" Took " + str(elapsed) + "ms");
```

### Using Formatter
```h#
import formatter;

let messy_code = "let x=10;fn f(a){return a+1;}";
let clean_code = format_code(messy_code);
print(clean_code);
```

### Using Linter
```h#
import linter;

let result = lint_file("my_program.hto");
lint_report();
```

---

## Contributing

When adding new bootstrap modules:
1. Write the module entirely in H#
2. Include comprehensive documentation
3. Add tests to `comprehensive_test.hto`
4. Ensure compatibility with existing modules
5. Update this README

---

## License

Part of the H# Language Project
