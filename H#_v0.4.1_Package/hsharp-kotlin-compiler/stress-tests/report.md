# H# v0.4 — High-Intensity Stress Test Report

**Generated:** 2026-06-19 20:21:58  
**Total wall time:** 3.634 s  
**Python compiler:** `HSharp_v0.4_Tests/compile_test.py`  
**Kotlin runtime:** `hsharp-kotlin-compiler.jar` (HbcRunner)  

## 1. Executive Summary

| Metric | Value |
| --- | --- |
| Total tests | **30** |
| Passed (compile + run) | **30** |
| Failed at compile | 0 |
| Failed at runtime | 0 |
| Timed out (> 60s) | 0 |
| Pass rate | **100.0%** |
| Avg compile time |    42.2 ms |
| Avg run time (Kotlin VM) |    78.5 ms |

## 2. Per-Category Results

| Category | Tests | Passed | Failed | Pass rate |
| --- | ---: | ---: | ---: | ---: |
| `algorithms` | 3 | 3 | 0 | 100% |
| `basics` | 5 | 5 | 0 | 100% |
| `collections` | 2 | 2 | 0 | 100% |
| `control` | 4 | 4 | 0 | 100% |
| `errors` | 1 | 1 | 0 | 100% |
| `functional` | 2 | 2 | 0 | 100% |
| `functions` | 1 | 1 | 0 | 100% |
| `logic` | 2 | 2 | 0 | 100% |
| `oop` | 7 | 7 | 0 | 100% |
| `perf` | 2 | 2 | 0 | 100% |
| `stress` | 1 | 1 | 0 | 100% |

## 3. Per-Test Detail

| # | Test | Cat | Compile | Run | Exit | Time | Status |
| ---: | --- | --- | ---: | ---: | ---: | ---: | :---: |
| 1 | `01_literals` | `basics` |    42.4 ms |    57.7 ms | 0 |   100.1 ms | **OK** |
| 2 | `02_arith` | `basics` |    41.6 ms |    53.1 ms | 0 |    94.7 ms | **OK** |
| 3 | `03_strings` | `basics` |    41.7 ms |    80.6 ms | 0 |   122.3 ms | **OK** |
| 4 | `04_lists` | `collections` |    42.0 ms |    81.9 ms | 0 |   123.9 ms | **OK** |
| 5 | `05_dicts` | `collections` |    41.7 ms |    79.5 ms | 0 |   121.2 ms | **OK** |
| 6 | `06_functions` | `functions` |    42.0 ms |    94.4 ms | 0 |   136.4 ms | **OK** |
| 7 | `07_branches` | `control` |    42.0 ms |    54.3 ms | 0 |    96.3 ms | **OK** |
| 8 | `08_while` | `control` |    41.6 ms |    54.9 ms | 0 |    96.5 ms | **OK** |
| 9 | `09_for` | `control` |    42.5 ms |    82.3 ms | 0 |   124.8 ms | **OK** |
| 10 | `10_for_dict` | `control` |    41.7 ms |    55.9 ms | 0 |    97.6 ms | **OK** |
| 11 | `11_class` | `oop` |    42.3 ms |    94.3 ms | 0 |   136.6 ms | **OK** |
| 12 | `12_inherit` | `oop` |    42.5 ms |    81.1 ms | 0 |   123.7 ms | **OK** |
| 13 | `13_private` | `oop` |    42.6 ms |    91.6 ms | 0 |   134.2 ms | **OK** |
| 14 | `14_static` | `oop` |    42.5 ms |    93.2 ms | 0 |   135.7 ms | **OK** |
| 15 | `15_union` | `oop` |    41.5 ms |    56.6 ms | 0 |    98.0 ms | **OK** |
| 16 | `16_closure` | `functional` |    41.8 ms |    93.3 ms | 0 |   135.2 ms | **OK** |
| 17 | `17_logic` | `logic` |    42.9 ms |    55.8 ms | 0 |    98.7 ms | **OK** |
| 18 | `18_compare` | `logic` |    41.9 ms |    54.5 ms | 0 |    96.4 ms | **OK** |
| 19 | `19_try_catch` | `errors` |    41.9 ms |    94.2 ms | 0 |   136.1 ms | **OK** |
| 20 | `20_fib` | `algorithms` |    42.2 ms |   106.8 ms | 0 |   148.9 ms | **OK** |
| 21 | `21_qsort` | `algorithms` |    42.7 ms |    97.8 ms | 0 |   140.5 ms | **OK** |
| 22 | `22_hof` | `functional` |    43.6 ms |    83.6 ms | 0 |   127.2 ms | **OK** |
| 23 | `23_deep_recur` | `stress` |    42.7 ms |    96.4 ms | 0 |   139.2 ms | **OK** |
| 24 | `24_str_advanced` | `basics` |    42.9 ms |    61.0 ms | 0 |   103.8 ms | **OK** |
| 25 | `25_destruct` | `basics` |    42.2 ms |    54.8 ms | 0 |    97.1 ms | **OK** |
| 26 | `26_perf_list` | `perf` |    42.2 ms |   103.7 ms | 0 |   145.9 ms | **OK** |
| 27 | `27_perf_dict` | `perf` |    42.1 ms |    83.4 ms | 0 |   125.6 ms | **OK** |
| 28 | `28_fizzbuzz` | `algorithms` |    41.7 ms |    82.2 ms | 0 |   123.9 ms | **OK** |
| 29 | `29_poly_dict` | `oop` |    42.2 ms |    94.1 ms | 0 |   136.3 ms | **OK** |
| 30 | `30_poly_class` | `oop` |    42.5 ms |    82.2 ms | 0 |   124.8 ms | **OK** |

