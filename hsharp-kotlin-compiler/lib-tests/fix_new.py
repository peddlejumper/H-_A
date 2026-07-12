#!/usr/bin/env python3
"""Add `new` keyword to class instantiations in lib-test .hto files.
Pattern: let <var> = ClassName(...);  ->  let <var> = new ClassName(...);
"""
import re
from pathlib import Path

# Match: let <var> = ClassName(...);
# Where ClassName starts with uppercase (Python convention for classes)
# But we need to be careful not to match builtins like len(), int(), etc.
# Solution: match class names that are followed by an uppercase letter
# and are in a known list of classes.
CLASSES = ['Stack', 'BankAccount', 'Cart', 'Point', 'Rect', 'Counter',
           'Node', 'Tree', 'TreeNode', 'LinkedList', 'DoublyLinkedList',
           'BinaryTree', 'BST', 'Graph', 'Matrix', 'Vector', 'Queue',
           'Deque', 'Heap', 'Pair', 'Triple', 'MinStack', 'FrequencyMap',
           'BSTNode', 'BinarySearchTree', 'Student', 'Gradebook',
           'Animal', 'Dog', 'Cat', 'Shape', 'Circle', 'Square',
           'Matrix2x2', 'Vec2', 'Vec3']


def update_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    for cls in CLASSES:
        # Match: <cls>( ...) but NOT new <cls>(...)
        # Use a negative lookbehind for 'new '
        text = re.sub(
            r'(?<!new )(?<![A-Za-z0-9_])' + re.escape(cls) + r'\(',
            f'new {cls}(',
            text,
        )
    if text == orig:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main():
    root = Path("/Users/peddlejumper/H#/v0.4/hsharp-kotlin-compiler/lib-tests/hto")
    n = 0
    for f in sorted(root.glob("*.hto")):
        if update_file(f):
            print(f"  updated  {f.name}")
            n += 1
    print(f"done: {n} files updated")


if __name__ == "__main__":
    main()
