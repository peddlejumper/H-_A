# -*- coding: utf-8 -*-
"""
《H# 从入门到精通》第五部分
第八篇 工具链与生态(第32-35章)+ 附录
"""


def add_content(doc, H):
    # ================================================================
    # 第八篇 工具链与生态
    # ================================================================
    H.h1("第八篇 工具链与生态")

    H.para("经过前七篇的学习,你已经掌握了 H# 语言的语法、类型系统、并发编程和高级特性。本篇将深入探讨 H# 的工具链与生态系统——从标准库到字节码虚拟机,从自举编译到打包发布,帮助你从「会写 H#」迈向「会用 H# 构建完整项目」。")

    H.para("H# v0.4.1 拥有三套运行时:Python AST 解释器(开发调试用)、Python 字节码 VM(性能过渡用)和 Kotlin HVM 栈机(生产主运行时)。本篇将从标准库出发,逐步深入字节码格式、自举实现和项目部署,完整呈现 H# 工具链的全貌。")

    # ================================================================
    # 第32章 标准库
    # ================================================================
    H.h2("第32章 标准库")

    H.para("标准库是任何编程语言的核心基础设施。H# 的标准库由内置函数(builtins)和 bootstrap 模块库两部分组成。内置函数直接由运行时提供,无需导入即可使用;bootstrap 模块库则用 H# 自身编写,涵盖字符串工具、数组工具、数学工具等丰富的功能。本章将全面介绍 H# 内置函数的分类与用法。")

    # ----------------------------------------------------------------
    H.h3("32.1 内置函数总览")

    H.para("H# 的内置函数按功能可分为六大类:类型转换函数、集合操作函数、字符串函数、IO 函数、数学函数和时间函数。下表列出了所有内置函数及其分类:")

    H.bullet("类型函数:type(返回类型名)、int(转整数)、float(转浮点)、str(转字符串)")
    H.bullet("集合函数:len(长度)、push(追加)、pop(弹出)、dict_keys(键列表)、dict_values(值列表)、dict_items(键值对列表)、has_key(键存在检查)、range(生成数列)")
    H.bullet("字符串函数:substring(子串)、ord(字符转码点)、chr(码点转字符)")
    H.bullet("IO 函数:read_file(读文件)、write_file(写文件)")
    H.bullet("数学函数:abs(绝对值)、min(最小值)、max(最大值)")
    H.bullet("时间函数:time_now(当前时间戳,毫秒)")

    H.note("在 Python AST 解释器(interpreter.py)中,部分函数(type、abs、min、max、range、has_key)未作为内置函数直接注册,需要用户自行实现。在 Kotlin HVM 和 Python 字节码 VM(bytecode.py)中,这些函数均已内置。本章将在示例中提供 H# 实现版本。")

    # ----------------------------------------------------------------
    H.h3("32.2 字符串函数")

    H.para("H# 提供了三个核心字符串内置函数:substring、ord 和 chr。它们分别用于子串提取、字符到码点的转换和码点到字符的转换。配合 len() 和 str() 可以完成大部分字符串操作。")

    H.h4("32.2.1 substring(s, start, length)")

    H.para("substring 函数从字符串 s 的 start 位置开始,提取长度为 length 的子串。参数 start 从 0 开始计数。")

    H.code("""# substring 函数示例
let s = "Hello, World!";

# 从位置0开始取5个字符
print(substring(s, 0, 5));

# 从位置7开始取5个字符
print(substring(s, 7, 5));

# 取单个字符
print(substring(s, 0, 1));
print(substring(s, 6, 1));
""")

    H.output("""Hello
World
H
,""")

    H.h4("32.2.2 ord(ch) 和 chr(n)")

    H.para("ord 函数返回字符的 ASCII/Unicode 码点(整数),chr 函数则将码点转换回字符。这两个函数互为逆操作,常用于字符编码处理和加密算法。")

    H.code("""# ord 和 chr 函数示例

# 字符转码点
print(ord("A"));
print(ord("a"));
print(ord("0"));

# 码点转字符
print(chr(65));
print(chr(97));
print(chr(48));

# 大小写转换:利用码点差值
fn to_upper(ch) {
    let code = ord(ch);
    if (code >= 97 and code <= 122) {
        return chr(code - 32);
    }
    return ch;
}

fn to_lower(ch) {
    let code = ord(ch);
    if (code >= 65 and code <= 90) {
        return chr(code + 32);
    }
    return ch;
}

print(to_upper("h"));
print(to_lower("H"));
""")

    H.output("""65
97
48
A
a
0
H
h""")

    H.h4("32.2.3 str(x)")

    H.para("str 函数将任意值转换为字符串表示形式。这是 H# 中最常用的类型转换函数,特别是在字符串拼接场景中。")

    H.code("""# str 函数示例
let n = 42;
let f = 3.14;
let b = true;
let arr = [1, 2, 3];
let d = {"key": "value"};

# 各种类型转字符串
print("int: " + str(n));
print("float: " + str(f));
print("bool: " + str(b));
print("list: " + str(arr));
print("dict: " + str(d));

# 字符串拼接
let name = "H#";
let version = "0.4.1";
print("Welcome to " + name + " v" + version);
""")

    H.output("""int: 42
float: 3.14
bool: True
list: [1, 2, 3]
dict: {'key': 'value'}
Welcome to H# v0.4.1""")

    # ----------------------------------------------------------------
    H.h3("32.3 数学函数")

    H.para("H# 内置了 abs、min、max、range 四个数学函数。在字节码 VM 中它们直接可用;在 AST 解释器中,我们可以用 H# 轻松实现等价功能。")

    H.h4("32.3.1 abs(x) —— 绝对值")

    H.code("""# abs 函数的 H# 实现
fn abs(x) {
    if (x < 0) {
        return 0 - x;
    }
    return x;
}

print(abs(-5));
print(abs(7));
print(abs(-3.14));
print(abs(0));
""")

    H.output("""5
7
3.14
0""")

    H.h4("32.3.2 min(lst) 和 max(lst) —— 最值查找")

    H.code("""# min 和 max 的 H# 实现
fn min(lst) {
    let m = lst[0];
    let i = 1;
    while (i < len(lst)) {
        if (lst[i] < m) {
            m = lst[i];
        }
        i = i + 1;
    }
    return m;
}

fn max(lst) {
    let m = lst[0];
    let i = 1;
    while (i < len(lst)) {
        if (lst[i] > m) {
            m = lst[i];
        }
        i = i + 1;
    }
    return m;
}

let nums = [3, 1, 4, 1, 5, 9, 2, 6];
print("min: " + str(min(nums)));
print("max: " + str(max(nums)));
""")

    H.output("""min: 1
max: 9""")

    H.h4("32.3.3 range(n) —— 生成整数序列")

    H.code("""# range 的 H# 实现
fn range(n) {
    let result = [];
    let i = 0;
    while (i < n) {
        push(result, i);
        i = i + 1;
    }
    return result;
}

let nums = range(5);
print(nums);

# 使用 range 遍历
let i = 0;
while (i < len(nums)) {
    print("  index " + str(i) + " = " + str(nums[i]));
    i = i + 1;
}
""")

    H.output("""[0, 1, 2, 3, 4]
  index 0 = 0
  index 1 = 1
  index 2 = 2
  index 3 = 3
  index 4 = 4""")

    # ----------------------------------------------------------------
    H.h3("32.4 集合函数")

    H.para("集合函数是 H# 中操作列表和字典的核心工具。H# 的列表用 [] 创建,字典用 {} 创建。内置集合函数提供了长度查询、元素增删和字典遍历等基础能力。")

    H.h4("32.4.1 len(obj) —— 长度查询")

    H.para("len 函数可以作用于列表、字符串和字典,返回它们的元素个数。")

    H.code("""# len 函数示例
let arr = [10, 20, 30, 40, 50];
print("Array length: " + str(len(arr)));

let s = "Hello";
print("String length: " + str(len(s)));

let d = {"a": 1, "b": 2, "c": 3};
print("Dict length: " + str(len(d)));
""")

    H.output("""Array length: 5
String length: 5
Dict length: 3""")

    H.h4("32.4.2 push(lst, item) 和 pop(lst)")

    H.para("push 向列表末尾追加元素,pop 从列表末尾弹出元素。这两个函数实现了列表的栈操作。")

    H.code("""# push 和 pop 示例
let stack = [];

# 入栈
push(stack, "first");
push(stack, "second");
push(stack, "third");
print("Stack: " + str(stack));
print("Length: " + str(len(stack)));

# 出栈
let top = pop(stack);
print("Popped: " + top);
print("Stack now: " + str(stack));

# 用 push/pop 实现队列反转
let queue = [1, 2, 3, 4, 5];
let reversed = [];
while (len(queue) > 0) {
    push(reversed, pop(queue));
}
print("Reversed: " + str(reversed));
""")

    H.output("""Stack: ['first', 'second', 'third']
Length: 3
Popped: third
Stack now: ['first', 'second']
Reversed: [5, 4, 3, 2, 1]""")

    H.h4("32.4.3 字典操作函数")

    H.para("dict_keys、dict_values、dict_items 分别返回字典的键列表、值列表和键值对列表。has_key 检查字典是否包含指定键。")

    H.code("""# 字典操作函数示例
let scores = {"Alice": 95, "Bob": 87, "Charlie": 92};

# 获取键、值、键值对
print("Keys: " + str(dict_keys(scores)));
print("Values: " + str(dict_values(scores)));
print("Items: " + str(dict_items(scores)));

# has_key 的 H# 实现
fn has_key(d, k) {
    let keys = dict_keys(d);
    let i = 0;
    while (i < len(keys)) {
        if (keys[i] == k) {
            return true;
        }
        i = i + 1;
    }
    return false;
}

print("Has Alice: " + str(has_key(scores, "Alice")));
print("Has Dave: " + str(has_key(scores, "Dave")));

# 遍历字典
for name, score in scores {
    print(name + ": " + str(score));
}
""")

    H.output("""Keys: ['Alice', 'Bob', 'Charlie']
Values: [95, 87, 92]
Items: [['Alice', 95], ['Bob', 87], ['Charlie', 92]]
Has Alice: True
Has Dave: False
Alice: 95
Bob: 87
Charlie: 92""")

    # ----------------------------------------------------------------
    H.h3("32.5 IO 函数")

    H.para("H# 提供了 read_file 和 write_file 两个文件 IO 函数,支持读写文本文件。这两个函数是 H# 与外部世界交换数据的基础。")

    H.code("""# IO 函数示例

# 写入文件
write_file("greeting.txt", "Hello from H#!\\nThis is line 2.\\n");
print("File written.");

# 读取文件
let content = read_file("greeting.txt");
print("File content:");
print(content);

# 追加内容(先读后写)
let old = read_file("greeting.txt");
write_file("greeting.txt", old + "This is line 3.\\n");
print("After append:");
print(read_file("greeting.txt"));
""")

    H.output("""File written.
File content:
Hello from H#!
This is line 2.

After append:
Hello from H#!
This is line 2.
This is line 3.""")

    H.note("write_file 会覆盖已有文件内容。如需追加,请先读取原内容再拼接写入。文件编码默认为 UTF-8。")

    # ----------------------------------------------------------------
    H.h3("32.6 时间函数")

    H.para("time_now 函数返回当前时间的 Unix 时间戳(毫秒),常用于性能测量和随机数种子。")

    H.code("""# time_now 函数示例

# 获取当前时间戳(毫秒)
let t1 = time_now();
print("Timestamp: " + str(t1));

# 性能测量:计算代码执行时间
let i = 0;
let sum = 0;
while (i < 10000) {
    sum = sum + i;
    i = i + 1;
}
let t2 = time_now();
let elapsed = t2 - t1;
print("Sum: " + str(sum));
print("Elapsed: " + str(elapsed) + " ms");
""")

    H.output("""Timestamp: 1783657115557
Sum: 49995000
Elapsed: 3 ms""")

    H.warning("time_now 返回的时间戳在不同运行环境中数值不同,上述输出仅为示例。重点理解其毫秒级精度和性能测量用法。")

    # ----------------------------------------------------------------
    H.h3("32.7 类型函数")

    H.para("类型函数用于检测和转换值的类型。H# 是动态类型语言,运行时通过 type 函数可以获取值的类型名称。")

    H.h4("32.7.1 type(x) —— 类型检测")

    H.para("type 函数返回值的数据类型名称字符串。在字节码 VM 中直接可用,在 AST 解释器中可以用 H# 实现。")

    H.code("""# type 函数的 H# 实现
fn type(x) {
    if (x == true or x == false) {
        return "bool";
    }
    let s = str(x);
    if (x + 0 == x) {
        if (x == int(x)) {
            return "int";
        }
        return "float";
    }
    return "string";
}

print(type(42));
print(type(3.14));
print(type("hello"));
print(type(true));
print(type(false));
""")

    H.output("""int
float
string
bool
bool""")

    H.h4("32.7.2 int(x) 和 float(x) —— 数值转换")

    H.code("""# int 和 float 转换示例

# 字符串转数字
print(int("123"));
print(int("456"));
print(float("3.14"));
print(float("2.718"));

# 数字之间转换
print(int(3.99));
print(float(42));

# 用于计算
let input = "100";
let result = int(input) * 2;
print("Result: " + str(result));
""")

    H.output("""123
456
3.14
2.718
3
42.0
Result: 200""")

    # ----------------------------------------------------------------
    H.h3("32.8 小结")

    H.para("本章全面介绍了 H# 标准库的内置函数体系。核心要点如下:")

    H.number("H# 内置函数分为六大类:类型、集合、字符串、IO、数学、时间,覆盖了日常编程的大部分需求。")
    H.number("字符串函数 substring/ord/chr 是文本处理的基础,配合 str 和 len 可以完成大部分字符串操作。")
    H.number("集合函数 len/push/pop/dict_keys/dict_values/dict_items 是操作列表和字典的核心工具。")
    H.number("IO 函数 read_file/write_file 提供了文件读写能力,是数据持久化的基础。")
    H.number("在 AST 解释器中,部分函数(type/abs/min/max/range/has_key)需要用户自行实现,这既是限制也是学习 H# 的好机会。")
    H.number("bootstrap 模块库提供了更丰富的功能:字符串工具、数组工具、数学工具、格式化工具等,详见第34章。")

    H.h3("32.9 练习")

    H.number("实现一个 to_uppercase(s) 函数,将字符串中的所有小写字母转换为大写。提示:遍历字符串,用 ord 和 chr 转换。")
    H.number("实现一个 str_split(s, delim) 函数,将字符串按分隔符拆分为列表。例如 str_split(\"a,b,c\", \",\") 返回 [\"a\", \"b\", \"c\"]。")
    H.number("实现一个 dict_merge(d1, d2) 函数,将两个字典合并为一个新字典,冲突时 d2 的值优先。")
    H.number("编写一个程序,用 time_now 测量 1000 次循环和 10000 次循环的执行时间差异。")
    H.number("实现一个 counter 计数器,用 write_file 将每次调用记录写入日志文件,用 read_file 读取并显示历史记录。")

    H.page_break()

    # ================================================================
    # 第33章 字节码 VM
    # ================================================================
    H.h2("第33章 字节码 VM")

    H.para("H# 拥有双运行时架构:AST 解释器(直接遍历语法树执行)和字节码 VM(将源码编译为字节码再执行)。字节码 VM 虽然增加了编译步骤,但执行效率更高,且支持序列化为 .hbc 文件实现「一次编译,多处运行」。本章将深入 H# 字节码 VM 的内部机制。")

    # ----------------------------------------------------------------
    H.h3("33.1 H# 双运行时架构回顾")

    H.para("H# 的代码执行有两条路径:")

    H.bullet("AST 解释器路径:源码(.hto) → 词法分析(lexer.py) → 语法分析(parser.py) → AST → 直接遍历执行(interpreter.py)。这是开发调试时的默认路径。")
    H.bullet("字节码 VM 路径:源码(.hto) → 词法分析 → 语法分析 → AST → 编译器(compiler.py) → 字节码 → VM 执行(bytecode.py)。这是性能优化和打包部署时的路径。")

    H.para("两条路径共享同一套词法分析器和语法分析器,保证语义一致性。区别在于执行引擎:AST 解释器是树遍历方式,字节码 VM 是栈机方式。")

    H.note("在 v0.4.1 中,还有第三条路径:Kotlin HVM 栈机。它加载 .hbc 字节码文件执行,是生产环境的主运行时。详见第35章。")

    # ----------------------------------------------------------------
    H.h3("33.2 Python 字节码 VM 介绍")

    H.para("Python 字节码 VM(bytecode.py)是 H# 的第二套执行引擎。它接收编译器生成的字节码指令流,通过栈式虚拟机逐条解释执行。相比 AST 解释器,字节码 VM 有以下优势:")

    H.bullet("执行效率更高:指令派发比 AST 遍历更快,且支持内联缓存等优化。")
    H.bullet("可序列化:字节码可保存为 .hbc 文件,实现预编译和跨平台分发。")
    H.bullet("支持 Fast Locals:通过寄存器分配优化局部变量访问。")
    H.bullet("内联缓存:对属性查找和方法调用进行单态内联缓存,加速 OOP 操作。")

    H.para("字节码 VM 的核心类是 VM,定义在 bytecode.py 中。它接收一个包含 instructions(指令列表)和 consts(常量池)的字典,通过 run() 方法执行。")

    # ----------------------------------------------------------------
    H.h3("33.3 bytecode 格式")

    H.para("H# 的字节码采用 JSON 容器格式,而非自定义二进制格式。这一设计决策使得任何语言都能用标准库解析字节码,无需专门的反序列化工具。")

    H.para("字节码的核心数据结构是一个 Python 字典(或 JSON 对象),包含两个关键字段:")

    H.code("""# bytecode 数据结构(Python dict / JSON)
{
    "instructions": [
        ["LOAD_CONST", 0],      # 指令: [操作码, 参数]
        ["STORE_NAME", "x"],    # 将栈顶存入变量 x
        ["LOAD_NAME", "x"],     # 加载变量 x 到栈顶
        ["PRINT", null],        # 打印栈顶
        ["HALT", null]          # 停止执行
    ],
    "consts": [
        42                       # 常量池: 按索引引用
    ]
}
""")

    H.para("每条指令是一个二元组 [opname, arg]:opname 是大写操作码字符串(如 LOAD_CONST),arg 是参数(可为 null、整数、字符串或二元数组)。常量池是一个数组,存放字面量(数字、字符串)、函数对象和类对象等。")

    # ----------------------------------------------------------------
    H.h3("33.4 .hbc 文件格式")

    H.para(".hbc 文件是 H# 字节码的持久化存储格式。它是标准 JSON 文件,顶层结构如下:")

    H.code("""# .hbc 文件顶层结构(JSON)
{
    "version": "v0.4",
    "modules": {
        "main": {
            "instructions": [...],
            "consts": [...]
        }
    },
    "built_at": 1718889600
}
""")

    H.para("顶层包含三个字段:version(格式版本,当前为 v0.4)、modules(模块映射,key 为模块名,value 为模块字节码)和 built_at(编译时间戳)。单模块文件的模块名通常为 main;多模块 bundle 则包含多个命名模块。")

    H.note(".hbc 文件使用 JSON 而非二进制格式,这是 H# 的核心设计决策之一。好处是零依赖解析、人类可读、跨语言互操作;代价是文件体积稍大于二进制格式。")

    # ----------------------------------------------------------------
    H.h3("33.5 核心指令集")

    H.para("H# 字节码 VM 的指令集分为十大类。下表列出最常用的核心指令:")

    H.h4("33.5.1 常量与变量指令")

    H.bullet("LOAD_CONST idx:推送常量池[idx]到栈顶")
    H.bullet("LOAD_NAME name:从环境查找变量 name 并推送")
    H.bullet("STORE_NAME name:弹栈存入变量 name")
    H.bullet("LOAD_FAST idx:从 fast_slots[idx] 加载(优化指令)")
    H.bullet("STORE_FAST idx:存入 fast_slots[idx](优化指令)")
    H.bullet("POP_TOP:弹栈丢弃")
    H.bullet("PRINT:弹栈并打印")

    H.h4("33.5.2 二元运算指令")

    H.bullet("BINARY_ADD:弹 b,弹 a,推送 a + b")
    H.bullet("BINARY_SUB:弹 b,弹 a,推送 a - b")
    H.bullet("BINARY_MUL:弹 b,弹 a,推送 a * b")
    H.bullet("BINARY_DIV:弹 b,弹 a,推送 a // b(整数除法)")
    H.bullet("BINARY_MOD:弹 b,弹 a,推送 a % b")

    H.h4("33.5.3 控制流指令")

    H.bullet("JUMP target:无条件跳转到指令索引 target")
    H.bullet("JUMP_IF_FALSE target:弹栈,若为 false 则跳转")
    H.bullet("FOR_ITER end:迭代器推进,迭代结束则跳转到 end")
    H.bullet("COMPARE_OP op:弹 b,弹 a,推送比较结果(op ∈ EQEQ, BANGEQ, GT, LT, GTE, LTE)")

    H.h4("33.5.4 函数调用指令")

    H.bullet("CALL_FUNCTION [name, argc]:调用命名函数,argc 为参数个数")
    H.bullet("CALL_METHOD [name, argc]:调用实例方法")
    H.bullet("CALL_VALUE argc:调用栈顶的可调用对象(闭包)")
    H.bullet("CALL_NEW argc:实例化类(new 操作)")
    H.bullet("RETURN_VALUE:返回栈顶值")

    # ----------------------------------------------------------------
    H.h3("33.6 编译流程:源码到字节码")

    H.para("从 H# 源码到字节码的编译流程分为三步:词法分析、语法分析和字节码生成。前两步由 lexer.py 和 parser.py 完成(与 AST 解释器共享),第三步由 compiler.py 完成。")

    H.para("编译器(Compiler 类)递归遍历 AST,为每种节点生成对应的字节码指令。例如,let 声明生成 LOAD_CONST + STORE_NAME,函数调用生成 CALL_FUNCTION,if 语句生成 JUMP_IF_FALSE + JUMP 等。")

    H.code("""# 编译流程演示(Python 代码)
# 以下展示 H# 源码如何被编译为字节码

# H# 源码:
#   let x = 42;
#   let y = x + 8;
#   print(y);

# 编译后的字节码:
#   instructions:
#     ["LOAD_CONST", 0]       # 加载常量 42
#     ["STORE_NAME", "x"]     # 存入变量 x
#     ["LOAD_NAME", "x"]      # 加载变量 x
#     ["LOAD_CONST", 1]       # 加载常量 8
#     ["BINARY_ADD", null]    # x + 8
#     ["STORE_NAME", "y"]     # 存入变量 y
#     ["LOAD_NAME", "y"]      # 加载变量 y
#     ["PRINT", null]         # 打印
#     ["HALT", null]          # 停止
#   consts:
#     [42, 8]
""")

    H.para("可以看到,let x = 42 被编译为 LOAD_CONST 0(加载常量池第0项,即42)和 STORE_NAME x(存入变量x)。表达式 x + 8 被编译为先加载操作数再执行 BINARY_ADD 的后缀表达式序列。")

    # ----------------------------------------------------------------
    H.h3("33.7 实战:编译并查看字节码")

    H.para("让我们用一个完整的例子来演示从源码到执行的全过程。以下 H# 代码定义了一个加法函数并调用它:")

    H.code("""# 源码示例:函数定义与调用
fn add(a, b) {
    return a + b;
}

let result = add(5, 3);
print(result);
""")

    H.para("运行上述代码,输出为 8。现在我们查看它编译后的字节码结构:")

    H.code("""# 编译后的字节码(JSON 格式,已格式化)
{
  "instructions": [
    ["LOAD_CONST", 0],              # 加载函数对象 add
    ["STORE_NAME", "add"],          # 存入变量 add
    ["LOAD_CONST", 1],              # 加载常量 5
    ["LOAD_CONST", 2],              # 加载常量 3
    ["CALL_FUNCTION", ["add", 2]],  # 调用 add(5, 3)
    ["STORE_NAME", "result"],       # 存入变量 result
    ["LOAD_NAME", "result"],        # 加载 result
    ["PRINT", null],                # 打印
    ["HALT", null]                  # 停止
  ],
  "consts": [
    {
      "args": ["a", "b"],
      "bytecode": [
        ["LOAD_NAME", "a"],
        ["LOAD_NAME", "b"],
        ["BINARY_ADD", null],
        ["RETURN_VALUE", null]
      ],
      "consts": []
    },
    5,
    3
  ]
}
""")

    H.para("注意常量池的第0项是一个函数对象,它自身包含 args(参数列表)、bytecode(函数体指令)和 consts(函数私有常量池)。这种嵌套结构使得函数可以作为「一等公民」在常量池中存储。")

    H.para("以下是用 H# 编写的迷你字节码 VM,展示了栈机执行的核心原理:")

    H.code("""# 迷你字节码 VM 的 H# 实现
fn run_vm(instructions, consts) {
    let stack = [];
    let pc = 0;
    let env = {};

    while (pc < len(instructions)) {
        let instr = instructions[pc];
        let op = instr[0];
        let arg = instr[1];
        pc = pc + 1;

        if (op == "LOAD_CONST") {
            push(stack, consts[arg]);
        }
        if (op == "LOAD_NAME") {
            push(stack, env[arg]);
        }
        if (op == "STORE_NAME") {
            env[arg] = pop(stack);
        }
        if (op == "BINARY_ADD") {
            let b = pop(stack);
            let a = pop(stack);
            push(stack, a + b);
        }
        if (op == "BINARY_SUB") {
            let b = pop(stack);
            let a = pop(stack);
            push(stack, a - b);
        }
        if (op == "BINARY_MUL") {
            let b = pop(stack);
            let a = pop(stack);
            push(stack, a * b);
        }
        if (op == "PRINT") {
            print(pop(stack));
        }
        if (op == "HALT") {
            return nullptr;
        }
    }
}

# 字节码: let a = 10; let b = 20; print(a + b);
let instrs = [
    ["LOAD_CONST", 0],
    ["STORE_NAME", "a"],
    ["LOAD_CONST", 1],
    ["STORE_NAME", "b"],
    ["LOAD_NAME", "a"],
    ["LOAD_NAME", "b"],
    ["BINARY_ADD", nullptr],
    ["PRINT", nullptr],
    ["HALT", nullptr]
];
let consts = [10, 20];

run_vm(instrs, consts);

# 字节码: let x = 5; let y = 3; print(x * y);
let instrs2 = [
    ["LOAD_CONST", 0],
    ["STORE_NAME", "x"],
    ["LOAD_CONST", 1],
    ["STORE_NAME", "y"],
    ["LOAD_NAME", "x"],
    ["LOAD_NAME", "y"],
    ["BINARY_MUL", nullptr],
    ["PRINT", nullptr],
    ["HALT", nullptr]
];
let consts2 = [5, 3];

run_vm(instrs2, consts2);
""")

    H.output("""30
15""")

    H.para("这个迷你 VM 实现了 LOAD_CONST、LOAD_NAME、STORE_NAME、BINARY_ADD、BINARY_SUB、BINARY_MUL、PRINT 和 HALT 共8条指令。虽然简化,但它完整展示了栈式虚拟机的核心工作原理:指令驱动栈操作,运算通过弹栈-计算-压栈完成。")

    # ----------------------------------------------------------------
    H.h3("33.8 内联缓存优化")

    H.para("内联缓存(Inline Cache)是 H# 字节码 VM 的重要性能优化技术。它通过在指令位置缓存上次执行的类型信息,避免重复的属性查找和方法分派。")

    H.para("H# VM 实现了两类内联缓存:")

    H.bullet("LOAD_ATTR 缓存:记录上次属性查找的对象类 ID 和查找结果(直接字段/方法/类字段)。下次遇到同类对象时直接使用缓存结果,跳过完整的属性查找链。")
    H.bullet("CALL_METHOD 缓存:记录上次方法调用的类 ID 和方法字典引用。下次同类对象调用同名方法时,直接从缓存的方法字典中取,跳过类查找。")

    H.para("内联缓存是单态的(monomorphic):每个指令位置只缓存一种类型。当类型发生变化时(多态场景),缓存会失效并回退到慢路径。在 OOP 代码中,由于大多数调用点的接收者类型是固定的,单态内联缓存的命中率通常很高。")

    H.note("H# VM 还实现了小对象分配优化:通过对象池复用实例字典,减少内存分配次数。池大小上限为 256,超出后直接新建。此外,VM 运行期间会禁用 Python 的周期性 GC,依赖引用计数回收,消除全堆扫描造成的暂停。")

    H.para("以下代码展示了对象池和内联缓存的性能效果(通过大量方法调用体现):")

    H.code("""# 演示 OOP 性能(内联缓存生效)
class Point {
    let x = 0;
    let y = 0;

    fn init(x, y) {
        self.x = x;
        self.y = y;
    }

    fn distance_sq(other) {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        return dx * dx + dy * dy;
    }
}

let p1 = new Point(0, 0);
let p2 = new Point(3, 4);

# 大量方法调用 - 内联缓存优化生效
let t1 = time_now();
let i = 0;
let total = 0;
while (i < 10000) {
    total = total + p1.distance_sq(p2);
    i = i + 1;
}
let t2 = time_now();

print("Distance^2: " + str(p1.distance_sq(p2)));
print("Total: " + str(total));
print("Time: " + str(t2 - t1) + " ms");
""")

    H.output("""Distance^2: 25
Total: 250000
Time: 5 ms""")

    # ----------------------------------------------------------------
    H.h3("33.9 小结")

    H.number("H# 拥有双运行时架构:AST 解释器(开发)和字节码 VM(生产)。")
    H.number("字节码采用 JSON 容器格式,包含 instructions(指令流)和 consts(常量池)。")
    H.number(".hbc 文件是字节码的持久化存储,支持「一次编译,多处运行」。")
    H.number("核心指令集涵盖常量加载、变量操作、二元运算、控制流、函数调用和 OOP 等十大类。")
    H.number("编译流程为:源码 → 词法分析 → 语法分析 → AST → 字节码生成。")
    H.number("内联缓存和小对象池是 VM 的两大性能优化技术,显著加速 OOP 代码。")

    H.h3("33.10 练习")

    H.number("手动将以下 H# 代码翻译为字节码指令序列:let a = 10; let b = 20; print(a > b);")
    H.number("扩展本章的迷你 VM,增加 COMPARE_OP 指令支持,使其能执行比较运算。")
    H.number("使用 Python 的 compiler.py 编译一段包含 if 语句的 H# 代码,观察 JUMP_IF_FALSE 指令的跳转目标。")
    H.number("编写一个 H# 程序,用 time_now 测量 AST 解释器与字节码 VM 执行同一递归 Fibonacci(25) 的时间差异。")
    H.number("解释为什么内联缓存是「单态」的?在什么场景下缓存会频繁失效?如何改进?")

    H.page_break()

    # ================================================================
    # 第34章 Bootstrap 自举
    # ================================================================
    H.h2("第34章 Bootstrap 自举")

    H.para("自举(Bootstrapping)是编程语言发展史上的重要里程碑——用语言自身实现自身的工具链。C 语言用 C 编写编译器,Python 用 Python 编写解释器,H# 也不例外。本章将深入 H# 的 bootstrap 自举实现,展示如何用 H# 编写 H# 的词法分析器、语法分析器、编译器和虚拟机。")

    # ----------------------------------------------------------------
    H.h3("34.1 什么是自举")

    H.para("自举是指用一门编程语言自身来实现其编译器、解释器或开发工具链。自举的意义在于:")

    H.bullet("语言成熟度验证:能实现自身工具链,说明语言的表达能力已足够完备。")
    H.bullet("减少外部依赖:工具链不依赖其他语言,降低维护和移植成本。")
    H.bullet("自我进化能力:语言可以用自身来扩展自身,形成正反馈循环。")
    H.bullet("开发者体验:开发者只需掌握一门语言即可参与工具链开发。")

    H.para("H# 的自举目标是:用 H# 编写 H# 的 tokenizer(词法分析器)、parser(语法分析器)、compiler(编译器)和 interpreter(虚拟机),实现完整的「源码到执行」工具链。")

    # ----------------------------------------------------------------
    H.h3("34.2 Bootstrap 四阶段")

    H.para("H# 的 bootstrap 工具链分为四个阶段,对应四个核心模块:")

    H.number("tokenize.hto —— 词法分析:将 H# 源码字符串转换为 token 流(词法单元列表)。")
    H.number("parser.hto —— 语法分析:将 token 流解析为 AST(抽象语法树),以嵌套列表形式表示。")
    H.number("compiler.hto —— 编译器:将 AST 编译为字节码指令流(JSON 格式的 instructions + consts)。")
    H.number("interpreter.hto —— 虚拟机:加载字节码并执行,完成源码到结果的完整闭环。")

    H.para("这四个模块全部用 H# 编写,位于项目的 bootstrap/ 目录下。它们可以被 Python 解释器执行(第一阶段自举),也可以被 Kotlin HVM 执行(第二阶段自举)。")

    H.para("自举的「鸡生蛋」问题通过分阶段解决:首先用 Python 实现 H# 解释器(Python 能运行 H#),然后用 H# 编写 H# 工具链(此时由 Python 解释器执行),最后 H# 工具链可以自行执行 H# 代码,实现自循环。")

    # ----------------------------------------------------------------
    H.h3("34.3 tokenizer.hto 词法分析")

    H.para("词法分析器的任务是将源码字符串切分为有意义的词法单元(token)。每个 token 包含类型(type)和值(value)两个字段。例如,源码 let x = 42; 被切分为:LET、IDENT(x)、ASSIGN(=)、NUMBER(42)、SEMI(;)。")

    H.para("以下是 H# tokenizer 的简化实现,展示了词法分析的核心逻辑:")

    H.code("""# H# 词法分析器(简化版)
fn is_digit(ch) {
    return ch >= "0" and ch <= "9";
}

fn is_alpha(ch) {
    return (ch >= "a" and ch <= "z") or (ch >= "A" and ch <= "Z") or ch == "_";
}

fn is_alnum(ch) {
    return is_alpha(ch) or is_digit(ch);
}

fn tokenize(src) {
    let i = 0;
    let n = len(src);
    let tokens = [];

    while (i < n) {
        let ch = src[i];

        # 跳过空白字符
        if (ch == " " or ch == "\\t" or ch == "\\n" or ch == "\\r") {
            i = i + 1;
            continue;
        }

        # 跳过注释(# 到行尾)
        if (ch == "#") {
            while (i < n and src[i] != "\\n") {
                i = i + 1;
            }
            continue;
        }

        # 数字字面量
        if (is_digit(ch)) {
            let num = "";
            while (i < n and is_digit(src[i])) {
                num = num + src[i];
                i = i + 1;
            }
            push(tokens, {"type": "NUMBER", "value": num});
            continue;
        }

        # 标识符和关键字
        if (is_alpha(ch)) {
            let word = "";
            while (i < n and is_alnum(src[i])) {
                word = word + src[i];
                i = i + 1;
            }
            # 关键字识别
            if (word == "let") {
                push(tokens, {"type": "LET", "value": word});
            } else if (word == "print") {
                push(tokens, {"type": "PRINT", "value": word});
            } else if (word == "fn") {
                push(tokens, {"type": "FN", "value": word});
            } else if (word == "return") {
                push(tokens, {"type": "RETURN", "value": word});
            } else {
                push(tokens, {"type": "IDENT", "value": word});
            }
            continue;
        }

        # 运算符和标点
        if (ch == "=") {
            push(tokens, {"type": "ASSIGN", "value": "="});
            i = i + 1;
            continue;
        }
        if (ch == "+") {
            push(tokens, {"type": "PLUS", "value": "+"});
            i = i + 1;
            continue;
        }
        if (ch == ";") {
            push(tokens, {"type": "SEMI", "value": ";"});
            i = i + 1;
            continue;
        }
        if (ch == "(") {
            push(tokens, {"type": "LPAREN", "value": "("});
            i = i + 1;
            continue;
        }
        if (ch == ")") {
            push(tokens, {"type": "RPAREN", "value": ")"});
            i = i + 1;
            continue;
        }
        if (ch == "{") {
            push(tokens, {"type": "LBRACE", "value": "{"});
            i = i + 1;
            continue;
        }
        if (ch == "}") {
            push(tokens, {"type": "RBRACE", "value": "}"});
            i = i + 1;
            continue;
        }

        # 未知字符,跳过
        i = i + 1;
    }

    push(tokens, {"type": "EOF", "value": ""});
    return tokens;
}

# 测试词法分析器
let src = "let x = 42; print(x);";
let toks = tokenize(src);
let i = 0;
while (i < len(toks)) {
    let t = toks[i];
    print(t["type"] + ": " + t["value"]);
    i = i + 1;
}
""")

    H.output("""LET: let
IDENT: x
ASSIGN: =
NUMBER: 42
SEMI: ;
PRINT: print
LPAREN: (
IDENT: x
RPAREN: )
SEMI: ;
EOF:""")

    H.para("完整的 tokenize.hto 支持所有 H# 关键字(let、fn、if、else、while、for、class、return、true、false、nullptr 等)和所有运算符(+、-、*、/、%、==、!=、<、>、<=、>=、and、or、not 等),还支持字符串字面量和 ASM 内联汇编块。")

    # ----------------------------------------------------------------
    H.h3("34.4 parser.hto 语法分析")

    H.para("语法分析器接收 token 流,根据语法规则将其解析为 AST。H# 的 bootstrap parser 将 AST 表示为嵌套列表,例如 ['LetStatement', 'x', ['NumberLiteral', '42']] 表示 let x = 42。")

    H.para("parser 采用递归下降(Recursive Descent)策略,为每种语法结构实现一个解析函数:parse_statement、parse_expression、parse_let、parse_if、parse_while、parse_function 等。")

    H.para("以下是 parser 的核心结构示意:")

    H.code("""# H# 语法分析器结构(简化示意)
# parse(tokens) -> 返回 AST(嵌套列表)

# Token 流位置指针(全局状态)
let __pos = 0;
let __tokens = [];

fn parse(tokens) {
    __pos = 0;
    __tokens = tokens;
    let statements = [];

    # 循环解析每条语句
    while (peek_type() != "EOF") {
        push(statements, parse_statement());
    }
    return ["Program", statements];
}

fn peek_type() {
    if (__pos >= len(__tokens)) {
        return "EOF";
    }
    return __tokens[__pos]["type"];
}

fn advance() {
    __pos = __pos + 1;
    return nullptr;
}

fn parse_statement() {
    let t = peek_type();
    if (t == "LET") {
        return parse_let();
    }
    if (t == "PRINT") {
        return parse_print();
    }
    if (t == "FN") {
        return parse_function();
    }
    # ... 更多语句类型
    return ["Unknown"];
}

fn parse_let() {
    advance();  # 消费 LET
    let name = __tokens[__pos]["value"];
    advance();  # 消费标识符
    advance();  # 消费 ASSIGN
    let value = parse_expression();
    advance();  # 消费 SEMI
    return ["LetStatement", name, value];
}

fn parse_expression() {
    # 简化:直接返回字面量或标识符
    let t = peek_type();
    if (t == "NUMBER") {
        let val = __tokens[__pos]["value"];
        advance();
        return ["NumberLiteral", val];
    }
    if (t == "IDENT") {
        let val = __tokens[__pos]["value"];
        advance();
        return ["Identifier", val];
    }
    return ["Unknown"];
}
""")

    H.para("上述代码展示了递理下降解析器的核心模式:peek 查看当前 token 类型,advance 消费当前 token,parse_xxx 函数递归解析对应语法结构。完整的 parser.hto 支持所有 H# 语法:表达式优先级、函数定义、类定义、控制流、try/catch 等。")

    H.note("bootstrap parser 将 AST 表示为嵌套列表(如 [\"LetStatement\", \"x\", [\"NumberLiteral\", \"42\"]]),而非 Python 版 parser 使用的 AST 类对象。这种序列化友好格式使得 AST 可以直接通过 JSON 传输和存储。")

    # ----------------------------------------------------------------
    H.h3("34.5 compiler.hto 编译器")

    H.para("编译器接收 AST(嵌套列表),遍历每个节点,生成对应的字节码指令。编译器的核心是一个大的分发函数,根据节点类型选择对应的编译逻辑。")

    H.para("以下是编译器的核心结构示意:")

    H.code("""# H# 编译器结构(简化示意)
# compile(ast) -> {"instructions": [...], "consts": [...]}

fn add_const(consts, val) {
    let i = 0;
    while (i < len(consts)) {
        if (consts[i] == val) {
            return i;
        }
        i = i + 1;
    }
    push(consts, val);
    return len(consts) - 1;
}

fn emit(instrs, opname, arg) {
    push(instrs, [opname, arg]);
    return nullptr;
}

fn compile_expr(node, instrs, consts) {
    let t = node[0];

    if (t == "NumberLiteral") {
        let idx = add_const(consts, node[1]);
        emit(instrs, "LOAD_CONST", idx);
        return nullptr;
    }

    if (t == "StringLiteral") {
        let idx = add_const(consts, node[1]);
        emit(instrs, "LOAD_CONST", idx);
        return nullptr;
    }

    if (t == "Identifier") {
        emit(instrs, "LOAD_NAME", node[1]);
        return nullptr;
    }

    if (t == "BinaryOp") {
        compile_expr(node[2], instrs, consts);  # 左操作数
        compile_expr(node[3], instrs, consts);  # 右操作数
        let op = node[1];
        if (op == "+") {
            emit(instrs, "BINARY_ADD", nullptr);
        }
        if (op == "-") {
            emit(instrs, "BINARY_SUB", nullptr);
        }
        if (op == "*") {
            emit(instrs, "BINARY_MUL", nullptr);
        }
        return nullptr;
    }

    return nullptr;
}

fn compile_stmt(node, instrs, consts) {
    let t = node[0];

    if (t == "LetStatement") {
        compile_expr(node[2], instrs, consts);
        emit(instrs, "STORE_NAME", node[1]);
        return nullptr;
    }

    if (t == "PrintStatement") {
        compile_expr(node[1], instrs, consts);
        emit(instrs, "PRINT", nullptr);
        return nullptr;
    }

    return nullptr;
}

fn compile(program) {
    let instrs = [];
    let consts = [];
    let statements = program[1];
    let i = 0;
    while (i < len(statements)) {
        compile_stmt(statements[i], instrs, consts);
        i = i + 1;
    }
    emit(instrs, "HALT", nullptr);
    return {"instructions": instrs, "consts": consts};
}
""")

    H.para("编译器的核心模式是递归遍历:compile_stmt 处理语句节点,compile_expr 处理表达式节点。对于二元运算 BinaryOp,先递归编译左右操作数(后缀顺序),再发射对应的运算指令。常量通过 add_const 去重后存入常量池,指令通过 emit 追加到指令流。")

    # ----------------------------------------------------------------
    H.h3("34.6 interpreter.hto 虚拟机")

    H.para("bootstrap 虚拟机(interpreter.hto)接收编译器生成的字节码,通过栈式解释器执行。它是 H# 用 H# 实现的完整 VM,支持完整的指令集。")

    H.para("以下是 VM 的核心执行循环示意:")

    H.code("""# H# 字节码 VM 结构(简化示意)
# execute(bytecode, env) -> 执行字节码

fn execute(bytecode, env) {
    let instrs = bytecode["instructions"];
    let consts = bytecode["consts"];
    let stack = [];
    let pc = 0;

    while (pc < len(instrs)) {
        let instr = instrs[pc];
        let op = instr[0];
        let arg = instr[1];
        pc = pc + 1;

        # 常量与变量
        if (op == "LOAD_CONST") {
            push(stack, consts[arg]);
        }
        if (op == "LOAD_NAME") {
            push(stack, env[arg]);
        }
        if (op == "STORE_NAME") {
            env[arg] = pop(stack);
        }

        # 二元运算
        if (op == "BINARY_ADD") {
            let b = pop(stack);
            let a = pop(stack);
            push(stack, a + b);
        }
        if (op == "BINARY_SUB") {
            let b = pop(stack);
            let a = pop(stack);
            push(stack, a - b);
        }
        if (op == "BINARY_MUL") {
            let b = pop(stack);
            let a = pop(stack);
            push(stack, a * b);
        }

        # 控制流
        if (op == "JUMP") {
            pc = arg;
        }
        if (op == "JUMP_IF_FALSE") {
            let cond = pop(stack);
            if (cond == false) {
                pc = arg;
            }
        }

        # 输出与终止
        if (op == "PRINT") {
            print(pop(stack));
        }
        if (op == "HALT") {
            return nullptr;
        }
    }
    return nullptr;
}

# 测试:执行 let a = 10; let b = 20; print(a + b);
let bc = {
    "instructions": [
        ["LOAD_CONST", 0],
        ["STORE_NAME", "a"],
        ["LOAD_CONST", 1],
        ["STORE_NAME", "b"],
        ["LOAD_NAME", "a"],
        ["LOAD_NAME", "b"],
        ["BINARY_ADD", nullptr],
        ["PRINT", nullptr],
        ["HALT", nullptr]
    ],
    "consts": [10, 20]
};

execute(bc, {});
""")

    H.output("""30""")

    H.para("完整的 interpreter.hto 实现了全部 H# 指令集,包括函数调用(CALL_FUNCTION)、方法调用(CALL_METHOD)、类实例化(CALL_NEW)、异常处理(SETUP_EXCEPT/POP_EXCEPT/RAISE)、迭代器(FOR_ITER)等。它还支持闭包捕获、词法作用域查找和协程调度。")

    # ----------------------------------------------------------------
    H.h3("34.7 自举的意义与挑战")

    H.para("H# 实现自举有以下重要意义:")

    H.bullet("语言完备性验证:能实现自身的 tokenizer、parser、compiler 和 VM,证明 H# 的表达能力已足够完备,可以处理字符串、字典、列表、递归等复杂逻辑。")
    H.bullet("零外部依赖:bootstrap 工具链不依赖 Python 的任何库(仅依赖少量内置函数),理论上可以被任何 H# 运行时执行。")
    H.bullet("教学价值:bootstrap 模块是学习编译原理的最佳教材——完整的词法分析、语法分析、代码生成和虚拟机实现,全部用一门语言搞定。")
    H.bullet("自我进化:未来 H# 的新特性可以先用 H# 实现 bootstrap 版本,再同步到 Python/Kotlin 主实现。")

    H.para("自举过程中也面临诸多挑战:")

    H.bullet("性能瓶颈:H# 实现的工具链比 Python/Kotlin 实现慢,不适合作为生产编译器。解决方案是 bootstrap 仅用于验证和教学,生产使用 Python 编译器 + Kotlin HVM。")
    H.bullet("功能同步:bootstrap 模块需要与 Python 主实现保持语法兼容。当主实现新增语法时,bootstrap 需要同步更新。")
    H.bullet("引导问题:bootstrap 模块自身需要由 Python 解释器执行才能启动。真正的「自循环」(H# 工具链执行 H# 工具链)需要完整的字节码路径支持。")
    H.bullet("调试困难:当 bootstrap 模块出现 bug 时,调试链路较长(源码 → Python 解释器 → bootstrap 模块 → 错误)。")

    # ----------------------------------------------------------------
    H.h3("34.8 bootstrap 与主实现的差异")

    H.para("bootstrap 模块与 Python 主实现(lexer.py/parser.py/compiler.py/bytecode.py)有以下关键差异:")

    H.bullet("实现语言:bootstrap 用 H# 编写,主实现用 Python 编写。")
    H.bullet("AST 表示:bootstrap 使用嵌套列表(如 [\"NumberLiteral\", \"42\"]),主实现使用 AST 类对象(如 NumberLiteral(value=42))。")
    H.bullet("Token 表示:两者都使用字典 {\"type\": str, \"value\": val},保持兼容。")
    H.bullet("字节码格式:两者生成的字节码格式一致(均为 JSON 兼容的 instructions + consts),保证互操作。")
    H.bullet("性能:主实现(PyPy/CPython)比 bootstrap 快 10-100 倍,因为 Python 的字典/列表操作比 H# 快。")
    H.bullet("功能覆盖:主实现支持全部 H# 语法,bootstrap 仍在追赶部分高级特性(如泛型、模式匹配等 v0.4.1 新特性)。")

    H.para("下表演示了从源码到执行的完整 bootstrap 链路:")

    H.code("""# Bootstrap 完整链路演示
# 以下代码展示 tokenize -> parse -> compile -> execute 的完整流程

# 第一阶段:词法分析
fn is_digit(ch) {
    return ch >= "0" and ch <= "9";
}

fn is_alpha(ch) {
    return (ch >= "a" and ch <= "z") or (ch >= "A" and ch <= "Z") or ch == "_";
}

fn is_alnum(ch) {
    return is_alpha(ch) or is_digit(ch);
}

fn tokenize(src) {
    let i = 0;
    let n = len(src);
    let tokens = [];
    while (i < n) {
        let ch = src[i];
        if (ch == " " or ch == "\\t" or ch == "\\n") {
            i = i + 1;
            continue;
        }
        if (is_digit(ch)) {
            let num = "";
            while (i < n and is_digit(src[i])) {
                num = num + src[i];
                i = i + 1;
            }
            push(tokens, {"type": "NUMBER", "value": num});
            continue;
        }
        if (is_alpha(ch)) {
            let word = "";
            while (i < n and is_alnum(src[i])) {
                word = word + src[i];
                i = i + 1;
            }
            if (word == "let") {
                push(tokens, {"type": "LET", "value": word});
            } else if (word == "print") {
                push(tokens, {"type": "PRINT", "value": word});
            } else {
                push(tokens, {"type": "IDENT", "value": word});
            }
            continue;
        }
        if (ch == "=") {
            push(tokens, {"type": "ASSIGN", "value": "="});
            i = i + 1;
            continue;
        }
        if (ch == ";") {
            push(tokens, {"type": "SEMI", "value": ";"});
            i = i + 1;
            continue;
        }
        i = i + 1;
    }
    push(tokens, {"type": "EOF", "value": ""});
    return tokens;
}

# 第二阶段:语法分析(简化)
fn parse(tokens) {
    let pos = 0;
    let stmts = [];

    fn peek_type() {
        if (pos >= len(tokens)) { return "EOF"; }
        return tokens[pos]["type"];
    }

    fn advance() {
        pos = pos + 1;
        return nullptr;
    }

    while (peek_type() != "EOF") {
        if (peek_type() == "LET") {
            advance();
            let name = tokens[pos]["value"];
            advance();
            advance();  # ASSIGN
            let val = tokens[pos]["value"];
            advance();
            advance();  # SEMI
            push(stmts, ["Let", name, val]);
        } else if (peek_type() == "PRINT") {
            advance();
            let name = tokens[pos]["value"];
            advance();
            advance();  # SEMI
            push(stmts, ["Print", name]);
        } else {
            advance();
        }
    }
    return stmts;
}

# 第三阶段:编译(简化)
fn compile(ast) {
    let instrs = [];
    let consts = [];
    let i = 0;
    while (i < len(ast)) {
        let node = ast[i];
        if (node[0] == "Let") {
            let idx = len(consts);
            push(consts, node[2]);
            push(instrs, ["LOAD_CONST", idx]);
            push(instrs, ["STORE_NAME", node[1]]);
        }
        if (node[0] == "Print") {
            push(instrs, ["LOAD_NAME", node[1]]);
            push(instrs, ["PRINT", nullptr]);
        }
        i = i + 1;
    }
    push(instrs, ["HALT", nullptr]);
    return {"instructions": instrs, "consts": consts};
}

# 第四阶段:执行
fn execute(bc) {
    let instrs = bc["instructions"];
    let consts = bc["consts"];
    let stack = [];
    let env = {};
    let pc = 0;
    while (pc < len(instrs)) {
        let op = instrs[pc][0];
        let arg = instrs[pc][1];
        pc = pc + 1;
        if (op == "LOAD_CONST") {
            push(stack, consts[arg]);
        }
        if (op == "LOAD_NAME") {
            push(stack, env[arg]);
        }
        if (op == "STORE_NAME") {
            env[arg] = pop(stack);
        }
        if (op == "PRINT") {
            print(pop(stack));
        }
        if (op == "HALT") {
            return nullptr;
        }
    }
    return nullptr;
}

# 完整链路:源码 -> tokens -> AST -> bytecode -> 执行
let source = "let x = 42; print(x);";

print("=== Stage 1: Tokenize ===");
let toks = tokenize(source);
let i = 0;
while (i < len(toks)) {
    print(toks[i]["type"] + ": " + toks[i]["value"]);
    i = i + 1;
}

print("=== Stage 2: Parse ===");
let ast = parse(toks);
print(str(ast));

print("=== Stage 3: Compile ===");
let bc = compile(ast);
print(str(bc));

print("=== Stage 4: Execute ===");
execute(bc);
""")

    H.output("""=== Stage 1: Tokenize ===
LET: let
IDENT: x
ASSIGN: =
NUMBER: 42
SEMI: ;
PRINT: print
IDENT: x
SEMI: ;
EOF:
=== Stage 2: Parse ===
[['Let', 'x', '42'], ['Print', 'x']]
=== Stage 3: Compile ===
{'instructions': [['LOAD_CONST', 0], ['STORE_NAME', 'x'], ['LOAD_NAME', 'x'], ['PRINT', nullptr], ['HALT', nullptr]], 'consts': ['42']}
=== Stage 4: Execute ===
42""")

    H.warning("注意:简化版编译器将数字 42 作为字符串 「42」 存入常量池,执行时需要用 int() 转换。完整版 compiler.hto 通过 str_to_num 函数在编译期完成类型转换,确保常量池中的数字是正确的整数或浮点数类型。")

    # ----------------------------------------------------------------
    H.h3("34.9 小结")

    H.number("自举是用语言自身实现自身工具链的过程,是语言成熟度的重要标志。")
    H.number("H# bootstrap 分四阶段:tokenize(词法)→ parser(语法)→ compiler(编译)→ interpreter(执行)。")
    H.number("bootstrap 模块全部用 H# 编写,位于 bootstrap/ 目录,可被 Python 解释器或 Kotlin HVM 执行。")
    H.number("tokenizer 使用字符扫描法,识别关键字、标识符、数字、运算符等 token 类型。")
    H.number("parser 采用递归下降策略,将 token 流解析为嵌套列表形式的 AST。")
    H.number("compiler 递归遍历 AST,为每种节点生成对应的字节码指令。")
    H.number("interpreter 实现栈式 VM,逐条解释执行字节码指令。")
    H.number("bootstrap 与主实现的差异在于实现语言、AST 表示和性能,但字节码格式保持兼容。")

    H.h3("34.10 练习")

    H.number("扩展本章的 tokenizer,增加对字符串字面量(\"...\")的支持。提示:遇到引号时扫描到结束引号。")
    H.number("扩展本章的 parser,增加对 print(表达式) 的支持,使其能解析 print(x + 1) 这样的语句。")
    H.number("在迷你 VM 中增加 CALL_FUNCTION 指令支持,使其能执行函数调用。提示:函数对象存储在常量池中。")
    H.number("阅读 bootstrap/tokenize.hto 源码,找出它支持的所有关键字列表。")
    H.number("思考:为什么 bootstrap parser 使用嵌套列表而非类对象来表示 AST?这种设计有什么优缺点?")

    H.page_break()

    # ================================================================
    # 第35章 打包与发布
    # ================================================================
    H.h2("第35章 打包与发布")

    H.para("将 H# 代码从开发环境推向生产环境,需要经过编译、打包和部署三个环节。本章将介绍 H# 的打包流程、Kotlin HVM 部署、跨平台运行策略,以及从源码到部署的完整工作流。")

    # ----------------------------------------------------------------
    H.h3("35.1 hbc 打包流程")

    H.para("H# 的打包流程将 .hto 源码编译为 .hbc 字节码文件。.hbc 是标准 JSON 格式,包含指令流和常量池,可被 Python VM 或 Kotlin HVM 加载执行。")

    H.para("打包的命令行方式:")

    H.code("""# 编译单个文件为 .hbc
python3 hsharp.py --emit-bc hello.hto
# 输出: hello.hbc

# 编译并立即执行字节码
python3 hsharp.py --run-bc hello.hbc

# 编译多模块 bundle
python3 bootstrap/build_bundle.py
# 输出: hsharp_bundle.hbc(包含多个模块)
""")

    H.para("打包的 Python API 方式:")

    H.code("""# 通过 Python API 编译 H# 代码
import json
from lexer import Lexer
from parser import Parser
from compiler import Compiler

# 读取源码
with open("hello.hto", "r") as f:
    code = f.read()

# 编译
lexer = Lexer(code)
parser = Parser(lexer)
program = parser.parse()
compiler = Compiler()
bytecode = compiler.compile(program)

# 保存为 .hbc 文件(JSON 格式)
hbc = {
    "version": "v0.4",
    "modules": {
        "main": bytecode
    },
    "built_at": 1718889600
}

with open("hello.hbc", "w") as f:
    json.dump(hbc, f, indent=2)

print("Compiled to hello.hbc")
""")

    H.para(".hbc 文件的结构遵循 HBC 格式规范(详见第33章)。单模块文件的模块名为 main,多模块 bundle 则包含多个命名模块,如 main、hwdui、math_utils 等。")

    # ----------------------------------------------------------------
    H.h3("35.2 Kotlin HVM 部署")

    H.para("Kotlin HVM 是 H# v0.4.1 的生产主运行时。它是一个用 Kotlin 编写的栈式字节码解释器,位于 hsharp-kotlin-compiler/ 目录。HVM 加载 .hbc 文件并执行,无需 Python 环境。")

    H.para("HVM 的核心组件:")

    H.bullet("HbcReader.kt:读取 .hbc 文件,解析 JSON 格式的字节码容器。使用自研的 MiniJson 解析器,不依赖第三方 JSON 库。")
    H.bullet("HVM.kt:栈式虚拟机,执行字节码指令。支持主要指令子集,35/35 项测试全部通过。")
    H.bullet("标准库模块:内置 assert、path、regex、crypto 四个标准库模块,提供常用功能。")

    H.para("HVM 部署流程:")

    H.code("""# 1. 编译 H# 源码为 .hbc
python3 hsharp.py --emit-bc app.hto
# 生成 app.hbc

# 2. 用 Kotlin HVM 执行
java -jar hvm.jar app.hbc
# 或直接使用构建好的原生可执行文件
./hsharp-vm app.hbc

# 3. 多模块 bundle 执行
./hsharp-vm hsharp_bundle.hbc
""")

    H.note("HVM 的 For 循环跳转修正:Python 编译器发出的 for 循环回跳指令指向循环体起始,而非 FOR_ITER 指令。Kotlin HbcReader 在加载时自动将跳转目标回退 1,修正此 bug。Python VM 不需要此修正(兼容两种跳转模式)。")

    # ----------------------------------------------------------------
    H.h3("35.3 跨平台运行")

    H.para("H# 的跨平台能力源于其分层架构:")

    H.bullet("开发平台:Python AST 解释器(interpreter.py),在任何有 Python 3 的平台上运行,支持 macOS、Linux、Windows。")
    H.bullet("过渡平台:Python 字节码 VM(bytecode.py),同样跨平台,性能优于 AST 解释器。")
    H.bullet("生产平台:Kotlin HVM,编译为 JVM 字节码或原生可执行文件,支持任何有 JVM 或 Kotlin/Native 的平台。")

    H.para("跨平台开发工作流:")

    H.code("""# 跨平台开发工作流

# 1. 开发阶段:用 Python 解释器快速迭代
python3 interpreter.py my_app.hto

# 2. 测试阶段:编译为字节码并用 Python VM 测试
python3 hsharp.py --emit-bc my_app.hto
python3 hsharp.py --run-bc my_app.hbc

# 3. 生产阶段:用 Kotlin HVM 部署
#    - 将 .hbc 文件复制到目标平台
#    - 运行 ./hsharp-vm my_app.hbc
#    - 无需安装 Python,只需 JVM 或原生 HVM
""")

    H.para("H# 的 .hbc 文件是纯 JSON,可以在任何平台上生成并在任何其他平台上执行,实现真正的「一次编译,处处运行」。")

    # ----------------------------------------------------------------
    H.h3("35.4 项目组织结构")

    H.para("一个完整的 H# 项目通常包含以下结构:")

    H.code("""# H# 项目结构示例
my_project/
├── src/                    # 源码目录
│   ├── main.hto           # 主入口文件
│   ├── utils.hto          # 工具函数模块
│   ├── models.hto         # 数据模型
│   └── services.hto       # 业务逻辑
├── lib/                    # 标准库扩展
│   ├── string_utils.hto   # 字符串工具
│   ├── array_utils.hto    # 数组工具
│   └── math_utils.hto     # 数学工具
├── tests/                  # 测试目录
│   ├── test_main.hto      # 主测试
│   └── test_utils.hto     # 工具测试
├── dist/                   # 发布目录
│   ├── main.hbc           # 编译后的字节码
│   └── bundle.hbc         # 多模块打包
├── HSharp_v0.4_Package/   # H# 运行时
│   ├── interpreter.py     # Python 解释器
│   ├── bytecode.py        # Python VM
│   └── hsharp.py          # 编译器入口
└── README.md              # 项目说明
""")

    H.para("项目组织建议:")

    H.number("源码和发布产物分离:src/ 放源码,dist/ 放编译后的 .hbc 文件。")
    H.number("模块化设计:将不同功能拆分为独立的 .hto 文件,便于维护和复用。")
    H.number("标准库扩展:将通用工具函数放在 lib/ 目录,作为项目的标准库。")
    H.number("测试驱动:每个模块对应一个测试文件,放在 tests/ 目录。")
    H.number("运行时打包:将 H# 运行时(interpreter.py / hsharp-vm)随项目一起分发,确保目标环境可执行。")

    # ----------------------------------------------------------------
    H.h3("35.5 从源码到部署的完整流程")

    H.para("以下是一个完整的 H# 项目从源码编写到部署执行的实例:")

    H.code("""# 完整 H# 项目示例:任务管理器

# === 工具模块 ===
fn gen_id() {
    # 简单的 ID 生成器
    let t = time_now();
    return t % 100000;
}

# === 数据模型 ===
class Task {
    let id = 0;
    let title = "";
    let done = false;

    fn init(title) {
        self.id = gen_id();
        self.title = title;
        self.done = false;
    }

    fn complete() {
        self.done = true;
    }

    fn to_string() {
        let status = "[ ]";
        if (self.done) {
            status = "[x]";
        }
        return "#" + str(self.id) + " " + status + " " + self.title;
    }
}

# === 业务逻辑 ===
class TaskManager {
    let tasks = [];

    fn init() {
        self.tasks = [];
    }

    fn add(title) {
        let t = new Task(title);
        push(self.tasks, t);
        return t.id;
    }

    fn complete(id) {
        let i = 0;
        while (i < len(self.tasks)) {
            if (self.tasks[i].id == id) {
                self.tasks[i].complete();
                return true;
            }
            i = i + 1;
        }
        return false;
    }

    fn list_all() {
        let i = 0;
        while (i < len(self.tasks)) {
            print(self.tasks[i].to_string());
            i = i + 1;
        }
    }

    fn count_pending() {
        let count = 0;
        let i = 0;
        while (i < len(self.tasks)) {
            if (self.tasks[i].done == false) {
                count = count + 1;
            }
            i = i + 1;
        }
        return count;
    }
}

# === 主程序 ===
let mgr = new TaskManager();
let id1 = mgr.add("Learn H# standard library");
let id2 = mgr.add("Write bytecode compiler");
let id3 = mgr.add("Deploy to HVM");

print("=== All Tasks ===");
mgr.list_all();

mgr.complete(id1);

print("");
print("=== After Update ===");
mgr.list_all();

print("");
print("Pending: " + str(mgr.count_pending()));
""")

    H.output("""=== All Tasks ===
#<id> [ ] Learn H# standard library
#<id> [ ] Write bytecode compiler
#<id> [ ] Deploy to HVM

=== After Update ===
#<id> [x] Learn H# standard library
#<id> [ ] Write bytecode compiler
#<id> [ ] Deploy to HVM

Pending: 2""")

    H.note("上述输出中的 <id> 是动态生成的(基于 time_now),每次运行数值不同。重点是理解项目的组织结构:工具函数 → 数据模型 → 业务逻辑 → 主程序。")

    # ----------------------------------------------------------------
    H.h3("35.6 性能考虑")

    H.para("H# 的三套运行时在性能上有显著差异。选择合适的运行时是优化的第一步:")

    H.bullet("Python AST 解释器:最慢,但功能最全,适合开发和调试。执行速度约为 Python 的 1/5-1/10(因为 AST 遍历开销)。")
    H.bullet("Python 字节码 VM:中等,比 AST 解释器快 2-5 倍(得益于指令派发和内联缓存)。适合性能测试和过渡部署。")
    H.bullet("Kotlin HVM:最快,约为 Python VM 的 3-10 倍(得益于 Kotlin 的 JVM 优化和原生编译)。适合生产部署。")

    H.para("性能优化建议:")

    H.number("选择合适的运行时:开发用 AST 解释器,测试用 Python VM,生产用 Kotlin HVM。")
    H.number("利用内联缓存:在 OOP 密集的代码中,保持方法调用的接收者类型稳定,提高缓存命中率。")
    H.number("减少动态分配:重用对象和列表,避免频繁创建小对象。利用 VM 的对象池优化。")
    H.number("使用 Fast Locals:register_allocation.py 可将局部变量从字典查找优化为数组索引访问。")
    H.number("预编译为 .hbc:避免运行时编译开销,直接加载字节码执行。")
    H.number("批量处理:减少循环次数,增加每次迭代的工作量,降低指令派发开销。")

    H.para("以下代码展示了性能测量的标准模式:")

    H.code("""# 性能测量示例
let t1 = time_now();

# 被测代码:计算 Fibonacci 数列
fn fib(n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

let result = fib(25);
let t2 = time_now();

print("fib(25) = " + str(result));
print("Time: " + str(t2 - t1) + " ms");
""")

    H.output("""fib(25) = 75025
Time: 15 ms""")

    H.warning("性能数据因运行时和硬件而异。上述结果在 Python AST 解释器上约为 15ms;在 Python 字节码 VM 上约为 5ms;在 Kotlin HVM 上约为 2ms。实际数值请以本地测量为准。")

    # ----------------------------------------------------------------
    H.h3("35.7 实战:构建一个完整的 H# 项目")

    H.para("让我们构建一个完整的 H# 项目——一个简单的计算器应用,展示从源码到部署的全流程:")

    H.code("""# 完整项目:数学工具集

# === 数学函数库 ===
fn factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

fn fibonacci(n) {
    if (n <= 1) {
        return n;
    }
    let a = 0;
    let b = 1;
    let i = 2;
    while (i <= n) {
        let temp = a + b;
        a = b;
        b = temp;
        i = i + 1;
    }
    return b;
}

fn is_prime(n) {
    if (n < 2) {
        return false;
    }
    let i = 2;
    while (i * i <= n) {
        if (n % i == 0) {
            return false;
        }
        i = i + 1;
    }
    return true;
}

fn gcd(a, b) {
    while (b != 0) {
        let temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

# === 主程序 ===
print("=== Math Toolkit ===");
print("");

# 阶乘
print("Factorials:");
let i = 1;
while (i <= 6) {
    print("  " + str(i) + "! = " + str(factorial(i)));
    i = i + 1;
}

print("");

# 斐波那契
print("Fibonacci:");
i = 0;
while (i <= 10) {
    print("  fib(" + str(i) + ") = " + str(fibonacci(i)));
    i = i + 1;
}

print("");

# 素数检查
print("Prime check:");
print("  17 is prime: " + str(is_prime(17)));
print("  18 is prime: " + str(is_prime(18)));
print("  97 is prime: " + str(is_prime(97)));

print("");

# 最大公约数
print("GCD:");
print("  gcd(12, 8) = " + str(gcd(12, 8)));
print("  gcd(48, 36) = " + str(gcd(48, 36)));

print("");

# 素数列表
print("Primes up to 30:");
i = 2;
while (i <= 30) {
    if (is_prime(i)) {
        print("  " + str(i));
    }
    i = i + 1;
}
""")

    H.output("""=== Math Toolkit ===

Factorials:
  1! = 1
  2! = 2
  3! = 6
  4! = 24
  5! = 120
  6! = 720

Fibonacci:
  fib(0) = 0
  fib(1) = 1
  fib(2) = 1
  fib(3) = 2
  fib(4) = 3
  fib(5) = 5
  fib(6) = 8
  fib(7) = 13
  fib(8) = 21
  fib(9) = 34
  fib(10) = 55

Prime check:
  17 is prime: True
  18 is prime: False
  97 is prime: True

GCD:
  gcd(12, 8) = 4
  gcd(48, 36) = 12

Primes up to 30:
  2
  3
  5
  7
  11
  13
  17
  19
  23
  29""")

    H.para("这个项目展示了完整的 H# 应用开发模式:模块化的函数库、清晰的主程序结构、格式化的输出。将其编译为 .hbc 后,即可在任何 H# 运行时上部署执行。")

    # ----------------------------------------------------------------
    H.h3("35.8 小结")

    H.number("H# 打包流程:.hto 源码 → compiler.py 编译 → .hbc 字节码文件(JSON 格式)。")
    H.number("Kotlin HVM 是 v0.4.1 的生产主运行时,加载 .hbc 执行,无需 Python 环境。")
    H.number("三套运行时支持跨平台:Python 解释器(开发)、Python VM(测试)、Kotlin HVM(生产)。")
    H.number("项目结构建议:src/ 放源码,lib/ 放扩展库,tests/ 放测试,dist/ 放发布产物。")
    H.number("从源码到部署:编写 .hto → 用 interpreter.py 调试 → 编译为 .hbc → 用 HVM 部署。")
    H.number("性能优化:选择合适运行时、利用内联缓存、减少动态分配、预编译为 .hbc。")

    H.h3("35.9 练习")

    H.number("将第35.7节的数学工具集项目编译为 .hbc 文件,并用 Python VM 执行,验证输出一致。")
    H.number("为本章的任务管理器项目添加「删除任务」和「按标题搜索」功能。")
    H.number("编写一个 H# 项目,包含至少两个模块(如 math_utils.hto 和 string_utils.hto),用 build_bundle.py 打包为多模块 bundle。")
    H.number("用 time_now 测量递归 Fibonacci(20) 和迭代 Fibonacci(20) 的执行时间,比较性能差异。")
    H.number("设计一个完整的 H# 项目目录结构,包含 README 说明文件,描述如何编译、测试和部署。")

    H.page_break()

    # ================================================================
    # 附录
    # ================================================================
    H.h1("附录")

    H.para("本附录提供 H# 语言的快速参考材料,包括运算符优先级表、内置函数速查、关键字列表和 v0.4.1 特性总结。")

    # ----------------------------------------------------------------
    # 附录 A
    # ----------------------------------------------------------------
    H.h2("附录 A 运算符优先级表")

    H.para("H# 的运算符优先级从高到低排列如下(同一行的运算符优先级相同):")

    H.bullet("1. (最高) 括号 ()、索引 []、属性访问 .、函数调用 ()")
    H.bullet("2. 一元运算符: not、负号 -")
    H.bullet("3. 乘除模: *、/、%")
    H.bullet("4. 加减: +、-")
    H.bullet("5. 位运算: &、|、^、<<、>>")
    H.bullet("6. 比较运算: <、>、<=、>=")
    H.bullet("7. 相等比较: ==、!=")
    H.bullet("8. 逻辑与: and")
    H.bullet("9. 逻辑或: or")
    H.bullet("10. (最低) 赋值: =")

    H.para("运算符结合性说明:")

    H.bullet("赋值运算符 = 为右结合:a = b = c 等价于 a = (b = c)")
    H.bullet("二元运算符为左结合:a - b - c 等价于 (a - b) - c")
    H.bullet("一元运算符为右结合:not not a 等价于 not (not a)")
    H.bullet("比较运算不可链式:1 < x < 10 需写为 (1 < x) and (x < 10)")

    H.note("当不确定优先级时,建议使用括号明确表达式的求值顺序。这不仅避免错误,还提高代码可读性。")

    H.code("""# 运算符优先级示例
let a = 2 + 3 * 4;       # 14, 不是 20
let b = (2 + 3) * 4;     # 20
let c = 10 - 3 - 2;      # 5, 左结合
let d = not true or false;  # false, not 先于 or
let e = 1 < 2 and 3 > 2;    # true, 比较先于 and

print("a = " + str(a));
print("b = " + str(b));
print("c = " + str(c));
print("d = " + str(d));
print("e = " + str(e));
""")

    H.output("""a = 14
b = 20
c = 5
d = False
e = True""")

    # ----------------------------------------------------------------
    # 附录 B
    # ----------------------------------------------------------------
    H.h2("附录 B 内置函数速查")

    H.para("以下是 H# 所有内置函数的签名和简短说明,按功能分类列出。")

    H.h3("B.1 类型转换函数")

    H.bullet("int(x) —— 将 x 转换为整数。字符串先转 float 再取整。")
    H.bullet("float(x) —— 将 x 转换为浮点数。")
    H.bullet("str(x) —— 将 x 转换为字符串表示。")
    H.bullet("type(x) —— 返回 x 的类型名称字符串(int/float/string/bool/list/dict)。")

    H.h3("B.2 集合操作函数")

    H.bullet("len(obj) —— 返回列表/字符串/字典的元素个数。")
    H.bullet("push(lst, item) —— 向列表末尾追加元素,返回 null。")
    H.bullet("pop(lst) —— 弹出列表末尾元素并返回。")
    H.bullet("dict_keys(d) —— 返回字典所有键的列表。")
    H.bullet("dict_values(d) —— 返回字典所有值的列表。")
    H.bullet("dict_items(d) —— 返回字典所有键值对的列表(每对为 [key, value])。")
    H.bullet("has_key(d, k) —— 检查字典 d 是否包含键 k,返回布尔值。")
    H.bullet("range(n) —— 生成 [0, 1, ..., n-1] 的整数列表。")

    H.h3("B.3 字符串函数")

    H.bullet("substring(s, start, length) —— 从 s 的 start 位置提取长度为 length 的子串。")
    H.bullet("ord(ch) —— 返回字符 ch 的 ASCII/Unicode 码点(整数)。")
    H.bullet("chr(n) —— 将码点 n 转换为对应字符。")

    H.h3("B.4 IO 函数")

    H.bullet("read_file(path) —— 读取文本文件内容,返回字符串。")
    H.bullet("write_file(path, content) —— 将 content 写入文件(覆盖模式),返回 null。")

    H.h3("B.5 数学函数")

    H.bullet("abs(x) —— 返回 x 的绝对值。")
    H.bullet("min(lst) —— 返回列表中的最小值。")
    H.bullet("max(lst) —— 返回列表中的最大值。")

    H.h3("B.6 时间函数")

    H.bullet("time_now() —— 返回当前时间的 Unix 时间戳(毫秒,整数)。")

    H.h3("B.7 其他内置函数")

    H.bullet("thread_spawn(fn) —— 启动新线程执行函数 fn(并发编程)。")
    H.bullet("thread_join(t) —— 等待线程 t 完成。")

    H.note("在 Python AST 解释器中,type、abs、min、max、range、has_key 需要用户自行实现(参见第32章)。在 Python 字节码 VM 和 Kotlin HVM 中,这些函数均已内置。")

    H.para("此外,interpreter.py 还注册了大量扩展内置函数,包括:文件系统(fs_*)、网络(http_*/tcp_*/udp_*)、数据库(db_*)、日期(date_*)、数学扩展(math_sin/cos/sqrt 等)、哈希表(htable_*)和 GUI(hwdui_*)等。这些函数在 bootstrap 模块库中有对应的 H# 封装。")

    # ----------------------------------------------------------------
    # 附录 C
    # ----------------------------------------------------------------
    H.h2("附录 C 关键字列表")

    H.para("H# v0.4.1 的所有关键字如下表所示。关键字不能用作变量名、函数名或类名。")

    H.h3("C.1 声明与定义关键字")

    H.bullet("let —— 声明不可变变量")
    H.bullet("auto —— 自动类型推断声明")
    H.bullet("fn —— 声明函数")
    H.bullet("class —— 声明类")
    H.bullet("union —— 声明联合类型")
    H.bullet("interface —— 声明接口")
    H.bullet("concept —— 声明概念(类型约束)")
    H.bullet("module —— 声明模块")
    H.bullet("import —— 导入模块")

    H.h3("C.2 控制流关键字")

    H.bullet("if —— 条件语句")
    H.bullet("else —— 条件语句的分支")
    H.bullet("while —— while 循环")
    H.bullet("for —— for-in 循环")
    H.bullet("in —— for 循环的迭代关键字")
    H.bullet("break —— 跳出循环")
    H.bullet("continue —— 跳到下一次循环")
    H.bullet("return —— 从函数返回")

    H.h3("C.3 面向对象关键字")

    H.bullet("new —— 创建对象实例")
    H.bullet("extends —— 声明类继承")
    H.bullet("implements —— 声明接口实现")
    H.bullet("super —— 调用父类方法")
    H.bullet("is —— 类型检查(instanceof)")
    H.bullet("as —— 类型转换(cast)")
    H.bullet("static —— 声明静态成员")
    H.bullet("private —— 声明私有成员")
    H.bullet("public —— 声明公共成员")

    H.h3("C.4 异常处理关键字")

    H.bullet("try —— 开始异常捕获块")
    H.bullet("catch —— 捕获异常")
    H.bullet("throw —— 抛出异常")

    H.h3("C.5 布尔与空值关键字")

    H.bullet("true —— 布尔真")
    H.bullet("false —— 布尔假")
    H.bullet("nullptr —— 空值(null)")

    H.h3("C.6 逻辑运算关键字")

    H.bullet("and —— 逻辑与")
    H.bullet("or —— 逻辑或")
    H.bullet("not —— 逻辑非")

    H.h3("C.7 并发与高级关键字")

    H.bullet("async —— 声明异步函数")
    H.bullet("await —— 等待异步操作完成")
    H.bullet("parallel —— 声明并行函数")
    H.bullet("concurrent —— 声明结构化并发块")
    H.bullet("coro —— 声明协程")
    H.bullet("ptr —— 指针类型")
    H.bullet("asm —— 内联汇编")
    H.bullet("del —— 删除变量/属性")

    H.h3("C.8 特殊领域关键字")

    H.bullet("3dsizepower —— 声明 D3 尺寸力量类型")
    H.bullet("em3d —— 声明 EM3D 类型")
    H.bullet("region —— 声明区域")
    H.bullet("region_interface —— 声明区域接口")

    # ----------------------------------------------------------------
    # 附录 D
    # ----------------------------------------------------------------
    H.h2("附录 D H# v0.4.1 特性总结")

    H.para("H# v0.4.1 是 H# 语言的重要里程碑版本,于 2026 年 6 月发布。本附录总结 v0.4.1 的新特性、三套运行时对比和已知限制。")

    H.h3("D.1 v0.4.1 新特性列表")

    H.bullet("泛型支持:支持 <T> 泛型参数,可用于函数和类的类型参数化。")
    H.bullet("模式匹配:支持 match 表达式,包括通配符、绑定、字面量匹配、守卫条件等。")
    H.bullet("异步编程:支持 async/await 语法,实现基于协程的异步编程模型。")
    H.bullet("多线程并行:支持 @parallel fn 和 parallel fn 声明并行函数,配合 WorkerPool 实现线程池。")
    H.bullet("Channel 与结构化并发:支持 chan T 通道类型和 concurrent{} 结构化并发块。")
    H.bullet("错误传播:支持 ? 运算符,简化错误传播语法。")
    H.bullet("标准库模块:新增 assert、path、regex、crypto 四个标准库模块。")
    H.bullet("Raytracer 管线:实现光线追踪渲染管线,支持 3D 场景渲染。")
    H.bullet("Kotlin HVM:Kotlin HVM 栈机成为生产主运行时,替代 Python VM。")
    H.bullet("HBC 格式标准化:定义并实现了 .hbc 字节码容器格式规范(JSON 格式)。")

    H.h3("D.2 三套运行时对比表")

    H.para("H# v0.4.1 拥有三套运行时,各有不同的定位和特性:")

    H.bullet("Python AST 解释器(interpreter.py):开发调试用。直接遍历 AST 执行,功能最全,支持所有内置函数。性能最慢,约 Python 的 1/5-1/10。用于开发和快速迭代。")
    H.bullet("Python 字节码 VM(bytecode.py):性能过渡用。栈式 VM 执行字节码,支持内联缓存和 Fast Locals 优化。比 AST 解释器快 2-5 倍。用于性能测试和过渡部署。")
    H.bullet("Kotlin HVM(hsharp-kotlin-compiler/):生产主运行时。Kotlin 编写的栈式 VM,加载 .hbc 执行。性能最快,约为 Python VM 的 3-10 倍。无需 Python 环境,支持 JVM 和原生编译。用于生产部署。")

    H.para("三套运行时的特性对比:")

    H.bullet("语法支持:AST 解释器(100%) > Python VM(95%) > Kotlin HVM(主要子集,35/35 测试通过)")
    H.bullet("执行性能:Kotlin HVM > Python VM > AST 解释器")
    H.bullet("部署依赖:Kotlin HVM(JVM/原生) < Python VM(Python 3) < AST 解释器(Python 3)")
    H.bullet("调试体验:AST 解释器(最佳,直接执行源码) > Python VM(可读字节码) > Kotlin HVM(需日志)")
    H.bullet("跨平台:三套运行时均跨平台(macOS/Linux/Windows),.hbc 文件可在任意平台执行")

    H.h3("D.3 已知限制")

    H.para("H# v0.4.1 仍存在以下已知限制,将在后续版本中逐步解决:")

    H.number("AST 解释器功能不全:type、abs、min、max、range、has_key 等函数未内置,需用户自行实现。")
    H.number("整数除法:两整数相除为整数除法(截断),可能导致精度丢失。需用 float() 转换获得浮点结果。")
    H.number("字符串不可变性:字符串不支持原地修改,每次操作生成新字符串。大量字符串拼接性能较差。")
    H.number("列表方法有限:内置仅 push/pop,缺少 sort/reverse/map/filter 等函数(由 bootstrap 模块库提供)。")
    H.number("错误信息:部分错误信息不够详细,缺少行号和调用栈信息。")
    H.number("标准库覆盖:标准库仍在完善中,缺少正则表达式、JSON 解析等常用功能(部分由扩展函数提供)。")
    H.number("Kotlin HVM 指令覆盖:HVM 尚未实现全部指令,部分高级特性(如协程、D3 系统)需 Python 路径。")
    H.number("Bootstrap 同步:bootstrap 模块尚未同步 v0.4.1 的所有新特性(泛型、模式匹配等)。")
    H.number("调试器:尚未提供交互式调试器,调试依赖 print 和日志。")
    H.number("包管理器:尚未提供官方包管理器,模块分发依赖手动复制或 git。")

    H.para("尽管存在上述限制,H# v0.4.1 已具备完整的编程语言能力,支持从简单脚本到中大型项目的开发。随着社区的参与和版本的迭代,这些限制将逐步消除。")

    H.para("H# 的未来路线图包括:完整的 JIT 编译支持、原生代码生成、宏系统、更完善的类型系统、交互式调试器、官方包管理器等。敬请期待!")

    H.blank()
    H.para("—— 全书完 ——")
    H.para("感谢你阅读《H# 从入门到精通》。希望这本书能帮助你掌握 H# 语言,并用它创造出优秀的软件。Happy coding with H#!")
