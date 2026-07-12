#!/usr/bin/env python3
"""
自动修复 zzw-code-teacher 中 .hto 文件里的 `return;` 模式
策略: 把 `if (cond) { return; }` 转为 `if (!(cond)) { ...rest... }`
其中 rest 是该 if 之后、直到外层 block 结束的代码(全部增加缩进)
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path("/Users/peddlejumper/H#/v0.4/zzw-code-teacher")


def find_matching_brace(lines, start_idx):
    """从 start_idx 开始,找到第一个 '{' 并向下找匹配的 '}' 行索引"""
    j = start_idx
    while j < len(lines) and "{" not in lines[j]:
        j += 1
    if j >= len(lines):
        return -1
    depth = 0
    for i in range(j, len(lines)):
        line = lines[i]
        for ch in line:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
    return -1


def get_indent(line):
    return len(line) - len(line.lstrip())


def negate_condition(cond):
    """if (cond) -> if (!(cond))"""
    cond = cond.strip()
    # 简单取反
    return f"!({cond})"


def fix_block(lines, block_start, block_end):
    """
    给定一个 block [block_start, block_end],扫描其中所有 `if (cond) { return; }` 行
    将其替换为 `if (!(cond)) { rest }`,其中 rest 是 if 之后到 block_end 之间的全部内容.
    """
    # 多次循环,每次处理一个
    while True:
        # 找一个 `if (...) { return; }` 行
        target = -1
        for i in range(block_start, block_end + 1):
            s = lines[i].strip()
            if re.match(r"^if\s*\(.*\)\s*\{\s*return\s*;\s*\}\s*$", s):
                target = i
                break
        if target < 0:
            return lines, False

        # 解析 if 的条件
        m = re.match(r"^if\s*\((.*)\)\s*\{\s*return\s*;\s*\}\s*$", lines[target].strip())
        cond = m.group(1).strip()
        negated = negate_condition(cond)

        # if 行的缩进
        if_indent = get_indent(lines[target])

        # if 行之后到 block_end 的内容 (rest)
        rest_start = target + 1
        rest_end = block_end

        if rest_start > rest_end:
            # 没有 rest,简单删除 if 行
            new_lines = lines[:target] + lines[target + 1:]
            # 调整 block_end
            return fix_block(new_lines, block_start, block_end - 1)

        # 计算 rest 中每行的最小缩进
        non_empty = [ln for ln in lines[rest_start:rest_end + 1] if ln.strip() != ""]
        if non_empty:
            min_indent = min(get_indent(ln) for ln in non_empty)
        else:
            min_indent = if_indent + 4

        # 新行: `if (!(cond)) {` (与原 if 同缩进)
        new_if_line = " " * if_indent + f"if ({negated}) {{"
        new_rest_lines = []
        for ln in lines[rest_start:rest_end + 1]:
            if ln.strip() == "":
                new_rest_lines.append(ln)
            else:
                # 增加 4 空格缩进
                old_indent = get_indent(ln)
                if old_indent >= min_indent:
                    extra = ln[min_indent:]
                else:
                    extra = ln.lstrip()
                new_rest_lines.append(" " * (if_indent + 4) + extra)
        new_close = " " * if_indent + "}"

        new_lines = lines[:target] + [new_if_line] + new_rest_lines + [new_close] + lines[rest_end + 1:]
        return fix_block(new_lines, block_start, len(new_lines) - 1)


def process_file(path):
    with open(path) as f:
        content = f.read()

    # 跳过字符串字面量
    # 简单处理: 不改 "..." 内部的 return;
    # 但实际上 H# 字符串中 "return;\n" 是普通字符,我们用一种不严格的方法:
    # 我们只处理 `if (...) { return; }` 这种模式,字符串里如果有这种模式,会被替换,需手工注意

    lines = content.split("\n")
    new_lines = lines[:]

    # 找所有 fn 头
    fn_starts = []
    for i, line in enumerate(new_lines):
        if re.match(r"^\s*fn\s+\w+", line):
            fn_starts.append(i)

    for fn_idx in fn_starts:
        j = fn_idx
        while j < len(new_lines) and "{" not in new_lines[j]:
            j += 1
        if j >= len(new_lines):
            continue
        fn_end = find_matching_brace(new_lines, j)
        if fn_end < 0:
            continue
        new_lines, _ = fix_block(new_lines, fn_idx, fn_end)

    if new_lines != lines:
        with open(path, "w") as f:
            f.write("\n".join(new_lines))
        return True
    return False


def main():
    changed = []
    for root, _, files in os.walk(ROOT):
        for fn in files:
            if fn.endswith(".hto"):
                p = Path(root) / fn
                if process_file(p):
                    changed.append(str(p))
    print("Changed files:")
    for c in changed:
        print(f"  {c}")


if __name__ == "__main__":
    main()