## 4. Test Catalogue

| # | Test | Category | Purpose |
| ---: | --- | --- | --- |
| 1 | `01_literals` | `basics` | Variable declarations & primitive literals (int, float, str, bool, null) |
| 2 | `02_arith` | `basics` | Arithmetic operators + - * / % and precedence |
| 3 | `03_strings` | `basics` | String concatenation, indexing, slicing, ord/chr |
| 4 | `04_lists` | `collections` | List creation, indexing, push, +, * operators |
| 5 | `05_dicts` | `collections` | Dict creation, get, dynamic key assignment, len |
| 6 | `06_functions` | `functions` | Function def, multi-arg call, recursion (factorial) |
| 7 | `07_branches` | `control` | if / else / else-if and nested if statements |
| 8 | `08_while` | `control` | while loop with body and counter |
| 9 | `09_for` | `control` | for-in over list and over numeric range |
| 10 | `10_for_dict` | `control` | for-in over dict (key iteration) |
| 11 | `11_class` | `oop` | class, instance fields, methods, init pattern |
| 12 | `12_inherit` | `oop` | Single & multi-level class inheritance, super call |
| 13 | `13_private` | `oop` | private fields (name-mangled access) |
| 14 | `14_static` | `oop` | static methods on class |
| 15 | `15_union` | `oop` | Sum/union type construction and pattern-style access |
| 16 | `16_closure` | `functional` | Closures capturing outer state (counter, adder) |
| 17 | `17_logic` | `logic` | Boolean operators and / or / not |
| 18 | `18_compare` | `logic` | Comparison operators < <= > >= == != on numbers, strings, lists |
| 19 | `19_try_catch` | `errors` | try / catch / throw error handling |
| 20 | `20_fib` | `algorithms` | Recursive Fibonacci (small) |
| 21 | `21_qsort` | `algorithms` | Quicksort on a list of ints |
| 22 | `22_hof` | `functional` | Higher order functions: map, filter, reduce |
| 23 | `23_deep_recur` | `stress` | Deep recursion (call depth ~ 200) |
| 24 | `24_str_advanced` | `basics` | Advanced string ops: strip, split, join, replace, lower, upper |
| 25 | `25_destruct` | `basics` | List indexing & element extraction |
| 26 | `26_perf_list` | `perf` | Performance: 1000-element list operations |
| 27 | `27_perf_dict` | `perf` | Performance: 100-key dict operations |
| 28 | `28_fizzbuzz` | `algorithms` | FizzBuzz 1..20 |
| 29 | `29_poly_dict` | `oop` | Polymorphism via dict-dispatch |
| 30 | `30_poly_class` | `oop` | Polymorphism via class hierarchy |

## 5. Runtime Output (stdout)

### `01_literals`

```text
42
3.14
hello
true
null
```

### `02_arith`

```text
10
6
42
3
2
-10
14
20
```

### `03_strings`

```text
Hello World
5
H
el
Hello42
ell
65
B
```

### `04_lists`

```text
5
1
5
6
6
6
[1, 2, 3, 4, 5, 6, 10, 20, 30]
[0, 0, 0, 0, 0]
3
30
```

### `05_dicts`

```text
1
2
3
3
4
0
```

### `06_functions`

```text
7
24
49
1
120
720
```

### `07_branches`

```text
positive
nonneg
B
double
```

### `08_while`

```text
45
5040
```

### `09_for`

```text
15
45
[0, 1, 4, 9, 16]
```

### `10_for_dict`

```text
3
```

### `11_class`

```text
Rex
Rex makes a sound
3
4
7
```

### `12_inherit`

```text
Rex
dog
Rex says woof
puppy
Buddy says woof
```

### `13_private`

```text
150
```

### `14_static`

```text
13
```

### `15_union`

```text
5
3
4
7
```

### `16_closure`

