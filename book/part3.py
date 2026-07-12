# -*- coding: utf-8 -*-
"""《H# 从入门到精通》第五篇 数据结构与算法(第18-22章)
所有代码示例均通过 python3 interpreter.py file.hto 实机测试。
"""


def add_content(doc, H):
    # ============================================================
    # 第五篇 数据结构与算法
    # ============================================================
    H.h1("第五篇 数据结构与算法")
    H.para(
        "数据结构与算法是编程的核心基石。本篇将深入讲解 H# 中的列表、字典、字符串三大内置数据结构,"
        "并在此基础上实现排序、查找、递归等经典算法,以及栈、队列、链表、二叉树、图等基础数据结构。"
        "通过本篇的学习,你将掌握用 H# 解决实际问题的能力,为后续的高级编程打下坚实基础。"
    )
    H.para(
        "本篇所有代码均在 Python 树遍历解释器(interpreter.py)下实机测试通过。"
        "由于 H# 解释器的布尔值输出为 Python 风格(True/False),空值输出为 None,"
        "本书输出示例均与实际运行结果保持一致。"
    )

    # ============================================================
    # 第18章 列表深入
    # ============================================================
    H.h2("第18章 列表深入")
    H.para(
        "列表(List)是 H# 中最常用的数据结构,它是一个有序的可变序列,可以存放任意类型的元素。"
        "列表用方括号 [] 创建,元素之间用逗号分隔。本章将从创建、访问、遍历到查找、修改、嵌套,"
        "全面讲解列表的操作方法。"
    )

    # --- 18.1 ---
    H.h3("18.1 列表创建与初始化")
    H.para("H# 提供多种方式创建列表:可以创建空列表,也可以在创建时直接初始化元素。")
    H.code("""# 创建空列表
let empty = [];
print(empty);

# 创建整数列表
let nums = [1, 2, 3, 4, 5];
print(nums);

# 创建字符串列表
let fruits = ["apple", "banana", "cherry"];
print(fruits);

# 创建混合类型列表
let mixed = [1, "hello", true, 3.14];
print(mixed);""")
    H.output("""[]
[1, 2, 3, 4, 5]
['apple', 'banana', 'cherry']
[1, 'hello', True, 3.14]""")
    H.note("H# 的列表可以存放不同类型的元素(混合类型),这在实际开发中非常灵活。")
    H.para(
        "从输出可以看到,布尔值 true 在 Python 解释器中显示为 True(Python 风格),"
        "浮点数 3.14 保持原样。空列表用 [] 表示。"
    )

    # --- 18.2 ---
    H.h3("18.2 索引访问(从0开始)")
    H.para(
        "H# 的列表索引从 0 开始,即第一个元素的索引为 0,第二个为 1,以此类推。"
        "通过 list[index] 语法可以访问指定位置的元素。"
    )
    H.code("""let colors = ["red", "green", "blue", "yellow"];
print(colors[0]);   # 第一个元素
print(colors[1]);   # 第二个元素
print(colors[2]);   # 第三个元素
print(colors[3]);   # 第四个元素""")
    H.output("""red
green
blue
yellow""")
    H.warning("访问不存在的索引会导致运行时错误。例如长度为 4 的列表,访问 colors[4] 会报错。请始终确保索引在 0 到 len(list)-1 的范围内。")
    H.para("H# 的列表不支持负数索引(如 colors[-1]),请使用 colors[len(colors) - 1] 来访问最后一个元素。")

    # --- 18.3 ---
    H.h3("18.3 len() 获取长度")
    H.para("len() 是 H# 最常用的内置函数之一,它可以获取列表、字符串和字典的长度。")
    H.code("""let arr = [10, 20, 30, 40, 50];
print(len(arr));      # 列表长度: 5

let s = "hello";
print(len(s));        # 字符串长度: 5

let d = {"a": 1, "b": 2, "c": 3};
print(len(d));        # 字典键值对数: 3""")
    H.output("""5
5
3""")
    H.para("len() 返回的是元素个数。对于列表,就是其中包含的元素数量;对于字符串,是字符数量;对于字典,是键值对的数量。")

    # --- 18.4 ---
    H.h3("18.4 push/pop 增删元素")
    H.para(
        "H# 通过内置函数 push() 和 pop() 来操作列表末尾的元素。"
        "push(list, item) 将元素添加到列表末尾,pop(list) 删除并返回列表末尾的元素。"
        "这两个操作是栈数据结构的基础(后进先出 LIFO)。"
    )
    H.code("""let stack = [];
push(stack, 1);          # 添加元素 1
push(stack, 2);          # 添加元素 2
push(stack, 3);          # 添加元素 3
print(stack);            # [1, 2, 3]
print(len(stack));       # 3

let last = pop(stack);   # 删除并返回末尾元素
print(last);             # 3
print(stack);            # [1, 2]

push(stack, 100);        # 再次添加
print(stack);            # [1, 2, 100]""")
    H.output("""[1, 2, 3]
3
3
[1, 2]
[1, 2, 100]""")
    H.note("push 和 pop 都操作列表的末尾。push 修改原列表并返回 None(不是新列表),pop 修改原列表并返回被删除的元素。")

    # --- 18.5 ---
    H.h3("18.5 遍历列表(for-in)")
    H.para("使用 for-in 循环可以方便地遍历列表中的每一个元素,这是处理列表最常用的方式。")
    H.code("""let animals = ["cat", "dog", "bird"];
for a in animals {
    print(a);
}""")
    H.output("""cat
dog
bird""")
    H.para("for-in 循环会依次将列表中的每个元素赋值给循环变量 a,然后执行循环体。遍历顺序与列表中元素的排列顺序一致。")

    H.para("如果需要在遍历时同时获取索引,可以使用 while 循环配合索引访问:")
    H.code("""let scores = [85, 90, 78, 92, 88];
let i = 0;
while (i < len(scores)) {
    print("Index " + i + ": " + scores[i]);
    i = i + 1;
}""")
    H.output("""Index 0: 85
Index 1: 90
Index 2: 78
Index 3: 92
Index 4: 88""")

    # --- 18.6 ---
    H.h3("18.6 列表查找(线性查找)")
    H.para("线性查找是最基本的查找算法:从头到尾依次比较每个元素,找到则返回索引,找不到返回 -1。")
    H.code("""fn linear_search(arr, target) {
    let i = 0;
    while (i < len(arr)) {
        if (arr[i] == target) {
            return i;
        }
        i = i + 1;
    }
    return -1;
}

let data = [10, 20, 30, 40, 50];
print(linear_search(data, 30));   # 找到,返回索引 2
print(linear_search(data, 99));   # 未找到,返回 -1""")
    H.output("""2
-1""")
    H.para("线性查找的时间复杂度为 O(n),适用于无序列表。对于有序列表,可以使用更高效的二分查找(见第21章)。")

    H.para("除了手动实现查找,H# 还支持用 in 运算符快速判断元素是否存在:")
    H.code("""let nums = [1, 2, 3, 4, 5];
print(3 in nums);    # True
print(9 in nums);    # False""")
    H.output("""True
False""")

    # --- 18.7 ---
    H.h3("18.7 列表修改")
    H.para("列表是可变的,可以通过索引直接修改指定位置的元素。")
    H.code("""let scores = [85, 90, 78, 92, 88];
print(scores);              # 原始列表

scores[2] = 95;             # 修改第三个元素
print(scores);              # 78 变为 95

scores[0] = scores[0] + 5;  # 第一个元素加 5
print(scores);              # 85 变为 90""")
    H.output("""[85, 90, 78, 92, 88]
[85, 90, 95, 92, 88]
[90, 90, 95, 92, 88]""")
    H.note("通过 list[index] = value 语法可以修改任意位置的元素。这是原地修改,不会创建新列表。")

    H.para("除了修改单个元素,还可以用 + 运算符拼接两个列表:")
    H.code("""let a = [1, 2, 3];
let b = [4, 5, 6];
let combined = a + b;
print(combined);       # [1, 2, 3, 4, 5, 6]
print(len(combined));  # 6""")
    H.output("""[1, 2, 3, 4, 5, 6]
6""")
    H.note("+ 运算符会创建一个新列表,原列表 a 和 b 不会被修改。")

    # --- 18.8 ---
    H.h3("18.8 嵌套列表(矩阵)")
    H.para(
        "列表中的元素也可以是列表,这就构成了嵌套列表(二维列表)。"
        "嵌套列表常用于表示矩阵、棋盘等二维数据结构。"
    )
    H.code("""let matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
];

# 访问单个元素: matrix[行][列]
print(matrix[0][0]);   # 第1行第1列: 1
print(matrix[1][2]);   # 第2行第3列: 6
print(matrix[2][1]);   # 第3行第2列: 8""")
    H.output("""1
6
8""")
    H.para("使用嵌套 while 循环可以遍历整个矩阵:")
    H.code("""let row = 0;
while (row < 3) {
    let col = 0;
    while (col < 3) {
        print(matrix[row][col]);
        col = col + 1;
    }
    row = row + 1;
}""")
    H.output("""1
2
3
4
5
6
7
8
9""")
    H.para("外层循环遍历行,内层循环遍历列。这种嵌套循环模式在处理二维数据时非常常见。")

    # --- 18.9 ---
    H.h3("18.9 列表与索引遍历")
    H.para(
        "虽然 H# 没有提供内置的 range() 函数来生成数字序列,"
        "但我们可以通过 while 循环配合索引变量来实现相同的效果。"
        "下面是一个计算列表所有元素之和的函数:"
    )
    H.code("""fn sum_list(arr) {
    let total = 0;
    let i = 0;
    while (i < len(arr)) {
        total = total + arr[i];
        i = i + 1;
    }
    return total;
}

let nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
print(sum_list(nums));   # 55""")
    H.output("55")
    H.para("使用 while 循环和索引变量是 H# 中遍历列表的通用方式,特别适合需要索引参与计算的场景。")

    H.para("另一个实用技巧:手动构建数字序列列表,然后遍历:")
    H.code("""# 手动构建 1 到 5 的序列
let seq = [];
let n = 1;
while (n <= 5) {
    push(seq, n);
    n = n + 1;
}
print(seq);   # [1, 2, 3, 4, 5]

# 计算平方
for x in seq {
    print(x * x);
}""")
    H.output("""[1, 2, 3, 4, 5]
1
4
9
16
25""")

    # --- 小结与练习 ---
    H.h3("本章小结")
    H.bullet("列表用 [] 创建,索引从 0 开始,支持混合类型元素")
    H.bullet("len() 获取长度,push() 添加元素,pop() 删除末尾元素")
    H.bullet("for-in 遍历元素,while + 索引遍历需要索引的场景")
    H.bullet("list[index] = value 修改元素,+ 运算符拼接列表")
    H.bullet("嵌套列表可以表示矩阵等二维数据")
    H.bullet("in 运算符可快速判断元素是否存在")

    H.h3("练习题")
    H.number("编写函数 find_max(arr),返回列表中的最大值。")
    H.number("编写函数 reverse_list(arr),返回反转后的新列表。")
    H.number("编写函数 count_val(arr, target),统计 target 在列表中出现的次数。")
    H.number("创建一个 3x3 的单位矩阵(对角线为 1,其余为 0),并打印。")
    H.number("编写函数 is_sorted(arr),判断列表是否已按升序排列。")

    H.page_break()

    # ============================================================
    # 第19章 字典深入
    # ============================================================
    H.h2("第19章 字典深入")
    H.para(
        "字典(Dictionary)是 H# 中的键值对集合,用花括号 {} 创建。"
        "字典通过键(Key)快速查找对应的值(Value),查找效率远高于列表的线性查找。"
        "字典是实现计数器、缓存、配置管理等功能的理想数据结构。"
    )

    # --- 19.1 ---
    H.h3("19.1 字典创建")
    H.para("字典用花括号 {} 创建,每个键值对用 key: value 表示,键值对之间用逗号分隔。")
    H.code("""# 创建空字典
let empty = {};
print(empty);

# 创建带初始值的字典
let person = {"name": "Alice", "age": 30, "city": "Beijing"};
print(person);""")
    H.output("""{}
{'name': 'Alice', 'age': 30, 'city': 'Beijing'}""")
    H.note("字典的键可以是字符串或数字,值可以是任意类型。同一个字典中每个键必须是唯一的。")

    H.para("字典也支持数字作为键:")
    H.code("""let d = {1: "one", 2: "two", 3: "three"};
print(d[1]);   # one
print(d[2]);   # two""")
    H.output("""one
two""")

    # --- 19.2 ---
    H.h3("19.2 增删改查")
    H.para("字典支持完整的增删改查操作(CRUD):添加新键值对、读取值、修改值、删除键值对。")
    H.code("""let scores = {"Alice": 90, "Bob": 85};
print(scores);

# 增:添加新键值对
scores["Carol"] = 92;
print(scores);

# 改:修改已有键的值
scores["Bob"] = 88;
print(scores);

# 查:通过键读取值
print(scores["Alice"]);   # 90

# 删:用 dict_pop 删除键值对
let removed = dict_pop(scores, "Bob");
print(removed);           # 88(被删除的值)
print(scores);            # Bob 已被删除""")
    H.output("""{'Alice': 90, 'Bob': 85}
{'Alice': 90, 'Bob': 85, 'Carol': 92}
{'Alice': 90, 'Bob': 88, 'Carol': 92}
90
88
{'Alice': 90, 'Carol': 92}""")
    H.note("dict_pop(d, key) 删除指定键值对并返回对应的值。如果键不存在则返回 None。")

    # --- 19.3 ---
    H.h3("19.3 dict_keys/dict_values/dict_items")
    H.para("H# 提供三个内置函数来获取字典的键、值和键值对列表:")
    H.code("""let prices = {"apple": 5, "banana": 3, "cherry": 8};

# 获取所有键
print(dict_keys(prices));

# 获取所有值
print(dict_values(prices));

# 获取所有键值对(每个键值对是一个 [key, value] 列表)
print(dict_items(prices));""")
    H.output("""['apple', 'banana', 'cherry']
[5, 3, 8]
[['apple', 5], ['banana', 3], ['cherry', 8]]""")
    H.para("这三个函数返回的都是列表,可以直接用 for-in 循环遍历。dict_items 返回的每个元素是一个包含两个元素的列表 [key, value]。")

    # --- 19.4 ---
    H.h3("19.4 遍历字典")
    H.para("使用 for k, v in dict 语法可以同时遍历字典的键和值,这是最常用的字典遍历方式。")
    H.code("""let students = {"Alice": 90, "Bob": 85, "Carol": 92};
for name, score in students {
    print(name + ": " + score);
}""")
    H.output("""Alice: 90
Bob: 85
Carol: 92""")
    H.para("for name, score in students 会将每个键赋给 name,对应的值赋给 score。遍历顺序与字典内部存储顺序一致。")

    H.para("如果只需要遍历键或值,可以使用 dict_keys 或 dict_values:")
    H.code("""let config = {"host": "localhost", "port": 8080, "debug": true};

# 只遍历键
for key in dict_keys(config) {
    print("Key: " + key);
}

# 只遍历值
for val in dict_values(config) {
    print("Value: " + val);
}""")
    H.output("""Key: host
Key: port
Key: debug
Value: localhost
Value: 8080
Value: True""")

    # --- 19.5 ---
    H.h3("19.5 判断键是否存在")
    H.para("在访问字典前,通常需要先判断键是否存在,避免出错。H# 提供两种方式判断键是否存在。")
    H.code("""let config = {"host": "localhost", "port": 8080};

# 方式一:用 in 运算符(推荐)
print("host" in config);    # True
print("user" in config);    # False

# 方式二:用 dict_has 函数
print(dict_has(config, "port"));   # True""")
    H.output("""True
False
True""")
    H.para("in 运算符语法简洁,推荐使用。dict_has 函数功能相同,适合需要函数式风格的场景。")

    H.para("结合 if 判断,可以安全地访问字典:")
    H.code("""let user = {"name": "Alice", "age": 30};

if ("email" in user) {
    print(user["email"]);
} else {
    print("email not set");
}""")
    H.output("email not set")

    # --- 19.6 ---
    H.h3("19.6 嵌套字典")
    H.para("字典的值可以是任意类型,包括另一个字典或列表。嵌套字典常用于表示复杂的数据结构。")
    H.code("""let company = {
    "name": "TechCorp",
    "info": {"founded": 2010, "employees": 50},
    "tags": ["tech", "software"]
};

print(company["name"]);                   # TechCorp
print(company["info"]["founded"]);        # 2010
print(company["info"]["employees"]);      # 50
print(company["tags"][0]);                # tech
print(company["tags"][1]);                # software""")
    H.output("""TechCorp
2010
50
tech
software""")
    H.para("通过连续使用 [] 运算符,可以访问任意层级的嵌套数据:company['info']['founded'] 先获取 info 字典,再获取其中的 founded 值。")

    # --- 19.7 ---
    H.h3("19.7 字典作为计数器")
    H.para(
        "字典最经典的应用之一是作为计数器:统计每个元素出现的次数。"
        "下面实现一个字符频率统计函数,它是字典计数器的典型应用。"
    )
    H.code("""fn count_chars(s) {
    let counts = {};
    for ch in s {
        if (ch in counts) {
            counts[ch] = counts[ch] + 1;
        } else {
            counts[ch] = 1;
        }
    }
    return counts;
}

let result = count_chars("hello");
print(result);
for ch, n in result {
    print(ch + " -> " + n);
}""")
    H.output("""{'h': 1, 'e': 1, 'l': 2, 'o': 1}
h -> 1
e -> 1
l -> 2
o -> 1""")
    H.para(
        "算法思路:遍历字符串的每个字符,如果字符已在字典中(之前出现过),则计数加 1;"
        "否则将该字符加入字典,初始计数为 1。最终字典中每个键值对表示字符及其出现次数。"
    )

    # --- 19.8 ---
    H.h3("19.8 字典与列表转换")
    H.para("通过 dict_keys 和 dict_values 可以将字典的键和值分别提取为列表,这在数据分析中非常实用。")
    H.code("""let word_count = {"a": 1, "b": 2, "c": 3};

let keys = dict_keys(word_count);
let values = dict_values(word_count);
print(keys);
print(values);

# 计算所有值的总和
let total = 0;
for v in values {
    total = total + v;
}
print(total);   # 6""")
    H.output("""['a', 'b', 'c']
[1, 2, 3]
6""")

    H.para("反向操作:从两个平行列表(键列表和值列表)构建字典:")
    H.code("""let names = ["x", "y", "z"];
let vals = [10, 20, 30];

let built = {};
let i = 0;
while (i < len(names)) {
    built[names[i]] = vals[i];
    i = i + 1;
}
print(built);""")
    H.output("{'x': 10, 'y': 20, 'z': 30}")
    H.para("通过 while 循环遍历索引,将 names[i] 作为键、vals[i] 作为值逐个添加到字典中。")

    # --- 小结与练习 ---
    H.h3("本章小结")
    H.bullet("字典用 {} 创建,键值对用 key: value 表示,键必须唯一")
    H.bullet("d[key] 读取/修改值,d[key] = value 添加/修改,dict_pop(d, key) 删除")
    H.bullet("dict_keys/dict_values/dict_items 获取键、值、键值对列表")
    H.bullet("for k, v in dict 同时遍历键和值")
    H.bullet("in 运算符或 dict_has 函数判断键是否存在")
    H.bullet("字典可作为计数器,统计元素出现频率")

    H.h3("练习题")
    H.number("编写函数 word_count(s),统计字符串中每个单词的出现次数(空格分隔)。")
    H.number("编写函数 merge_dict(d1, d2),将 d2 合并到 d1 中(d2 的键覆盖 d1)。")
    H.number("创建一个嵌套字典表示三个学生的成绩(数学、语文、英语),并打印每个学生的总分。")
    H.number("编写函数 dict_max(d),返回字典中值最大的键。")
    H.number("将列表 ['a', 'b', 'a', 'c', 'b', 'a'] 转为计数器字典并打印。")

    H.page_break()

    # ============================================================
    # 第20章 字符串处理进阶
    # ============================================================
    H.h2("第20章 字符串处理进阶")
    H.para(
        "字符串是编程中最常用的数据类型之一。H# 提供了 substring、ord、chr 等内置函数来处理字符串,"
        "但更复杂的操作(如查找、替换、分割)需要手动实现。本章将深入讲解字符串的各种操作,"
        "并实现常用的字符串处理算法。"
    )

    # --- 20.1 ---
    H.h3("20.1 substring(s, start, length) 详解")
    H.para(
        "substring 是 H# 中最核心的字符串函数。它的签名是 substring(s, start, length),"
        "从字符串 s 的 start 位置开始,截取长度为 length 的子字符串。"
    )
    H.warning("注意:substring 的第三个参数是长度(length),不是结束索引(end)!这与某些语言的 substring(s, start, end) 不同。")
    H.code("""let s = "Hello, World!";

# 从位置 0 开始截取 5 个字符
print(substring(s, 0, 5));    # Hello

# 从位置 7 开始截取 5 个字符
print(substring(s, 7, 5));    # World

# 截取单个字符(长度为 1)
print(substring(s, 0, 1));    # H
print(substring(s, 7, 1));    # W

# 将截取结果赋值给变量
let name = substring(s, 7, 5);
print(name);                  # World""")
    H.output("""Hello
World
H
W
World""")
    H.para("substring(s, start, length) 等价于取 s[start] 到 s[start+length-1] 的字符。如果 start+length 超过字符串长度,会自动截取到字符串末尾。")

    # --- 20.2 ---
    H.h3("20.2 ord(s) 与 chr(n) 字符编码")
    H.para(
        "ord(s) 返回单个字符的 ASCII/Unicode 编码值(整数),chr(n) 将编码值转回字符。"
        "这两个函数互为逆操作,常用于字符大小写转换、加密等场景。"
    )
    H.code("""print(ord("A"));    # 65
print(ord("a"));    # 97
print(ord("0"));    # 48
print(chr(65));     # A
print(chr(97));     # a
print(chr(48));     # 0""")
    H.output("""65
97
48
A
a
0""")
    H.para("ASCII 编码中,大写字母 A-Z 对应 65-90,小写字母 a-z 对应 97-122,数字 0-9 对应 48-57。利用这个规律可以实现大小写转换:")
    H.code("""fn to_upper(ch) {
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

print(to_upper("a"));   # A
print(to_lower("Z"));   # z""")
    H.output("""A
z""")
    H.note("大小写字母的 ASCII 码差值恰好是 32。大写转小写加 32,小写转大写减 32。")

    # --- 20.3 ---
    H.h3("20.3 字符串遍历(按字符)")
    H.para("H# 的 for-in 循环可以直接遍历字符串,每次迭代获取一个字符。")
    H.code("""let word = "Hello";
for ch in word {
    print(ch);
}""")
    H.output("""H
e
l
l
o""")
    H.para("也可以使用 while 循环配合 substring 按索引遍历,这种方式在需要索引参与计算时更灵活:")
    H.code("""let s = "abc";
let i = 0;
while (i < len(s)) {
    print(substring(s, i, 1));
    i = i + 1;
}""")
    H.output("""a
b
c""")

    # --- 20.4 ---
    H.h3("20.4 字符串查找")
    H.para("H# 没有内置的字符串查找函数,但我们可以手动实现。下面是一个朴素的字符串查找算法,返回子串首次出现的位置。")
    H.code("""fn str_find(s, target) {
    let n = len(s);
    let m = len(target);
    let i = 0;
    while (i <= n - m) {
        let matched = true;
        let j = 0;
        while (j < m) {
            if (substring(s, i + j, 1) != substring(target, j, 1)) {
                matched = false;
            }
            j = j + 1;
        }
        if (matched) {
            return i;
        }
        i = i + 1;
    }
    return -1;
}

print(str_find("Hello, World!", "World"));   # 7
print(str_find("Hello, World!", "xyz"));     # -1
print(str_find("aaa", "a"));                 # 0""")
    H.output("""7
-1
0""")
    H.para(
        "算法思路:从位置 0 开始,尝试在 s 的每个位置匹配 target。"
        "如果所有字符都匹配,返回当前位置;如果遍历完所有位置都没找到,返回 -1。"
        "这就是经典的朴素字符串匹配算法,时间复杂度为 O(n*m)。"
    )

    # --- 20.5 ---
    H.h3("20.5 字符串替换(手动实现)")
    H.para("字符串替换是常见操作:将字符串中的某个子串替换为另一个子串。下面手动实现 str_replace 函数。")
    H.code("""fn str_replace(s, old_str, new_str) {
    let result = "";
    let n = len(s);
    let m = len(old_str);
    let i = 0;
    while (i < n) {
        let matched = true;
        if (i <= n - m) {
            let j = 0;
            while (j < m) {
                if (substring(s, i + j, 1) != substring(old_str, j, 1)) {
                    matched = false;
                }
                j = j + 1;
            }
        } else {
            matched = false;
        }
        if (matched) {
            result = result + new_str;
            i = i + m;
        } else {
            result = result + substring(s, i, 1);
            i = i + 1;
        }
    }
    return result;
}

print(str_replace("Hello, World!", "World", "H#"));   # Hello, H#!
print(str_replace("aaa", "a", "b"));                   # bbb
print(str_replace("abc", "x", "y"));                   # abc(无匹配)""")
    H.output("""Hello, H#!
bbb
abc""")
    H.para(
        "算法思路:遍历字符串 s 的每个位置,检查从该位置开始是否匹配 old_str。"
        "如果匹配,将 new_str 追加到结果中,并跳过 old_str 的长度;"
        "如果不匹配,将当前字符追加到结果中,前进一个位置。"
    )

    # --- 20.6 ---
    H.h3("20.6 字符串分割(手动实现)")
    H.para("字符串分割将一个字符串按分隔符切分成多个子串,返回子串列表。下面手动实现 str_split 函数。")
    H.code("""fn str_split(s, delim) {
    let result = [];
    let current = "";
    let n = len(s);
    let m = len(delim);
    let i = 0;
    while (i < n) {
        let matched = true;
        if (i <= n - m) {
            let j = 0;
            while (j < m) {
                if (substring(s, i + j, 1) != substring(delim, j, 1)) {
                    matched = false;
                }
                j = j + 1;
            }
        } else {
            matched = false;
        }
        if (matched) {
            push(result, current);
            current = "";
            i = i + m;
        } else {
            current = current + substring(s, i, 1);
            i = i + 1;
        }
    }
    push(result, current);
    return result;
}

let parts = str_split("a,b,c,d", ",");
print(parts);                          # ['a', 'b', 'c', 'd']

let parts2 = str_split("Hello World H#", " ");
print(parts2);                         # ['Hello', 'World', 'H#']""")
    H.output("""['a', 'b', 'c', 'd']
['Hello', 'World', 'H#']""")
    H.note("str_split 的核心思路与 str_replace 类似:遍历字符串,遇到分隔符时将已收集的字符作为一个子串存入结果列表,然后跳过分隔符继续处理。")

    # --- 20.7 ---
    H.h3("20.7 字符串拼接")
    H.para("字符串拼接用 + 运算符即可。遍历列表并用 + 拼接所有元素,可以实现 join 功能。")
    H.code("""# 简单拼接
let words = ["Hello", ", ", "World", "!"];
let sentence = "";
for w in words {
    sentence = sentence + w;
}
print(sentence);   # Hello, World!""")
    H.output("Hello, World!")

    H.para("实现 join 函数:用分隔符将列表中的字符串连接成一个字符串。")
    H.code("""fn join(lst, sep) {
    let result = "";
    let i = 0;
    while (i < len(lst)) {
        if (i > 0) {
            result = result + sep;
        }
        result = result + lst[i];
        i = i + 1;
    }
    return result;
}

print(join(["apple", "banana", "cherry"], ", "));
# apple, banana, cherry""")
    H.output("apple, banana, cherry")
    H.para("join 函数在拼接时,除第一个元素外,每个元素前都加上分隔符 sep。")

    # --- 20.8 ---
    H.h3("20.8 实战:统计字符频率")
    H.para(
        "综合运用本章学到的字符串遍历和字典计数,实现一个字符频率统计函数。"
        "这个函数统计字符串中每个字符出现的次数,是文本分析的基础。"
    )
    H.code("""fn char_freq(s) {
    let counts = {};
    for ch in s {
        if (ch in counts) {
            counts[ch] = counts[ch] + 1;
        } else {
            counts[ch] = 1;
        }
    }
    return counts;
}

let freq = char_freq("programming");
print(freq);
for ch, n in freq {
    print(ch + ": " + n);
}""")
    H.output("""{'p': 1, 'r': 2, 'o': 1, 'g': 2, 'a': 1, 'm': 2, 'i': 1, 'n': 1}
p: 1
r: 2
o: 1
g: 2
a: 1
m: 2
i: 1
n: 1""")
    H.para("从输出可以看到,'programming' 中 r、g、m 各出现 2 次,其余字符各出现 1 次。这个函数在密码分析、文本压缩等领域有广泛应用。")

    # --- 小结与练习 ---
    H.h3("本章小结")
    H.bullet("substring(s, start, length) 截取子串,第三个参数是长度不是结束索引")
    H.bullet("ord(s) 获取字符编码,chr(n) 将编码转为字符,互为逆操作")
    H.bullet("for-in 直接遍历字符串的每个字符")
    H.bullet("字符串查找、替换、分割均可通过 while 循环和 substring 手动实现")
    H.bullet("+ 运算符拼接字符串,可封装为 join 函数")
    H.bullet("字典 + 字符串遍历 = 字符频率统计")

    H.h3("练习题")
    H.number("编写函数 to_uppercase(s),将字符串中所有小写字母转为大写。")
    H.number("编写函数 str_reverse(s),返回反转后的字符串(如 'abc' 返回 'cba')。")
    H.number("编写函数 is_palindrome(s),判断字符串是否为回文(正读反读相同)。")
    H.number("编写函数 count_words(s),统计字符串中的单词数(空格分隔)。")
    H.number("编写函数 str_trim(s),去除字符串首尾的空格。")

    H.page_break()

    # ============================================================
    # 第21章 常用算法
    # ============================================================
    H.h2("第21章 常用算法")
    H.para(
        "算法是解决问题的步骤和方法。本章将实现三种经典排序算法(冒泡、选择、插入),"
        "两种查找算法(线性、二分),以及递归算法(阶乘、斐波那契、汉诺塔)。"
        "这些算法是计算机科学的基础,也是面试和竞赛的常考内容。"
    )

    # --- 21.1 ---
    H.h3("21.1 冒泡排序")
    H.para(
        "冒泡排序是最简单的排序算法。它重复地遍历列表,比较相邻的两个元素,"
        "如果顺序错误就交换它们。每轮遍历会将最大的元素'冒泡'到末尾。"
    )
    H.code("""fn bubble_sort(arr) {
    let n = len(arr);
    let i = 0;
    while (i < n) {
        let j = 0;
        while (j < n - i - 1) {
            if (arr[j] > arr[j + 1]) {
                # 交换相邻元素
                let temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
            j = j + 1;
        }
        i = i + 1;
    }
    return arr;
}

let nums = [64, 34, 25, 12, 22, 11, 90];
print(bubble_sort(nums));""")
    H.output("[11, 12, 22, 25, 34, 64, 90]")
    H.para(
        "外层循环 i 控制排序轮数(共 n 轮),内层循环 j 比较相邻元素。"
        "每轮结束后,最大的元素已到达正确位置,所以内层循环的上界是 n - i - 1(已排序部分无需再比较)。"
    )
    H.note("冒泡排序的时间复杂度为 O(n^2),空间复杂度为 O(1)(原地排序)。适合小规模数据或教学演示。")

    # --- 21.2 ---
    H.h3("21.2 选择排序")
    H.para(
        "选择排序的思路是:每轮从未排序部分找出最小值,与未排序部分的第一个元素交换。"
        "这样每轮确定一个最小元素的位置。"
    )
    H.code("""fn selection_sort(arr) {
    let n = len(arr);
    let i = 0;
    while (i < n - 1) {
        # 找未排序部分最小值的索引
        let min_idx = i;
        let j = i + 1;
        while (j < n) {
            if (arr[j] < arr[min_idx]) {
                min_idx = j;
            }
            j = j + 1;
        }
        # 将最小值交换到位置 i
        let temp = arr[i];
        arr[i] = arr[min_idx];
        arr[min_idx] = temp;
        i = i + 1;
    }
    return arr;
}

let nums = [29, 10, 14, 37, 13];
print(selection_sort(nums));""")
    H.output("[10, 13, 14, 29, 37]")
    H.para("选择排序的交换次数少于冒泡排序(每轮最多交换一次),但比较次数相同,时间复杂度仍为 O(n^2)。")

    # --- 21.3 ---
    H.h3("21.3 插入排序")
    H.para(
        "插入排序类似于整理扑克牌:将每个元素插入到已排序部分的正确位置。"
        "从第二个元素开始,将其与前面的元素比较,找到合适的位置插入。"
    )
    H.code("""fn insertion_sort(arr) {
    let n = len(arr);
    let i = 1;
    while (i < n) {
        let key = arr[i];
        let j = i - 1;
        # 将比 key 大的元素向后移动
        while (j >= 0 and arr[j] > key) {
            arr[j + 1] = arr[j];
            j = j - 1;
        }
        arr[j + 1] = key;
        i = i + 1;
    }
    return arr;
}

let nums = [12, 11, 13, 5, 6];
print(insertion_sort(nums));""")
    H.output("[5, 6, 11, 12, 13]")
    H.note("插入排序在数据基本有序时效率很高,最佳情况时间复杂度为 O(n)。它也是希尔排序的基础。")

    # --- 21.4 ---
    H.h3("21.4 线性查找")
    H.para("线性查找从头到尾依次比较,适用于无序列表。这是最简单直接的查找方法。")
    H.code("""fn linear_search(arr, target) {
    let i = 0;
    while (i < len(arr)) {
        if (arr[i] == target) {
            return i;
        }
        i = i + 1;
    }
    return -1;
}

let data = [10, 23, 45, 70, 11, 15];
print(linear_search(data, 70));    # 3
print(linear_search(data, 99));    # -1""")
    H.output("""3
-1""")
    H.para("找到目标返回其索引,找不到返回 -1。时间复杂度 O(n),适合小规模或无序数据。")

    # --- 21.5 ---
    H.h3("21.5 二分查找(要求有序)")
    H.para(
        "二分查找要求数组已排序。它每次比较中间元素,如果目标小于中间值则在左半部分查找,"
        "大于则在右半部分查找,每次将搜索范围缩小一半。"
    )
    H.code("""fn binary_search(arr, target) {
    let left = 0;
    let right = len(arr) - 1;
    while (left <= right) {
        let mid = (left + right) / 2;
        if (arr[mid] == target) {
            return mid;
        }
        if (arr[mid] < target) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }
    return -1;
}

let sorted_nums = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19];
print(binary_search(sorted_nums, 7));    # 3
print(binary_search(sorted_nums, 15));   # 7
print(binary_search(sorted_nums, 8));    # -1""")
    H.output("""3
7
-1""")
    H.note("二分查找的时间复杂度为 O(log n),远优于线性查找的 O(n)。但前提是数组必须有序。注意 H# 中两整数相除为整数除法,所以 (left + right) / 2 自动取整。")

    # --- 21.6 ---
    H.h3("21.6 递归算法")
    H.para("递归是函数调用自身的编程技巧。每个递归函数必须包含两个要素:基线条件(终止递归)和递归条件(向基线靠近)。")

    H.para("阶乘: n! = n * (n-1)!,1! = 1")
    H.code("""fn factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

print(factorial(5));    # 120
print(factorial(10));   # 3628800""")
    H.output("""120
3628800""")

    H.para("斐波那契数列: F(n) = F(n-1) + F(n-2),F(0)=0, F(1)=1")
    H.code("""fn fib(n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

print(fib(10));    # 55
print(fib(15));    # 610""")
    H.output("""55
610""")
    H.warning("递归实现的斐波那契存在大量重复计算,时间复杂度为 O(2^n)。对于较大的 n,建议使用迭代方式或记忆化优化。")

    H.para("汉诺塔:经典递归问题,将 n 个盘子从 A 柱移到 C 柱,B 柱作为辅助。")
    H.code("""let hanoi_moves = 0;

fn hanoi(n, from_rod, to_rod, aux_rod) {
    if (n == 1) {
        hanoi_moves = hanoi_moves + 1;
        print("Move disk 1 from " + from_rod + " to " + to_rod);
        return 0;
    }
    hanoi(n - 1, from_rod, aux_rod, to_rod);
    hanoi_moves = hanoi_moves + 1;
    print("Move disk " + n + " from " + from_rod + " to " + to_rod);
    hanoi(n - 1, aux_rod, to_rod, from_rod);
    return 0;
}

hanoi(3, "A", "C", "B");
print("Total moves: " + hanoi_moves);""")
    H.output("""Move disk 1 from A to C
Move disk 2 from A to B
Move disk 1 from C to B
Move disk 3 from A to C
Move disk 1 from B to A
Move disk 2 from B to C
Move disk 1 from A to C
Total moves: 7""")
    H.para(
        "汉诺塔的递归思路:要将 n 个盘子从 A 移到 C,先把上面 n-1 个盘子从 A 移到 B(借助 C),"
        "然后把最大的盘子从 A 移到 C,最后把 n-1 个盘子从 B 移到 C(借助 A)。"
        "n 个盘子的最少移动次数为 2^n - 1,3 个盘子需要 7 步。"
    )

    # --- 21.7 ---
    H.h3("21.7 算法复杂度简介")
    H.para("算法复杂度用大 O 记号表示,描述算法运行时间(或空间)随输入规模增长的趋势。")
    H.bullet("O(1) — 常数时间:如数组索引访问、字典查找")
    H.bullet("O(log n) — 对数时间:如二分查找")
    H.bullet("O(n) — 线性时间:如线性查找、遍历列表")
    H.bullet("O(n log n) — 线性对数时间:如归并排序、快速排序")
    H.bullet("O(n^2) — 平方时间:如冒泡排序、选择排序、插入排序")
    H.bullet("O(2^n) — 指数时间:如递归实现的斐波那契")

    H.para("下面是本章实现的查找最大值和求和函数,它们都是 O(n) 算法:")
    H.code("""fn find_max(arr) {
    let m = arr[0];
    let i = 1;
    while (i < len(arr)) {
        if (arr[i] > m) {
            m = arr[i];
        }
        i = i + 1;
    }
    return m;
}

fn find_min(arr) {
    let m = arr[0];
    let i = 1;
    while (i < len(arr)) {
        if (arr[i] < m) {
            m = arr[i];
        }
        i = i + 1;
    }
    return m;
}

let nums = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5];
print(find_max(nums));   # 9
print(find_min(nums));   # 1

# 求和与平均值
fn sum_arr(arr) {
    let total = 0;
    for n in arr {
        total = total + n;
    }
    return total;
}

print(sum_arr(nums));               # 44
print(sum_arr(nums) / len(nums));   # 4 (整数除法)""")
    H.output("""9
1
44
4""")
    H.note("H# 中两个整数相除为整数除法(向下取整),44/11=4。若需浮点结果,需将操作数转为浮点数。")

    H.para("附:求最大公约数(GCD)的辗转相除法,时间复杂度 O(log n):")
    H.code("""fn gcd(a, b) {
    while (b != 0) {
        let temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

print(gcd(48, 18));     # 6
print(gcd(100, 75));    # 25""")
    H.output("""6
25""")

    # --- 小结与练习 ---
    H.h3("本章小结")
    H.bullet("冒泡排序:相邻元素比较交换,每轮冒泡最大值到末尾,O(n^2)")
    H.bullet("选择排序:每轮选最小值放到前面,交换次数少,O(n^2)")
    H.bullet("插入排序:将元素插入已排序部分的正确位置,近似有序时高效")
    H.bullet("线性查找 O(n) 适用于无序数据,二分查找 O(log n) 要求有序")
    H.bullet("递归三要素:基线条件、递归条件、向基线靠近")
    H.bullet("大 O 记号描述算法复杂度,是衡量算法效率的标准")

    H.h3("练习题")
    H.number("修改冒泡排序,增加一个标志位:如果某轮没有发生交换,提前终止排序。")
    H.number("编写函数 merge_sorted(a, b),合并两个有序列表为一个新的有序列表。")
    H.number("用迭代(非递归)方式实现斐波那契数列,避免重复计算。")
    H.number("编写函数 is_prime(n),判断 n 是否为素数(只能被 1 和自身整除)。")
    H.number("实现递归函数 power(base, exp),计算 base 的 exp 次方。")

    H.page_break()

    # ============================================================
    # 第22章 数据结构实战
    # ============================================================
    H.h2("第22章 数据结构实战")
    H.para(
        "数据结构是组织和存储数据的方式,直接影响算法的效率。本章将用 H# 实现栈、队列、链表、"
        "二叉树和图等基础数据结构,最后用栈实现一个表达式求值器。这些数据结构是更复杂程序的基础组件。"
    )

    # --- 22.1 ---
    H.h3("22.1 栈的实现")
    H.para(
        "栈是一种后进先出(LIFO, Last In First Out)的数据结构。"
        "最后压入的元素最先弹出。H# 的列表天然支持栈操作:push 压入,pop 弹出。"
    )
    H.code("""class Stack {
    fn init() {
        self.items = [];
    }
    fn push(item) {
        push(self.items, item);
        return self;
    }
    fn pop() {
        if (len(self.items) == 0) {
            return nullptr;
        }
        return pop(self.items);
    }
    fn peek() {
        if (len(self.items) == 0) {
            return nullptr;
        }
        return self.items[len(self.items) - 1];
    }
    fn size() {
        return len(self.items);
    }
    fn is_empty() {
        return len(self.items) == 0;
    }
}

let st = new Stack();
st.init();
st.push(10);
st.push(20);
st.push(30);
print(st.size());       # 3
print(st.peek());       # 30 (查看栈顶,不弹出)
print(st.pop());        # 30 (弹出栈顶)
print(st.pop());        # 20
print(st.size());       # 1
print(st.is_empty());   # False""")
    H.output("""3
30
30
20
1
False""")
    H.note("栈的 peek 方法返回栈顶元素但不删除,pop 方法返回并删除栈顶元素。空栈时两者都返回 nullptr。")
    H.para("栈的应用场景包括:函数调用管理、表达式求值、括号匹配、撤销操作(Undo)等。")

    # --- 22.2 ---
    H.h3("22.2 队列的实现")
    H.para(
        "队列是一种先进先出(FIFO, First In First Out)的数据结构。"
        "先入队的元素先出队。由于 H# 的 pop 只能从末尾删除,我们用一个 head 指针标记队首位置,"
        "避免每次出队都要移动所有元素。"
    )
    H.code("""class Queue {
    fn init() {
        self.items = [];
        self.head = 0;
    }
    fn enqueue(item) {
        push(self.items, item);
        return self;
    }
    fn dequeue() {
        if (self.head >= len(self.items)) {
            return nullptr;
        }
        let item = self.items[self.head];
        self.head = self.head + 1;
        return item;
    }
    fn size() {
        return len(self.items) - self.head;
    }
    fn is_empty() {
        return self.head >= len(self.items);
    }
}

let qu = new Queue();
qu.init();
qu.enqueue("A");
qu.enqueue("B");
qu.enqueue("C");
print(qu.size());       # 3
print(qu.dequeue());    # A (先入队的先出)
print(qu.dequeue());    # B
print(qu.size());       # 1
print(qu.is_empty());   # False""")
    H.output("""3
A
B
1
False""")
    H.para(
        "enqueue 用 push 将元素添加到末尾(入队),dequeue 通过移动 head 指针来'删除'队首元素(出队)。"
        "这种设计避免了每次出队都要移动所有元素,但会浪费空间(head 之前的元素不再使用)。"
        "在生产环境中,可以定期压缩列表回收空间。"
    )
    H.note("队列的应用场景包括:任务调度、消息队列、广度优先搜索(BFS)等。")

    # --- 22.3 ---
    H.h3("22.3 链表的实现")
    H.para(
        "链表是由节点组成的线性数据结构,每个节点包含数据和指向下一个节点的引用。"
        "与数组不同,链表的元素在内存中不必连续,插入和删除效率高但访问效率低。"
        "我们用字典来模拟链表节点:{value: 数据, next: 下一节点}。"
    )
    H.code("""# 创建节点
fn make_node(value) {
    return {"value": value, "next": nullptr};
}

# 构建链表: 1 -> 2 -> 3 -> 4
let head = make_node(1);
head["next"] = make_node(2);
head["next"]["next"] = make_node(3);
head["next"]["next"]["next"] = make_node(4);

# 遍历链表
fn print_list(node) {
    let curr = node;
    while (curr != nullptr) {
        print(curr["value"]);
        curr = curr["next"];
    }
    return 0;
}
print_list(head);""")
    H.output("""1
2
3
4""")

    H.para("计算链表长度:")
    H.code("""fn list_length(node) {
    let count = 0;
    let curr = node;
    while (curr != nullptr) {
        count = count + 1;
        curr = curr["next"];
    }
    return count;
}
print("Length: " + list_length(head));   # Length: 4""")
    H.output("Length: 4")

    H.para("在链表头部插入新节点(头插法):")
    H.code("""fn list_prepend(node, value) {
    let new_node = make_node(value);
    new_node["next"] = node;
    return new_node;
}

# 在头部插入 0
head = list_prepend(head, 0);
print_list(head);
print("Length: " + list_length(head));""")
    H.output("""0
1
2
3
4
Length: 5""")
    H.para("头插法创建一个新节点,将其 next 指向原链表头部,然后返回新节点作为新的头。时间复杂度 O(1),非常高效。")

    # --- 22.4 ---
    H.h3("22.4 二叉树的基础")
    H.para(
        "二叉树是每个节点最多有两个子节点(左子树和右子树)的树形结构。"
        "我们用字典模拟树节点:{value: 数据, left: 左子树, right: 右子树}。"
        "二叉树常用于实现搜索树、堆、表达式树等。"
    )
    H.code("""fn make_tree(value) {
    return {"value": value, "left": nullptr, "right": nullptr};
}

# 构建二叉树:
#         1
#        / \\
#       2   3
#      / \\ / \\
#     4  5 6  7
let root = make_tree(1);
root["left"] = make_tree(2);
root["right"] = make_tree(3);
root["left"]["left"] = make_tree(4);
root["left"]["right"] = make_tree(5);
root["right"]["left"] = make_tree(6);
root["right"]["right"] = make_tree(7);""")

    H.para("中序遍历(左 -> 根 -> 右):")
    H.code("""fn inorder(node) {
    if (node == nullptr) {
        return 0;
    }
    inorder(node["left"]);
    print(node["value"]);
    inorder(node["right"]);
    return 0;
}

print("Inorder traversal:");
inorder(root);""")
    H.output("""Inorder traversal:
4
2
5
1
6
3
7""")

    H.para("前序遍历(根 -> 左 -> 右):")
    H.code("""fn preorder(node) {
    if (node == nullptr) {
        return 0;
    }
    print(node["value"]);
    preorder(node["left"]);
    preorder(node["right"]);
    return 0;
}

print("Preorder traversal:");
preorder(root);""")
    H.output("""Preorder traversal:
1
2
4
5
3
6
7""")

    H.para("计算树的高度(最大深度):")
    H.code("""fn tree_height(node) {
    if (node == nullptr) {
        return 0;
    }
    let left_h = tree_height(node["left"]);
    let right_h = tree_height(node["right"]);
    if (left_h > right_h) {
        return left_h + 1;
    }
    return right_h + 1;
}

print("Height: " + tree_height(root));   # Height: 3""")
    H.output("Height: 3")
    H.note("树的高度等于左子树和右子树中较高者加 1。空树高度为 0。这是典型的递归算法。")

    # --- 22.5 ---
    H.h3("22.5 图的基础(邻接表)")
    H.para(
        "图由顶点和边组成。邻接表是图的常用表示方法:用字典存储每个顶点及其相邻顶点列表。"
        "下面创建一个无向图,并实现边的查询和广度优先搜索(BFS)。"
    )
    H.code("""# 用邻接表表示无向图
let graph = {
    "A": ["B", "C"],
    "B": ["A", "D", "E"],
    "C": ["A", "F"],
    "D": ["B"],
    "E": ["B", "F"],
    "F": ["C", "E"]
};

# 打印图的邻接表
fn print_graph(g) {
    for node, neighbors in g {
        let nbr_str = "";
        let i = 0;
        while (i < len(neighbors)) {
            if (i > 0) {
                nbr_str = nbr_str + ", ";
            }
            nbr_str = nbr_str + neighbors[i];
            i = i + 1;
        }
        print(node + " -> " + nbr_str);
    }
    return 0;
}
print_graph(graph);""")
    H.output("""A -> B, C
B -> A, D, E
C -> A, F
D -> B
E -> B, F
F -> C, E""")

    H.para("判断两个顶点之间是否有边:")
    H.code("""fn has_edge(g, a, b) {
    if (not (a in g)) {
        return false;
    }
    return b in g[a];
}

print(has_edge(graph, "A", "B"));   # True
print(has_edge(graph, "A", "D"));   # False
print(has_edge(graph, "X", "Y"));   # False""")
    H.output("""True
False
False""")

    H.para("广度优先搜索(BFS):从起点出发,逐层访问所有可达顶点。")
    H.code("""fn bfs(g, start) {
    let visited = {};
    let queue = [];
    push(queue, start);
    visited[start] = true;
    let order = [];
    while (len(queue) > 0) {
        # 取出队首
        let node = queue[0];
        let i = 1;
        let new_queue = [];
        while (i < len(queue)) {
            push(new_queue, queue[i]);
            i = i + 1;
        }
        queue = new_queue;
        push(order, node);
        # 访问所有未访问的邻居
        let neighbors = g[node];
        let j = 0;
        while (j < len(neighbors)) {
            let nb = neighbors[j];
            if (not (nb in visited)) {
                visited[nb] = true;
                push(queue, nb);
            }
            j = j + 1;
        }
    }
    return order;
}

print(bfs(graph, "A"));""")
    H.output("['A', 'B', 'C', 'D', 'E', 'F']")
    H.para(
        "BFS 使用队列实现:从起点 A 出发,先访问 A 的邻居 B 和 C,再访问 B 的邻居 D 和 E,"
        "最后访问 C 的邻居 F。visited 字典确保每个顶点只访问一次。"
    )
    H.note("由于 H# 列表没有内置的 dequeue(从头部删除)操作,这里通过重建列表的方式模拟队列出队。实际应用中可用 Queue 类优化。")

    # --- 22.6 ---
    H.h3("22.6 实战:表达式求值(用栈)")
    H.para(
        "栈的经典应用之一是表达式求值。下面实现一个支持加减乘除和括号的算术表达式求值器。"
        "使用两个栈:数值栈存放操作数,运算符栈存放运算符。"
        "遇到数字压入数值栈,遇到运算符时先将栈中优先级相同或更高的运算符弹出计算,再压入新运算符。"
    )
    H.warning("本实现采用左到右结合(同级运算符从左到右计算),不支持运算符优先级(即 3+4*2 先算 3+4 再乘 2)。括号可以改变计算顺序。")
    H.code("""# 应用一个运算符:从数值栈弹出两个数,从运算符栈弹出一个运算符,计算后压回数值栈
fn apply_op(values, ops) {
    let b = pop(values);
    let a = pop(values);
    let op = pop(ops);
    let r = 0;
    if (op == "+") { r = a + b; }
    if (op == "-") { r = a - b; }
    if (op == "*") { r = a * b; }
    if (op == "/") { r = a / b; }
    push(values, r);
    return 0;
}

fn eval_expr(expr) {
    let values = [];
    let ops = [];
    let i = 0;
    let n = len(expr);
    while (i < n) {
        let ch = substring(expr, i, 1);
        if (ch == " ") {
            i = i + 1;
        } else {
            if (ch >= "0" and ch <= "9") {
                # 解析多位数字
                let num = 0;
                while (i < n and substring(expr, i, 1) >= "0" and substring(expr, i, 1) <= "9") {
                    num = num * 10 + (ord(substring(expr, i, 1)) - ord("0"));
                    i = i + 1;
                }
                push(values, num);
            } else {
                if (ch == "(") {
                    push(ops, ch);
                    i = i + 1;
                } else {
                    if (ch == ")") {
                        # 遇到右括号,计算到左括号
                        while (len(ops) > 0 and ops[len(ops) - 1] != "(") {
                            apply_op(values, ops);
                        }
                        if (len(ops) > 0) {
                            pop(ops);   # 弹出左括号
                        }
                        i = i + 1;
                    } else {
                        # 遇到运算符,先计算栈中的运算符
                        while (len(ops) > 0 and ops[len(ops) - 1] != "(") {
                            apply_op(values, ops);
                        }
                        push(ops, ch);
                        i = i + 1;
                    }
                }
            }
        }
    }
    # 计算剩余的运算符
    while (len(ops) > 0) {
        apply_op(values, ops);
    }
    return values[0];
}

print(eval_expr("3 + 4 * 2"));          # 14 (左到右: 3+4=7, 7*2=14)
print(eval_expr("(1 + 2) * (3 + 4)"));  # 21 (括号: 3*7=21)
print(eval_expr("10 + 20 - 5"));        # 25 (左到右: 10+20=30, 30-5=25)
print(eval_expr("100 / 4 + 6"));        # 31 (左到右: 100/4=25, 25+6=31)""")
    H.output("""14
21
25
31""")
    H.para(
        "求值器的工作流程:逐字符扫描表达式。遇到数字时解析完整数字(支持多位数)压入数值栈;"
        "遇到运算符时,先将运算符栈中已有的运算符(到左括号为止)依次弹出并计算,再压入新运算符;"
        "遇到右括号时,计算到对应的左括号。扫描结束后,将运算符栈中剩余的运算符依次计算。"
        "最终数值栈中剩下的唯一元素就是结果。"
    )
    H.note("多位数字的解析:逐个字符读取数字,通过 num = num * 10 + (ord(ch) - ord('0')) 累加。例如 '123' 解析为 1*100 + 2*10 + 3 = 123。")

    # --- 小结与练习 ---
    H.h3("本章小结")
    H.bullet("栈:后进先出(LIFO),用列表 push/pop 实现,支持函数调用、表达式求值")
    H.bullet("队列:先进先出(FIFO),用列表 + head 指针实现,支持任务调度、BFS")
    H.bullet("链表:节点用字典模拟,支持 O(1) 头插法,适合频繁插入删除")
    H.bullet("二叉树:用字典模拟节点,中序/前序遍历用递归实现")
    H.bullet("图:邻接表用字典表示,顶点为键,邻接顶点列表为值")
    H.bullet("表达式求值:双栈法(数值栈 + 运算符栈)是栈的经典应用")

    H.h3("练习题")
    H.number("为 Stack 类增加 clear() 方法,清空栈中所有元素。")
    H.number("实现链表的 append(在末尾添加)和 delete_by_value(按值删除)方法。")
    H.number("实现二叉树的后序遍历(左 -> 右 -> 根)。")
    H.number("实现图的深度优先搜索(DFS),用递归或栈实现。")
    H.number("扩展表达式求值器,支持运算符优先级(* / 优先于 + -)。")

    H.page_break()
