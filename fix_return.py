#!/usr/bin/env python3
"""
自动修复 zzw-code-teacher 项目中 .hto 文件里的 `return;` 模式
策略: 把 `if (cond) { ...; return; }` 改为 `if (cond) { ... } else { rest }`
其中 rest 是该 if 之后,直到匹配的右花括号之前的全部代码块。
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
        # 简单数花括号
        for ch in line:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
    return -1


def find_if_block_end(lines, if_header_idx):
    """给定 `if (cond) {` 起始行,找到整个 if 块结束的下一个块(else / 后续)"""
    # 找 if 的左花括号行
    j = if_header_idx
    while j < len(lines) and "{" not in lines[j]:
        j += 1
    if j >= len(lines):
        return -1
    body_end = find_matching_brace(lines, j)
    return body_end


def fix_return_in_block(lines, block_start, block_end):
    """
    给定一个 block 的行范围 [block_start, block_end],扫描其中所有 `return;`
    将其转化为 if/else 嵌套.
    返回 (new_lines, changed)
    """
    # 递归处理:从最深的 return; 开始处理
    # 先找出 block 中所有 return; 行号
    return_lines = []
    for i in range(block_start, block_end + 1):
        s = lines[i].strip()
        if s == "return;":
            return_lines.append(i)

    if not return_lines:
        return lines, False

    # 处理最后一个 return; (最深的)
    # 它的转化: `if (cond) { ... return; }` -> `if (cond) { ... } else { <block_end 之后> }`
    # 找到包含这个 return; 的最近 if 块
    for ret_idx in return_lines:
        # 向上找最近的 `if (cond) {` 头
        if_start = -1
        for k in range(ret_idx - 1, block_start - 1, -1):
            stripped = lines[k].strip()
            if stripped.startswith("if ") and lines[k].rstrip().endswith("{"):
                # 找到 if 块头
                if_start = k
                break
            elif stripped.startswith("if ") and "{" in lines[k]:
                # 多行 if
                if_start = k
                break
            elif "return;" in lines[k]:
                # 嵌套更深的 return; 不归这个 if 管
                break

        if if_start < 0:
            # 这个 return; 不在 if 内,可能是函数末尾的 `return;`
            # 直接删除该行
            lines.pop(ret_idx)
            return fix_return_in_block(lines, block_start, block_end - 1)  # 重新扫描

        # 找 if 块的结束
        brace_line = if_start
        while brace_line < len(lines) and "{" not in lines[brace_line]:
            brace_line += 1
        if brace_line >= len(lines):
            continue
        if_end = find_matching_brace(lines, brace_line)
        if if_end < 0:
            continue

        # 检查 if 块内部是否还有 return; 在 ret_idx 之外
        # 简单起见,我们只处理 if 块体内只含一个 return; 的情况
        inner_returns = []
        for m in range(if_start, if_end + 1):
            if lines[m].strip() == "return;":
                inner_returns.append(m)

        if len(inner_returns) != 1 or inner_returns[0] != ret_idx:
            # 跳过复杂的(有多个 return; 或 return; 不在最深处)
            continue

        # 现在做转换: 把 ret_idx 这一行删掉,然后在 if 结束 } 之后插入 else { ... }
        # 1) 取出 if 的 header 部分
        if_header = lines[if_start]
        # 2) 取出 if 头部到第一个 { 之间的内容 (如果跨行)
        #    我们只处理单行 if header
        # 3) 取出 if_end 之后到 block_end 之间的内容
        rest_lines = lines[if_end + 1:block_end + 1]

        # 4) 重构: 保留 if_header, 内部去掉 return; 行, 加上 else { rest_lines }
        #    但要注意缩进
        #    找出 if_header 的缩进
        m = re.match(r"^(\s*)", if_header)
        indent = m.group(1) if m else ""

        # 找出 rest_lines 中每行的最小缩进(去除空行)
        non_empty = [ln for ln in rest_lines if ln.strip() != ""]
        if non_empty:
            min_indent = min(len(ln) - len(ln.lstrip()) for ln in non_empty)
        else:
            min_indent = 0

        # 移除 return; 行
        new_if_block = []
        for m in range(if_start, if_end + 1):
            if lines[m].strip() == "return;":
                continue
            new_if_block.append(lines[m])
        # new_if_block[0] 是 if header
        # new_if_block[-1] 是 }

        # 构建 else 块
        new_else_lines = []
        # else 头: 与 if_header 同缩进
        new_else_lines.append(indent + "} else {")
        for ln in rest_lines:
            if ln.strip() == "":
                new_else_lines.append(ln)
            else:
                # 增加缩进: 原缩进 + 一个 level
                extra = "    "
                # 计算原行相对 min_indent 的缩进
                old_indent = len(ln) - len(ln.lstrip())
                if old_indent >= min_indent:
                    stripped_part = ln[min_indent:]
                else:
                    stripped_part = ln.lstrip()
                new_else_lines.append(indent + extra + stripped_part)
        # 关闭 else 块
        new_else_lines.append(indent + "}")

        # 替换
        new_lines = lines[:if_start] + new_if_block + new_else_lines + lines[block_end + 1:]
        return fix_return_in_block(new_lines, block_start, len(new_lines) - 1)

    return lines, True


def process_file(path):
    with open(path) as f:
        lines = f.readlines()

    # 把每行末尾的换行去掉,以便后续处理
    lines = [l.rstrip("\n") for l in lines]

    # 先找所有 fn 头
    fn_starts = []
    for i, line in enumerate(lines):
        if line.strip().startswith("fn "):
            fn_starts.append(i)

    # 对每个 fn 块处理
    new_lines = lines[:]
    for fn_idx in fn_starts:
        # 找 fn 块的开始 {
        j = fn_idx
        while j < len(new_lines) and "{" not in new_lines[j]:
            j += 1
        if j >= len(new_lines):
            continue
        # fn 块结束
        fn_end = find_matching_brace(new_lines, j)
        if fn_end < 0:
            continue
        # 处理
        new_lines, _ = fix_return_in_block(new_lines, fn_idx, fn_end)
        # 注意 fn 块索引会变,但因为我们顺序处理,前面的 fn 不会影响后面的
        # 不再依赖原始索引

    if new_lines != lines:
        with open(path, "w") as f:
            f.write("\n".join(new_lines) + "\n")
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