```text
1
2
3
8
13
```

### `17_logic`

```text
false
true
false
true
true
true
true
false
true
true
```

### `18_compare`

```text
true
false
true
true
true
true
true
true
true
true
```

### `19_try_catch`

```text
10
negative!
-1
```

### `20_fib`

```text
0
1
1
5
55
610
```

### `21_qsort`

```text
[1, 2, 3, 4, 5, 6, 8, 9]
[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
[1, 2, 3, 4, 5]
[]
```

### `22_hof`

```text
[1, 4, 9, 16, 25]
[2, 4]
15
```

### `23_deep_recur`

```text
55
1275
5050
```

### `24_str_advanced`

```text
hello
[a, b, c]
x,y,z
hello world
HELLO WORLD
Hello H#
0
false
```

### `25_destruct`

```text
10
20
30
6
```

### `26_perf_list`

```text
1000
499500
1000
0
998001
```

### `27_perf_dict`

```text
100
100
9801
100
```

### `28_fizzbuzz`

```text
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
16
17
Fizz
19
Buzz
```

### `29_poly_dict`

```text
75
12
```

### `30_poly_class`

```text
4
```

## 7. Findings & Recommendations

- All 30 tests pass on the Kotlin runtime — H# v0.4 is healthy across the feature matrix.
- The Python compiler produced well-formed `.hbc` files for every construct we threw at it (classes, closures, inheritance, exceptions, higher-order functions, recursion).

**Bugs found and fixed during the latest run** (committed across the Python compiler and the Kotlin runtime):

1. `HVM.kt SET_ITEM` was re-pushing the assigned value onto the stack, breaking for-loops that mutate a dict inside the body (`for k in range(100) { d["k"+str(k)] = k*k }`).  Now a plain statement that does not leave a value on the stack, matching Python/Java/JS semantics.
2. `HbcReader.fixForLoopJumps` was only being applied to top-level module instructions.  For loops **inside** functions (e.g. `qsort`'s partition) iterated forever and OOM-ed.  The fix is now applied in `parseFunction` as well.
3. `HbcReader.parseClass` ignored `__static__` when the Python compiler emitted it at the **top level** of the class dict (the current layout).  Added a second pass that scans the top-level `__static__` map.
4. Static methods could not write to private fields because the private check required `self`.  We now pass a `__static_class__` env entry to static-method frames and allow private writes/reads when it matches the field's owning class.
5. **Slice syntax** (`s[1:3]`) — the Python parser did not understand `:` inside a subscript.  Added a `SliceExpression` AST node and a `_parse_subscript` helper; the compiler now emits a single `SLICE` opcode, and the Kotlin VM implements it for both `HString` and `HList` (with negative-index and step support).
6. **Chained method calls on literals** (`"abc".method(args)`) — the parser's `primary()` only allowed the postfix loop on identifiers, not on string/number literals.  Refactored to use a `_parse_postfix()` helper applied uniformly to all primary results.
7. **Closures** — added a `closure: MutableMap<String, HValue>` field on `HFunction` (each entry is a `HList` cell so the value can be mutated in place); added `LOAD_DEREF` / `STORE_DEREF` / `MAKE_CLOSURE` opcodes; rewrote the Python free-variable walker so it (a) returns the augmented bound set from each branch, (b) does not recurse into an inner function's body when computing the outer's freevars, and (c) excludes the function's own name from its own freevar set (so `fn fact(n) { ... fact(n-1) ... }` works without `fact` being treated as a freevar of itself).  Each `MAKE_CLOSURE` now constructs a **fresh** `HFunction` so that two independent calls (e.g. `makeAdder(5)` and `makeAdder(10)`) do not overwrite each other's captured cells.
8. **String / list built-in methods** — the Kotlin VM's `callMethod` previously only dispatched on classes and modules, so `"hello".strip()` and `lst.append(x)` failed at runtime.  Added dedicated `callStringMethod` and `callListMethod` handlers covering `strip / lstrip / rstrip / lower / upper / is_empty / len / length / starts_with / ends_with / contains / find / replace / split / join` for strings and `len / length / is_empty / append / push / pop / clear / contains` for lists.

**Verdict:** H# v0.4 is now feature-complete across the entire stress-test matrix — literals, arithmetic, strings, lists, dicts, classes, inheritance, private fields, static methods, sum/union types, closures with captured mutable state, try/catch, control flow, recursion (including deep recursion), higher-order functions, and 1000-element perf workloads all pass on the Kotlin runtime.  Pass rate is **100% (30/30)**.

## 8. Reproduction

```sh
# from the repo root
cd hsharp-kotlin-compiler
python3 stress-tests/run_tests.py
```

Outputs are written to `stress-tests/{hbc,out,report.md,results.json}`.
