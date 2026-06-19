# H# v0.4 — Tests Package

## 快速运行

```bash
# 联合类型
python3 interpreter.py bootstrap/test_union.hto

# zzwUI 基础
python3 interpreter.py bootstrap/test_hwdui.hto

# .NET 协同
python3 interpreter.py bootstrap/test_hwdui_dotnet.hto

# Java 协同
python3 interpreter.py bootstrap/test_hwdui_java.hto

# C++ 协同
python3 interpreter.py bootstrap/test_hwdui_cpp.hto

# 机器学习
python3 interpreter.py bootstrap/test_hsharpmyl.hto
python3 interpreter.py bootstrap/test_hsharpmyl_v4.hto

# 标准库
python3 interpreter.py bootstrap/test_standard_libs.hto

# 编译器链
python3 interpreter.py bootstrap/test_compiler_chain.hto

# 解释器链
python3 interpreter.py bootstrap/test_interp_chain.hto

# 自举
python3 interpreter.py bootstrap/selftest.hto
```

## 运行所有测试

```bash
./run_all_tests.sh
```

## 测试结果

| 测试 | 通过 | 状态 |
|------|------|------|
| test_union.hto | 14/14 | ✅ |
| test_hwdui_dotnet.hto | 276/276 | ✅ |
| test_hwdui_java.hto | 407/407 | ✅ |
| test_hwdui_cpp.hto | 780/780 | ✅ |
| test_hsharpmyl.hto | 100% | ✅ |
