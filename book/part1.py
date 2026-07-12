# -*- coding: utf-8 -*-
"""《H# 从入门到精通》第一篇 基础入门(第1-4章)+ 第二篇 核心语法(第5-9章)

所有代码示例均通过 python3 interpreter.py file.hto 实机测试。
"""


def add_content(doc, H):
    # ================================================================
    # 第一篇 基础入门
    # ================================================================
    H.h1("第一篇 基础入门")
    H.para("本篇是 H# 语言学习的起点。我们将从语言简介开始,逐步介绍环境搭建、"
           "基本语法元素以及变量与赋值,帮助零基础读者快速上手 H# 编程。"
           "通过本篇的学习,你将能够独立编写并运行简单的 H# 程序,理解语言的"
           "核心概念与基本约定,为后续深入学习核心语法打下坚实基础。")

    # ================================================================
    # 第1章 H# 语言简介
    # ================================================================
    H.h2("第1章 H# 语言简介")
    H.para("本章是全书的起点。我们将介绍 H# 语言的起源与设计哲学,概述其核心特性,"
           "并剖析独特的\"三套运行时\"架构。通过一个 Hello World 示例,你将初步感受"
           "H# 的代码风格与运行方式。本章末尾配有小结与练习,帮助你巩固所学。")

    H.h3("1.1 什么是 H#")
    H.para("H#(H-Sharp)是一门从 Python 衍生而来的脚本语言。它在设计上汲取了 "
           "Python 的简洁与易读,同时引入了花括号 {} 代码块、分号语句终结等 "
           "C 系列语言的风格元素。H# 是一门缩进敏感、多范式的语言——你可以用它"
           "编写过程式脚本,也可以采用函数式或面向对象的编程风格。")
    H.para("H# 的设计哲学可以概括为三点:")
    H.bullet("简洁优先:语法尽量直观,减少不必要的样板代码,让开发者专注于问题本身。")
    H.bullet("多范式融合:过程式、函数式、面向对象三大范式在同一语言中和谐共存。")
    H.bullet("同源多运行时:一套语法,三套运行时,从开发调试到生产部署无缝衔接。")
    H.para("H# 的名字中的 \"#\" 读作 Sharp,寓意\"敏捷、精准\"。它与 Python 的关系"
           "类似于 Java 与 C++——继承了前者的优秀基因,同时在语法形态与运行时"
           "架构上做了重新设计。")

    H.h3("1.2 核心特性")
    H.para("H# 具备以下核心特性,使其在脚本语言家族中独树一帜:")
    H.bullet("动态类型:变量声明无需指定类型,运行时自动推断与转换。")
    H.bullet("一等函数:函数可以赋值给变量、作为参数传递、作为返回值返回。")
    H.bullet("Lambda 闭包:支持匿名函数与词法作用域捕获,函数式编程得心应手。")
    H.bullet("面向对象:提供 class 定义、方法绑定、字段封装等完整 OOP 能力。")
    H.bullet("异常处理:通过 try/catch/throw 进行结构化错误处理。")
    H.bullet("丰富的内置函数:涵盖字符串、列表、字典、文件 I/O、数学运算等常用操作。")
    H.bullet("三套运行时:Python 树遍历解释器、Python 字节码 VM、Kotlin HVM 栈式虚拟机。")

    H.h3("1.3 三套运行时架构")
    H.para("H# 最显著的特点是\"三套同源运行时\"架构。同一份 .hto 源代码可以在"
           "三套不同的运行时上执行,各有侧重:")
    H.number("Python 树遍历解释器(interpreter.py):直接遍历 AST 执行,启动快、"
             "调试方便,是开发阶段的首选运行时。")
    H.number("Python 字节码 VM(bytecode.py):将源码编译为字节码后再执行,带有"
             "内联缓存优化,适合性能敏感的开发场景。")
    H.number("Kotlin HVM 栈式虚拟机:生产级运行时,支持跨平台原生打包,性能最高,"
             "用于最终部署与发布。")
    H.para("三套运行时在语义上保持一致:同一段 H# 代码在任意运行时上运行,结果相同。"
           "开发者可以在开发阶段使用 Python 解释器快速迭代,在发布阶段切换到 "
           "Kotlin HVM 获得最佳性能。本书所有示例均在 Python 解释器上测试通过。")
    H.note("运行 H# 程序的命令格式为:python3 interpreter.py 文件名.hto。"
           "本书后续所有代码示例均采用此方式运行。")

    H.h3("1.4 应用场景")
    H.para("H# 适用于多种开发场景:")
    H.bullet("脚本工具与自动化任务:快速编写系统管理脚本、数据处理工具。")
    H.bullet("教学与算法竞赛:H# 语法简洁,适合作为编程入门教学语言。")
    H.bullet("原型开发:快速验证算法与数据结构设计,无需复杂的工程配置。")
    H.bullet("嵌入式脚本:作为宿主应用的扩展脚本语言,提供灵活的定制能力。")
    H.bullet("Web 后端:配合内置 HTTP 服务器模块,可快速搭建后端服务。")

    H.h3("1.5 Hello World 示例")
    H.para("让我们从经典的 Hello World 开始,感受 H# 的代码风格。"
           "创建一个名为 hello.hto 的文件,输入以下内容:")
    H.code(r'''print("Hello, H#!");''')
    H.para("在终端中执行以下命令运行程序:")
    H.code('''python3 interpreter.py hello.hto''')
    H.para("程序运行后,终端将输出:")
    H.output('''Hello, H#!''')
    H.para("恭喜!你已经运行了第一个 H# 程序。print 是 H# 的内置输出函数,"
           "它将括号中的内容打印到终端。字符串使用双引号 \"\" 包裹,语句以分号 ; 结尾。"
           "下面再看一个稍复杂的示例,引入变量与字符串拼接:")
    H.code(r'''let name = "H#";
print("Welcome to " + name);''')
    H.output('''Welcome to H#''')
    H.para("这里用 let 声明了变量 name,然后用 + 号将两个字符串拼接在一起输出。"
           "let 是 H# 声明变量的关键字,无需指定类型,语言会自动推断。")
    H.para("我们再看一个多行输出的例子:")
    H.code(r'''print("Hello, World!");
print("I am learning H#.");
print("Let us begin!");''')
    H.output('''Hello, World!
I am learning H#.
Let us begin!''')

    H.h3("1.6 本章小结")
    H.para("本章介绍了 H# 语言的起源、设计哲学与核心特性。你了解到 H# 是一门 "
           "Python 衍生的多范式脚本语言,拥有三套同源运行时架构。通过 Hello World "
           "示例,你初步体验了 H# 的基本语法:print 输出、let 声明变量、双引号字符串、"
           "分号结尾。这些是后续学习的基石。")

    H.h3("练习题")
    H.number("用自己的话描述 H# 语言的三个设计哲学。")
    H.number("列举 H# 的三套运行时,并说明各自适用的场景。")
    H.number("编写一个 H# 程序,输出你的名字和一句问候语(使用变量和字符串拼接)。")
    H.number("运行本章的 Hello World 示例,观察输出结果是否与书中一致。")
    H.page_break()

    # ================================================================
    # 第2章 环境搭建
    # ================================================================
    H.h2("第2章 环境搭建")
    H.para("工欲善其事,必先利其器。本章将指导你搭建 H# 开发环境,包括获取源码、"
           "安装 Python 运行时、了解 Kotlin HVM 编译运行流程,以及配置开发工具。"
           "环境搭建完成后,我们将编写第一个完整的 H# 程序。")

    H.h3("2.1 获取源码与 Python 环境")
    H.para("H# 的 Python 运行时基于 Python 3 开发,因此首先需要确保系统中安装了 "
           "Python 3.10 或更高版本。可以在终端中执行以下命令检查 Python 版本:")
    H.code('''python3 --version''')
    H.output('''Python 3.13.0''')
    H.para("确认 Python 版本满足要求后,获取 H# 源码。H# 项目目录中包含以下核心文件:")
    H.bullet("interpreter.py — 树遍历解释器,本书主要使用的运行时入口")
    H.bullet("lexer.py — 词法分析器,将源码切分为 Token")
    H.bullet("parser.py — 语法分析器,将 Token 组织为 AST")
    H.bullet("h_ast.py — AST 节点定义")
    H.bullet("tokens.py — Token 类型定义")
    H.bullet("bytecode.py — 字节码虚拟机(开发调试用)")
    H.bullet("compiler.py — 字节码编译器,将 .hto 编译为 .hbc")
    H.bullet("hsharp.py — CLI 统一入口")
    H.note("本书只需 interpreter.py 即可运行所有示例。其他文件在后续深入章节中介绍。")

    H.h3("2.2 运行 H# 程序")
    H.para("运行 H# 程序非常简单。将 H# 源码保存为 .hto 扩展名的文件,然后用 "
           "Python 解释器执行即可。命令格式如下:")
    H.code('''python3 interpreter.py 文件名.hto''')
    H.para("例如,创建文件 hello.hto,内容为 print(\"Hello, H#!\");,然后运行:")
    H.code('''python3 interpreter.py hello.hto''')
    H.output('''Hello, H#!''')
    H.para("H# 源码文件通常使用 .hto 作为扩展名(hto 是 H-Sharp Object 的缩写)。"
           "这是社区约定,虽然解释器本身不强制要求扩展名,但建议统一使用 .hto。")

    H.h3("2.3 Kotlin HVM 编译运行")
    H.para("生产环境中推荐使用 Kotlin HVM 运行时。它将 H# 源码编译为字节码(.hbc),"
           "再由高性能的栈式虚拟机执行。流程如下:")
    H.number("使用 Python 编译器将 .hto 编译为 .hbc 字节码文件:")
    H.code('''python3 compiler.py app.hto -o app.hbc''')
    H.number("使用 Kotlin HVM 运行字节码:")
    H.code('''java -jar hsharp-kotlin-compiler/build/libs/hsharp-runtime.jar app.hbc''')
    H.para(".hbc 文件采用 JSON 容器格式,包含指令序列(instructions)与常量池"
           "(consts)两部分,可被 Kotlin HVM 与 Python 字节码 VM 共同加载。")
    H.warning("Kotlin HVM 需要 JDK 11 或更高版本。如果仅用于学习,使用 Python "
              "解释器即可,无需安装 JDK。")

    H.h3("2.4 bootstrap 工具链介绍")
    H.para("H# 项目包含一个 bootstrap 目录,其中存放着用 H# 语言自身实现的编译器"
           "组件。这是 H# 自举(self-hosting)计划的核心:用 H# 编写 H# 的词法分析器、"
           "语法分析器与编译器,最终摆脱对 Python 的依赖。")
    H.para("bootstrap 目录中的关键文件包括:")
    H.bullet("tokenize.hto — H# 实现的词法分析器")
    H.bullet("parser.hto — H# 实现的语法分析器")
    H.bullet("compiler.hto — H# 实现的字节码编译器")
    H.bullet("interpreter.hto — H# 实现的树遍历解释器")
    H.bullet("selftest.hto — 自举自测脚本")
    H.note("自举是编程语言发展的高级阶段。感兴趣的读者可以阅读 bootstrap 目录"
           "中的源码,了解 H# 如何用自身实现自身。")

    H.h3("2.5 IDE 配置")
    H.para("H# 源码本质上是文本文件,任何文本编辑器都可以编写。为了提升开发体验,"
           "建议配置语法高亮。H# 的语法与 C/Java/JavaScript 系列相似(花括号块、"
           "分号结尾),因此可以将编辑器的语法高亮设置为 JavaScript 或 C 模式,"
           "即可获得不错的高亮效果。")
    H.para("项目中也提供了专属的 HCS Code IDE(基于 Avalonia 的桌面 IDE),"
           "支持语法高亮、代码补全与一键运行。此外,VS Code 用户可以通过配置"
           "自定义语言模式来实现 H# 语法高亮。")

    H.h3("2.6 第一个完整程序")
    H.para("现在让我们编写第一个完整的 H# 程序,综合运用变量、运算与循环。"
           "创建文件 first.hto,输入以下代码:")
    H.code(r'''let name = "World";
print("Hello, " + name + "!");
let a = 10;
let b = 20;
print("a + b = " + str(a + b));
print("a * b = " + str(a * b));
let nums = [1, 2, 3, 4, 5];
let total = 0;
for n in nums {
    total = total + n;
}
print("sum = " + str(total));''')
    H.output('''Hello, World!
a + b = 30
a * b = 200
sum = 15''')
    H.para("这个程序做了四件事:输出问候语、计算两数之和与积、用循环求列表元素总和。"
           "其中 str() 函数将数字转换为字符串以便拼接,for-in 循环遍历列表中的每个元素。"
           "这些语法将在后续章节中详细讲解。")
    H.note("如果运行时出现 \"Function 'xxx' not defined\" 错误,说明你使用了一个"
           "当前运行时未注册的内置函数。请查阅附录的内置函数速查表确认可用函数。")

    H.h3("本章小结")
    H.para("本章搭建了 H# 开发环境。你学会了用 python3 interpreter.py file.hto "
           "运行 H# 程序,了解了 Kotlin HVM 编译运行流程与 bootstrap 自举工具链, "
           "并编写了第一个综合运用变量、运算与循环的完整程序。至此,你已具备"
           "独立编写和运行 H# 程序的能力。")

    H.h3("练习题")
    H.number("在你的计算机上搭建 H# 运行环境,成功运行 Hello World 程序。")
    H.number("修改 2.6 节的示例程序,将列表改为 [10, 20, 30],观察输出变化。")
    H.number("尝试用 write_file() 函数将一段文字写入文件,再用 read_file() 读回。")
    H.number("浏览 bootstrap 目录,了解自举工具链的文件组成。")
    H.page_break()

    # ================================================================
    # 第3章 基本语法元素
    # ================================================================
    H.h2("第3章 基本语法元素")
    H.para("本章介绍 H# 的基本语法元素,包括标识符与关键字、注释、缩进规则、"
           "语句与分号,以及各种字面量。这些是构成 H# 程序的最基本\"积木\","
           "掌握它们是阅读与编写 H# 代码的前提。")

    H.h3("3.1 标识符与关键字")
    H.para("标识符是开发者给变量、函数、类等起的名字。H# 的标识符规则如下:")
    H.bullet("由字母(a-z, A-Z)、数字(0-9)和下划线(_)组成。")
    H.bullet("首字符必须是字母或下划线,不能以数字开头。")
    H.bullet("区分大小写:userName 和 username 是不同的标识符。")
    H.bullet("不能与关键字重名。")
    H.para("H# 的关键字包括:let、auto、fn、class、if、else、for、while、"
           "return、break、continue、true、false、nullptr、and、or、not、"
           "try、catch、throw、import、new 等。这些关键字有特殊含义,不能用作标识符名。")
    H.para("以下是合法的标识符示例:")
    H.code(r'''let userName = "Alice";
let _count = 10;
let total2 = 100;
print(userName);
print(_count);
print(total2);''')
    H.output('''Alice
10
100''')
    H.para("userName 采用驼峰命名法,首单词全小写,后续单词首字母大写。"
           "_count 以下划线开头,total2 以数字结尾但非开头,都是合法的。")
    H.warning("以下标识符非法:2num(数字开头)、my-name(含连字符)、"
              "class(关键字)。这些会导致语法错误。")

    H.h3("3.2 注释")
    H.para("注释是给开发者看的说明文字,解释器会忽略注释内容。H# 使用 # 号"
           "作为注释符号,支持单行注释和行尾注释:")
    H.code(r'''# 这是单行注释
let x = 10; # 这是行尾注释
print(x);''')
    H.output('''10''')
    H.para("# 后面到行尾的所有内容都被视为注释。注释可以独占一行,也可以跟在代码后面。"
           "良好的注释习惯能大大提升代码的可读性与可维护性。")
    H.note("H# 目前仅支持单行注释(以 # 开头),不支持多行注释块。"
           "如需多行注释,可以在每行前加 #。")

    H.h3("3.3 缩进规则与花括号")
    H.para("H# 使用花括号 {} 来定义代码块。代码块常见于函数体、条件分支、"
           "循环体等场景。花括号内的语句属于同一个作用域。")
    H.para("虽然 H# 源自 Python(以缩进敏感著称),但 H# 在代码块的定义上"
           "采用了花括号而非纯缩进。这意味着缩进只是代码风格的约定,不影响"
           "程序的逻辑结构——真正界定代码块边界的是花括号。不过,为了代码可读性,"
           "强烈建议保持一致的缩进风格(推荐每层缩进 4 个空格)。")
    H.code(r'''if (true) {
    print("在代码块内");
    print("仍然在代码块内");
}
print("在代码块外");''')
    H.output('''在代码块内
仍然在代码块内
在代码块外''')

    H.h3("3.4 语句与分号")
    H.para("H# 的语句以分号 ; 结尾。每条语句完成一个操作,如变量声明、赋值、"
           "函数调用等。分号标志着一条语句的结束。")
    H.code(r'''let a = 1;
let b = 2;
let c = a + b;
print(c);''')
    H.output('''3''')
    H.para("虽然某些情况下解释器可以推断语句边界,但建议始终使用分号结尾,以避免"
           "歧义并保持代码风格的一致性。这也是 H# 与 Python 的一个显著区别——"
           "Python 使用换行分隔语句,而 H# 使用分号。")

    H.h3("3.5 字面量")
    H.para("字面量是源码中直接表示固定值的写法。H# 支持以下字面量类型:")
    H.bullet("数字字面量:整数(如 42)和浮点数(如 3.14)。")
    H.bullet("字符串字面量:用双引号包裹的文本,如 \"Hello\"。")
    H.bullet("布尔字面量:小写的 true 和 false。")
    H.bullet("空值字面量:nullptr 表示\"无值\"。")
    H.bullet("列表字面量:用方括号包裹,如 [1, 2, 3]。")
    H.bullet("字典字面量:用花括号包裹键值对,如 {\"name\": \"Bob\"}。")
    H.para("下面通过示例展示各种字面量:")
    H.code(r'''let num = 42;
let pi = 3.14;
let text = "Hello";
let flag = true;
let empty = nullptr;
let primes = [2, 3, 5, 7];
let person = {"name": "Bob", "age": 25};
print(num);
print(pi);
print(text);
print(flag);
print(empty);
print(primes);
print(person);''')
    H.output('''42
3.14
Hello
True
None
[2, 3, 5, 7]
{'name': 'Bob', 'age': 25}''')
    H.note("H# 的布尔值 true/false 在 Python 解释器中输出时显示为 True/False"
           "(Python 风格),nullptr 显示为 None,字典显示为 Python 字典格式"
           "{'key': value}。这是 Python 运行时的特性,在 Kotlin HVM 中输出为 "
           "true/false/null 与 H# 原生格式。")
    H.para("可以看到,42 是整数,3.14 是浮点数,\"Hello\" 是字符串,true 是布尔值,"
           "nullptr 是空值,[2, 3, 5, 7] 是列表,{\"name\": \"Bob\", \"age\": 25} "
           "是字典。这些字面量构成了 H# 程序中最基本的数据表达方式。")

    H.h3("本章小结")
    H.para("本章介绍了 H# 的基本语法元素。标识符遵循\"字母/下划线开头\"的规则;"
           "注释使用 # 号;代码块用花括号 {} 界定;语句以分号 ; 结尾;字面量涵盖"
           "数字、字符串、布尔、空值、列表与字典。这些元素是构建 H# 程序的基础部件,"
           "后续章节将围绕它们展开更深入的讨论。")

    H.h3("练习题")
    H.number("列出 5 个合法和 3 个非法的 H# 标识符,说明非法的原因。")
    H.number("编写程序,用字面量创建一个包含 3 种水果名称的列表并输出。")
    H.number("编写程序,创建一个包含你姓名和年龄的字典并输出。")
    H.number("在代码中添加单行注释和行尾注释,观察注释对程序运行的影响。")
    H.page_break()

    # ================================================================
    # 第4章 变量与赋值
    # ================================================================
    H.h2("第4章 变量与赋值")
    H.para("变量是存储数据的命名容器。本章介绍 H# 的变量声明方式、命名规范、"
           "作用域规则、重新赋值以及多重赋值技巧。掌握变量是编程的基础——"
           "没有变量,程序就无法保存和传递数据。")

    H.h3("4.1 let 声明")
    H.para("H# 使用 let 关键字声明变量。声明时需要提供变量名和初始值,"
           "无需指定类型——H# 是动态类型语言,会自动推断变量的类型。")
    H.code(r'''let count = 10;
let message = "Hello";
let price = 19.99;
let active = true;
print(count);
print(message);
print(price);
print(active);''')
    H.output('''10
Hello
19.99
True''')
    H.para("上面的代码声明了四个变量:count 是整数,message 是字符串,"
           "price 是浮点数,active 是布尔值。let 关键字告诉解释器\"声明一个新变量\","
           "等号 = 将右侧的值赋给左侧的变量名。")
    H.para("let 声明的变量在声明时必须有初始值,不支持\"先声明后赋值\"的写法:"
           "let x; 是不合法的,必须写成 let x = 0; 或其他初始值。")

    H.h3("4.2 auto 声明与类型推断")
    H.para("H# 还支持 auto 关键字声明变量,语义上与 let 等价,都表示"
           "由语言自动推断变量类型。auto 更强调\"类型推断\"这一特性——"
           "开发者无需关心变量的具体类型,交给运行时处理。")
    H.para("在当前解释器版本中,let 是最常用的声明方式,也是本书推荐的写法。"
           "以下示例展示 let 声明不同类型变量时的自动推断行为:")
    H.code(r'''let n = 42;
let s = "auto test";
let f = 3.14;
let lst = [1, 2, 3];
print(n);
print(s);
print(f);
print(lst);''')
    H.output('''42
auto test
3.14
[1, 2, 3]''')
    H.para("可以看到,同一个 let 关键字根据右侧值的形态,自动推断出整数、字符串、"
           "浮点数和列表四种不同类型。这就是动态类型语言的便利之处——"
           "代码简洁,开发效率高。")

    H.h3("4.3 命名规范")
    H.para("良好的命名规范能显著提升代码可读性。H# 社区推荐以下命名约定:")
    H.bullet("变量名:小驼峰命名法(camelCase),如 studentName、totalPrice。")
    H.bullet("常量名:全大写加下划线,如 MAX_SIZE、DEFAULT_PORT。")
    H.bullet("布尔变量:以 is/has/can 开头,如 is_valid、has_permission。")
    H.bullet("函数名:小驼峰命名法,如 calculateSum、printResult。")
    H.bullet("类名:大驼峰命名法(PascalCase),如 StudentAccount。")
    H.code(r'''let studentName = "Tom";
let MAX_SIZE = 100;
let is_valid = true;
print(studentName);
print(MAX_SIZE);
print(is_valid);''')
    H.output('''Tom
100
True''')

    H.h3("4.4 作用域基础")
    H.para("作用域是指变量的可见范围。H# 采用块作用域——在代码块(如 if、for、"
           "while 的花括号体内)中声明的变量,只在该块内有效,块外不可访问。"
           "外层作用域的变量在内层块中可以访问。")
    H.code(r'''let outer = 1;
if (outer > 0) {
    let inner = 2;
    print(outer + inner);
}
print(outer);''')
    H.output('''3
1''')
    H.para("变量 outer 在外层声明,if 块内可以访问它。变量 inner 在 if 块内声明,"
           "只在块内有效。print(outer) 在块外执行,输出 1;如果尝试在块外访问 inner,"
           "会报 \"Undefined variable\" 错误。")
    H.warning("H# 不支持裸花括号 {} 创建作用域块(裸 {} 会被解析为字典字面量)。"
              "作用域块必须依附于 if、for、while 等控制结构或函数体。")

    H.h3("4.5 重新赋值")
    H.para("用 let 声明变量后,可以多次重新赋值。重新赋值时不需要 let 关键字,"
           "直接用等号 = 即可。新值的类型可以与旧值不同(动态类型的特性)。")
    H.code(r'''let score = 80;
print(score);
score = 90;
print(score);
score = score + 5;
print(score);''')
    H.output('''80
90
95''')
    H.para("第一行声明 score 并赋值 80。第二行将 score 重新赋值为 90。"
           "第三行 score = score + 5 是一种常见的\"自增\"写法——"
           "取当前值加 5 再赋回给自己,结果为 95。")

    H.h3("4.6 多重赋值技巧")
    H.para("H# 支持解构赋值(多重赋值),可以一次性将列表中的值赋给多个变量。"
           "语法为 let [变量1, 变量2, ...] = 列表;。这在交换变量值、"
           "拆分返回值等场景中非常实用。")
    H.code(r'''let [p, q] = [1, 2];
print(p);
print(q);
let [r, s, _t] = [10, 20, 30];
print(r);
print(s);''')
    H.output('''1
2
10
20''')
    H.para("第一个例子将列表 [1, 2] 解构:p 得到 1,q 得到 2。"
           "第二个例子中,_t 是一个占位符(下划线前缀),表示\"跳过该位置的值\"——"
           "列表中第三个元素 30 被忽略,只取出 r=10 和 s=20。")
    H.note("解构赋值的变量数量应与列表长度匹配。使用 _ 开头的变量名(如 _t、_ignored)"
           "可以跳过不需要的元素,这在处理多返回值时十分方便。")

    H.h3("本章小结")
    H.para("本章介绍了 H# 的变量与赋值机制。let 是声明变量的主要关键字;"
           "变量遵循块作用域规则,代码块内声明的变量在块外不可见;"
           "变量可以重新赋值,且新值类型可与旧值不同;解构赋值 let [a, b] = list "
           "可以一次性给多个变量赋值。这些是后续学习函数与控制流的基础。")

    H.h3("练习题")
    H.number("声明三个变量分别存储你的姓名、年龄和身高,然后输出它们。")
    H.number("编写程序演示块作用域:在外层声明变量,在 if 块内声明另一个变量,"
             "分别在内层和块外访问它们。")
    H.number("用解构赋值交换两个变量的值:初始 a=1, b=2,交换后输出 a=2, b=1。")
    H.number("用 score = score + 10 的方式实现一个累加器,循环 5 次后输出结果。")
    H.page_break()

    # ================================================================
    # 第二篇 核心语法
    # ================================================================
    H.h1("第二篇 核心语法")
    H.para("本篇深入 H# 的核心语法,涵盖数据类型、运算符、控制流、字符串处理"
           "与输入输出。这些是编写实用程序的关键工具。通过本篇的学习,你将能够"
           "编写具备逻辑判断、循环控制、数据处理与文件操作能力的 H# 程序。")

    # ================================================================
    # 第5章 数据类型
    # ================================================================
    H.h2("第5章 数据类型")
    H.para("数据类型决定了数据在程序中的表示方式与可执行的操作。H# 是动态类型语言,"
           "变量无需声明类型,运行时根据值自动推断。本章详细介绍 H# 的基本数据类型"
           "(整数、浮点数、字符串、布尔、空值)以及容器类型(列表、字典)的入门用法,"
           "并讲解类型转换。")

    H.h3("5.1 整数")
    H.para("整数是没有小数部分的数字,可以是正数、负数或零。H# 的整数"
           "支持加减乘除等算术运算。")
    H.code(r'''let a = 42;
let b = -7;
let c = 0;
print(a);
print(b);
print(c);
print(a + b);
print(a * 2);''')
    H.output('''42
-7
0
35
84''')
    H.para("42 + (-7) = 35,42 * 2 = 84。整数运算的结果仍为整数(除法除外,见 6.2 节)。"
           "H# 的整数没有大小限制,可以表示任意大的整数(继承自 Python)。")

    H.h3("5.2 浮点数")
    H.para("浮点数是带小数部分的数字,用于表示实数。H# 的浮点数采用双精度表示。")
    H.code(r'''let pi = 3.14;
let g = 9.8;
let neg = -0.5;
print(pi);
print(g);
print(neg);
print(1.5 + 2.5);
print(pi * 2);''')
    H.output('''3.14
9.8
-0.5
4.0
6.28''')
    H.para("1.5 + 2.5 = 4.0(注意结果是浮点数 4.0 而非整数 4),3.14 * 2 = 6.28。"
           "当整数与浮点数混合运算时,结果自动提升为浮点数。")
    H.warning("浮点数在计算机中以二进制存储,某些小数无法精确表示,可能出现精度误差。"
              "例如 0.1 + 0.2 的结果可能不是精确的 0.3。这是所有编程语言的共性问题。")

    H.h3("5.3 字符串")
    H.para("字符串是文本数据的表示方式,用双引号 \"\" 包裹。字符串支持拼接(+)、"
           "索引([])和长度查询(len)等操作。字符串的详细用法见第8章。")
    H.code(r'''let s1 = "Hello";
let s2 = "World";
print(s1 + " " + s2);
print(len(s1));
print(s1[0]);''')
    H.output('''Hello World
5
H''')
    H.para("\"Hello\" + \" \" + \"World\" 拼接得到 \"Hello World\"。len(s1) 返回"
           "字符串长度 5。s1[0] 取第一个字符 \"H\"(索引从 0 开始)。")

    H.h3("5.4 布尔")
    H.para("布尔类型只有两个值:true(真)和 false(假),用于逻辑判断。"
           "布尔值支持 and(与)、or(或)、not(非)三种逻辑运算。")
    H.code(r'''let t = true;
let f = false;
print(t);
print(f);
print(t and f);
print(t or f);
print(not t);''')
    H.output('''True
False
False
True
False''')
    H.para("true and false = false(两者都为真才为真);true or false = true"
           "(只要有一个为真即为真);not true = false(取反)。"
           "注意输出显示为 True/False(Python 解释器风格),源码中写小写 true/false。")

    H.h3("5.5 null")
    H.para("nullptr 是 H# 的空值字面量,表示\"没有值\"或\"未知值\"。它常用于"
           "表示变量尚未赋值、函数无返回值或查找失败等场景。")
    H.code(r'''let nothing = nullptr;
print(nothing);
print(nothing == nullptr);''')
    H.output('''None
True''')
    H.para("nullptr 在 Python 解释器中输出为 None。可以用 == 判断一个值是否为 "
           "nullptr:nothing == nullptr 的结果为 true。")

    H.h3("5.6 列表")
    H.para("列表是有序的数据集合,用方括号 [] 创建,元素之间用逗号分隔。"
           "列表可以包含任意类型的元素,支持添加(push)、删除(pop)、"
           "索引访问和长度查询等操作。列表的深入用法见后续章节。")
    H.code(r'''let fruits = ["apple", "banana", "cherry"];
print(fruits);
print(len(fruits));
print(fruits[0]);
push(fruits, "date");
print(fruits);
let last = pop(fruits);
print(last);
print(fruits);''')
    H.output('''['apple', 'banana', 'cherry']
3
apple
['apple', 'banana', 'cherry', 'date']
date
['apple', 'banana', 'cherry']''')
    H.para("创建列表 [\"apple\", \"banana\", \"cherry\"] 后:len 返回元素个数 3;"
           "fruits[0] 取第一个元素 \"apple\";push(fruits, \"date\") 在末尾添加 \"date\";"
           "pop(fruits) 移除并返回末尾元素 \"date\"。注意 push 和 pop 会直接修改原列表。")

    H.h3("5.7 字典")
    H.para("字典是键值对(key-value)的集合,用花括号 {} 创建。每个键唯一对应一个值。"
           "字典通过键快速查找值,支持 dict_keys、dict_values、dict_items 等操作。")
    H.code(r'''let scores = {"math": 90, "english": 85};
print(scores);
print(scores["math"]);
print(dict_has(scores, "math"));
print(dict_keys(scores));
print(dict_values(scores));''')
    H.output('''{'math': 90, 'english': 85}
90
True
['math', 'english']
[90, 85]''')
    H.para("创建字典后:scores[\"math\"] 通过键 \"math\" 取出值 90;"
           "dict_has 检查键是否存在;dict_keys 返回所有键组成的列表;"
           "dict_values 返回所有值组成的列表。")

    H.h3("5.8 类型推断")
    H.para("H# 是动态类型语言,变量类型由运行时推断,无需显式声明。"
           "同一个 let 关键字可以根据赋值表达式的不同,推断出不同的类型:")
    H.bullet("let x = 42; — x 被推断为整数")
    H.bullet("let x = 3.14; — x 被推断为浮点数")
    H.bullet("let x = \"hello\"; — x 被推断为字符串")
    H.bullet("let x = true; — x 被推断为布尔值")
    H.bullet("let x = [1, 2]; — x 被推断为列表")
    H.bullet("let x = {\"k\": 1}; — x 被推断为字典")
    H.para("类型推断让代码保持简洁。在赋值时,值的形态决定了变量的类型——"
           "整数赋值得到整数类型,字符串赋值得到字符串类型,依此类推。"
           "重新赋值时,变量的类型也会随新值自动变化。")

    H.h3("5.9 类型转换")
    H.para("H# 提供 str()、int()、float() 三个内置函数实现类型转换。"
           "它们可以将一种类型的值转换为另一种类型,在数据格式处理中非常常用。")
    H.code(r'''print(str(42));
print(str(3.14));
print(str(true));
print(int("123"));
print(int(3.9));
print(float("2.5"));
print(float(5));''')
    H.output('''42
3.14
True
123
3
2.5
5.0''')
    H.para("各函数的行为如下:")
    H.bullet("str(42) → \"42\":将整数转为字符串。str(true) → \"True\"。")
    H.bullet("int(\"123\") → 123:将数字字符串转为整数。int(3.9) → 3:浮点数转整数时截断小数部分。")
    H.bullet("float(\"2.5\") → 2.5:将数字字符串转为浮点数。float(5) → 5.0:整数转浮点数。")
    H.note("int() 转换浮点数时是截断(向零取整)而非四舍五入:int(3.9) = 3,int(-3.9) = -3。"
           "如需四舍五入,可以先用 float 加 0.5 再取整(正数情况)。")

    H.h3("本章小结")
    H.para("本章介绍了 H# 的数据类型体系。基本类型包括整数、浮点数、字符串、"
           "布尔和空值(nullptr);容器类型包括列表和字典。H# 通过类型推断自动确定"
           "变量类型,并通过 str()、int()、float() 实现类型转换。理解每种类型的特点"
           "与可执行的操作,是编写正确程序的前提。")

    H.h3("练习题")
    H.number("声明整数、浮点数、字符串、布尔和空值各一个变量,输出它们的值。")
    H.number("创建一个包含 5 个数字的列表,用 push 添加第 6 个元素,再 pop 移除最后一个。")
    H.number("创建一个字典存储三种商品及其价格,用 dict_keys 和 dict_values 分别输出键和值。")
    H.number("用 int() 和 float() 将字符串 \"42.99\" 分别转换为整数和浮点数,观察结果差异。")
    H.page_break()

    # ================================================================
    # 第6章 运算符
    # ================================================================
    H.h2("第6章 运算符")
    H.para("运算符是对数据进行操作的符号。H# 提供了丰富的运算符,包括算术运算符、"
           "比较运算符、逻辑运算符和赋值运算符。本章详细讲解各类运算符的用法,"
           "并重点剖析 H# 整数除法的特性与运算符优先级规则。")

    H.h3("6.1 算术运算符")
    H.para("H# 支持五种算术运算符:加(+)、减(-)、乘(*)、除(/)、取模(%)。")
    H.code(r'''print(10 + 3);
print(10 - 3);
print(10 * 3);
print(10 / 3);
print(10 % 3);''')
    H.output('''13
7
30
3
1''')
    H.para("10 + 3 = 13,10 - 3 = 7,10 * 3 = 30,10 / 3 = 3(整数除法,见下节),"
           "10 % 3 = 1(10 除以 3 的余数)。取模运算 % 常用于判断奇偶性:"
           "n % 2 == 0 表示 n 是偶数。")

    H.h3("6.2 整数除法特性详解")
    H.para("H# 的除法运算有一个重要特性:当两个操作数都是整数时,执行整数除法"
           "(向下取整),结果为整数;当至少一个操作数为浮点数时,执行浮点除法,"
           "结果为浮点数。这与 Python 2 的行为一致,但不同于 Python 3。")
    H.code(r'''print(7 / 2);
print(7.0 / 2);
print(9 / 4);
print(9.0 / 4);
print(100 / 10);
print(-7 / 2);''')
    H.output('''3
3.5
2
2.25
10
-4''')
    H.para("逐行分析:")
    H.bullet("7 / 2 = 3:两个整数相除,整数除法,3.5 截断为 3。")
    H.bullet("7.0 / 2 = 3.5:有浮点数参与,浮点除法,结果 3.5。")
    H.bullet("9 / 4 = 2:整数除法,2.25 截断为 2。")
    H.bullet("9.0 / 4 = 2.25:浮点除法。")
    H.bullet("100 / 10 = 10:恰好整除。")
    H.bullet("-7 / 2 = -4:负数整数除法向负无穷方向取整,-3.5 变为 -4。")
    H.warning("整数除法对负数是向负无穷取整(地板除),而非向零取整。"
              "-7 / 2 = -4 而非 -3。这一点与 C/Java 的截断除法不同,需特别注意。"
              "如果需要浮点结果,将其中一个操作数写成浮点数即可。")

    H.h3("6.3 比较运算符")
    H.para("比较运算符用于比较两个值的大小或是否相等,返回布尔值 true 或 false。"
           "H# 支持六种比较运算符:等于(==)、不等于(!=)、大于(>)、"
           "小于(<)、大于等于(>=)、小于等于(<=)。")
    H.code(r'''print(5 == 5);
print(5 != 3);
print(8 > 3);
print(3 < 8);
print(5 >= 5);
print(5 <= 4);
print("abc" == "abc");
print("abc" != "abd");''')
    H.output('''True
True
True
True
True
False
True
True''')
    H.para("比较运算符不仅用于数字,也用于字符串。\"abc\" == \"abc\" 为 true"
           "(内容相同),\"abc\" != \"abd\" 为 true(内容不同)。"
           "字符串比较区分大小写:\"abc\" != \"ABC\"。")

    H.h3("6.4 逻辑运算符")
    H.para("逻辑运算符用于组合布尔表达式。H# 提供三种逻辑运算符:"
           "and(逻辑与)、or(逻辑或)、not(逻辑非),使用短路求值策略。")
    H.code(r'''print(true and true);
print(true and false);
print(false or true);
print(false or false);
print(not true);
print(not false);''')
    H.output('''True
False
True
False
False
True''')
    H.para("短路求值是指:对于 a and b,如果 a 为 false,则直接返回 false,不再计算 b;"
           "对于 a or b,如果 a 为 true,则直接返回 true,不再计算 b。"
           "短路求值可以避免不必要的计算,也能防止潜在的错误:")
    H.code(r'''let n = 0;
if (n != 0 and 10 / n > 1) {
    print("不会执行");
} else {
    print("短路保护成功");
}''')
    H.output('''短路保护成功''')
    H.para("当 n = 0 时,n != 0 为 false,由于短路求值,10 / n 不会被计算,"
           "从而避免了除零错误。如果不会短路,10 / 0 会导致运行时崩溃。")

    H.h3("6.5 赋值运算符")
    H.para("H# 使用等号 = 作为赋值运算符。它将右侧表达式的值赋给左侧的变量。"
           "赋值运算可以链式组合,也支持复合赋值模式(通过自引用表达式实现)。")
    H.code(r'''let v = 10;
print(v);
v = 20;
print(v);
v = v + 5;
print(v);
v = v * 2;
print(v);''')
    H.output('''10
20
25
50''')
    H.para("v = v + 5 是\"自增赋值\"——将 v 当前值加 5 后再赋给 v。"
           "同理 v = v * 2 是\"自乘赋值\"。H# 目前不提供 +=、*= 等"
           "复合赋值运算符简写,需用完整表达式 v = v + 5 的形式。")

    H.h3("6.6 运算符优先级")
    H.para("当表达式中出现多个运算符时,优先级决定了运算的先后顺序。"
           "H# 的运算符优先级从高到低为:")
    H.number("括号 () — 最高优先级,可以改变默认运算顺序")
    H.number("一元运算符(not、负号 -)— 如 not x、-5")
    H.number("乘除取模(* / %)— 高于加减")
    H.number("加减(+ -)")
    H.number("比较(== != < > <= >=)")
    H.number("逻辑与(and)— 高于或")
    H.number("逻辑或(or)— 最低")
    H.para("通过示例验证优先级规则:")
    H.code(r'''print(2 + 3 * 4);
print((2 + 3) * 4);
print(10 - 2 - 3);
print(2 + 3 == 5);
print(true or false and false);
print(not true or false);''')
    H.output('''14
20
5
True
True
False''')
    H.para("逐行分析:")
    H.bullet("2 + 3 * 4 = 14:先算 3*4=12,再算 2+12=14(乘法优先于加法)。")
    H.bullet("(2 + 3) * 4 = 20:括号改变优先级,先算 2+3=5,再算 5*4=20。")
    H.bullet("10 - 2 - 3 = 5:同级运算从左到右,先 10-2=8,再 8-3=5。")
    H.bullet("2 + 3 == 5 = True:先算 2+3=5,再比较 5==5 得 True。")
    H.bullet("true or false and false = True:and 优先于 or,先算 false and false = false,"
             "再算 true or false = True。")
    H.bullet("not true or false = False:not 优先于 or,先算 not true = false,"
             "再算 false or false = False。")
    H.note("当不确定优先级时,使用括号 () 显式指定运算顺序是最安全的做法。"
           "这不仅能避免错误,还能提升代码可读性。")

    H.h3("本章小结")
    H.para("本章介绍了 H# 的运算符体系。算术运算符(+ - * / %)中,整数除法是重点"
           "——两整数相除得整数(向下取整)。比较运算符返回布尔值。逻辑运算符"
           "(and/or/not)采用短路求值。运算符优先级从高到低为:括号 > 一元 > "
           "乘除模 > 加减 > 比较 > and > or。不确定时请用括号。")

    H.h3("练习题")
    H.number("计算 17 / 5 和 17.0 / 5,观察整数除法与浮点除法的区别。")
    H.number("用取模运算判断数字 17 是奇数还是偶数,输出判断结果。")
    H.number("验证短路求值:设计一个表达式,利用 and 短路避免除零错误。")
    H.number("不使用括号,计算 true or true and false 的结果,再用括号验证优先级。")
    H.number("用 v = v * n 的方式实现计算 2 的 10 次方(循环 10 次)。")
    H.page_break()

    # ================================================================
    # 第7章 控制流
    # ================================================================
    H.h2("第7章 控制流")
    H.para("控制流决定了程序执行的路径。H# 提供了条件分支(if/else if/else)、"
           "循环(while、for-in)和跳转(break、continue)等控制流结构。"
           "本章通过经典示例(九九乘法表、斐波那契数列)帮助你掌握这些结构。")

    H.h3("7.1 if / else if / else")
    H.para("if 语句根据条件决定执行哪个代码块。else if 用于多条件分支,"
           "else 处理所有未匹配的情况。条件表达式必须用括号 () 包裹。")
    H.code(r'''let score = 85;
if (score >= 90) {
    print("优秀");
} else if (score >= 80) {
    print("良好");
} else if (score >= 70) {
    print("中等");
} else if (score >= 60) {
    print("及格");
} else {
    print("不及格");
}''')
    H.output('''良好''')
    H.para("score = 85,首先检查 >= 90(不满足),再检查 >= 80(满足),输出\"良好\"。"
           "一旦某个条件满足,执行对应代码块后跳过后续所有分支。"
           "else if 可以有任意多个,else 是可选的。")

    H.h3("7.2 while 循环")
    H.para("while 循环在条件为 true 时重复执行代码块。每次循环前检查条件,"
           "条件为 false 时退出循环。while 适合循环次数不确定的场景。")
    H.code(r'''let i = 1;
let sum = 0;
while (i <= 10) {
    sum = sum + i;
    i = i + 1;
}
print("1到10的和: " + str(sum));''')
    H.output('''1到10的和: 55''')
    H.para("这个程序计算 1+2+3+...+10 的和。i 从 1 开始,每次循环将 i 加到 sum 上,"
           "然后 i 自增 1。当 i 超过 10 时,条件 i <= 10 为 false,循环结束。"
           "结果为 55。")
    H.warning("while 循环必须确保条件最终会变为 false,否则会形成无限循环。"
              "常见做法是在循环体内修改变量(如 i = i + 1),使条件逐步趋向 false。")

    H.h3("7.3 for-in 循环(列表)")
    H.para("for-in 循环用于遍历可迭代对象(如列表、字符串)。每次循环取出一个元素,"
           "赋值给循环变量,执行代码块。for-in 比while 更简洁,适合已知集合的遍历。")
    H.code(r'''let colors = ["red", "green", "blue"];
for c in colors {
    print(c);
}''')
    H.output('''red
green
blue''')
    H.para("循环变量 c 依次取列表中的 \"red\"、\"green\"、\"blue\",每次输出当前颜色。"
           "for-in 循环自动处理迭代,无需手动管理索引,代码更简洁、不易出错。")

    H.h3("7.4 for-in 遍历字典(k, v)")
    H.para("遍历字典时,for-in 可以同时获取键和值。语法为 for 键, 值 in 字典 { ... }。"
           "这使得字典遍历非常直观。")
    H.code(r'''let book = {"title": "H#入门", "price": 59, "pages": 300};
for k, v in book {
    print(k + ": " + str(v));
}''')
    H.output('''title: H#入门
price: 59
pages: 300''')
    H.para("每次循环,k 获取键(如 \"title\"),v 获取对应的值(如 \"H#入门\")。"
           "str(v) 将值转为字符串以便拼接。注意字典的遍历顺序不保证与定义顺序一致。")

    H.h3("7.5 break 和 continue")
    H.para("break 立即终止当前循环,跳出循环体。continue 跳过本次循环剩余代码,"
           "直接进入下一次循环。这两个关键字可以更灵活地控制循环流程。")
    H.code(r'''for x in [1, 2, 3, 4, 5, 6, 7, 8] {
    if (x == 3) {
        continue;
    }
    if (x == 7) {
        break;
    }
    print(x);
}''')
    H.output('''1
2
4
5
6''')
    H.para("当 x == 3 时,continue 跳过本次循环(不输出 3),进入下一次循环。"
           "当 x == 7 时,break 终止整个循环(不输出 7 和 8)。"
           "因此输出 1、2、4、5、6——跳过了 3,在 7 处中断。")

    H.h3("7.6 嵌套循环")
    H.para("循环可以嵌套使用——外层循环的每次迭代中,内层循环完整执行一遍。"
           "嵌套循环常用于处理二维数据、生成乘法表等场景。")
    H.para("经典示例:九九乘法表(此处展示前 3 行):")
    H.code(r'''for i in [1, 2, 3] {
    for j in [1, 2, 3, 4, 5] {
        print(str(i) + "x" + str(j) + "=" + str(i * j));
    }
}''')
    H.output('''1x1=1
1x2=2
1x3=3
1x4=4
1x5=5
2x1=2
2x2=4
2x3=6
2x4=8
2x5=10
3x1=3
3x2=6
3x3=9
3x4=12
3x5=15''')
    H.para("外层循环变量 i 取 1、2、3,内层循环变量 j 取 1 到 5。"
           "每次组合 i 和 j,输出乘法表达式。当 i=1 时,j 遍历 1-5;"
           "然后 i=2,j 再次遍历 1-5,依此类推。")

    H.para("另一个经典示例:斐波那契数列。该数列从 0 和 1 开始,"
           "每个后续数字是前两个数字之和:0, 1, 1, 2, 3, 5, 8, 13, 21, 34, ...")
    H.code(r'''let a = 0;
let b = 1;
let count = 0;
while (count < 10) {
    print(a);
    let temp = a + b;
    a = b;
    b = temp;
    count = count + 1;
}''')
    H.output('''0
1
1
2
3
5
8
13
21
34''')
    H.para("算法思路:a 和 b 分别代表数列中相邻的两个数。每次循环:输出 a,"
           "计算下一个数 temp = a + b,然后将 a 更新为 b,b 更新为 temp。"
           "count 计数,循环 10 次后输出前 10 个斐波那契数。")

    H.h3("本章小结")
    H.para("本章介绍了 H# 的控制流结构。if/else if/else 实现条件分支;"
           "while 在条件为 true 时循环;for-in 遍历列表和字典;"
           "break 跳出循环,continue 跳过本次迭代;嵌套循环处理多维问题。"
           "通过九九乘法表和斐波那契数列两个经典示例,你应当已能灵活运用这些结构。")

    H.h3("练习题")
    H.number("编写程序,输入一个分数(用变量模拟),输出对应等级(A/B/C/D)。")
    H.number("用 while 循环计算 1 到 100 中所有偶数的和。")
    H.number("用 for-in 遍历一个包含 5 个名字的列表,输出每个名字及其长度。")
    H.number("用嵌套循环打印完整的九九乘法表(1x1 到 9x9)。")
    H.number("用 while 循环生成斐波那契数列的前 20 项。")
    H.number("用 break 编写程序:在列表 [3, 7, 2, 9, 5] 中找到第一个大于 5 的数并输出。")
    H.page_break()

    # ================================================================
    # 第8章 字符串详解
    # ================================================================
    H.h2("第8章 字符串详解")
    H.para("字符串是编程中最常用的数据类型之一。本章深入讲解 H# 字符串的各个方面:"
           "字面量、拼接、索引、切片、字符编码(ord/chr)、遍历与转义字符。"
           "掌握字符串操作是处理文本数据的基础。")

    H.h3("8.1 字符串字面量")
    H.para("H# 的字符串字面量使用双引号 \"\" 包裹。双引号内的所有字符(包括空格、"
           "中文、特殊符号)都是字符串的内容。")
    H.code(r'''let s1 = "Hello";
let s2 = "H# Language";
print(s1);
print(s2);''')
    H.output('''Hello
H# Language''')
    H.para("字符串可以包含中文、空格和特殊符号。H# 目前仅支持双引号字符串,"
           "不支持单引号字符串(单引号 ' 会被解释器视为非法字符)。")
    H.warning("H# 字符串只能用双引号 \"\" 包裹。如果需要在字符串中包含双引号本身,"
              "请使用转义字符 \\\",详见 8.7 节。")

    H.h3("8.2 字符串拼接(+)")
    H.para("使用 + 运算符可以将多个字符串拼接为一个。拼接时,+ 两边的操作数"
           "必须是字符串——如果需要拼接数字,先用 str() 转换。")
    H.code(r'''let first = "Hello";
let second = "World";
let combined = first + ", " + second + "!";
print(combined);
print("Say: " + combined);''')
    H.output('''Hello, World!
Say: Hello, World!''')
    H.para("\"Hello\" + \", \" + \"World\" + \"!\" 逐步拼接得到 \"Hello, World!\"。"
           "字符串拼接是构建动态文本的主要手段,在输出格式化信息时非常常用。")

    H.h3("8.3 字符串索引与长度(len)")
    H.para("字符串中的每个字符都有一个索引,从 0 开始。通过方括号 [] 加索引"
           "可以访问单个字符。len() 函数返回字符串的长度(字符个数)。")
    H.code(r'''let s = "H#Sharp";
print(len(s));
print(s[0]);
print(s[1]);
print(s[2]);
print(s[6]);''')
    H.output('''7
H
#
S
p''')
    H.para("\"H#Sharp\" 共 7 个字符:s[0]='H', s[1]='#', s[2]='S', s[6]='p'(最后一个字符)。"
           "索引从 0 开始,因此最后一个字符的索引是 len(s)-1 = 6。"
           "注意 H# 的字符串索引目前不支持负数索引(如 s[-1])。")

    H.h3("8.4 substring(s, start, length) 切片")
    H.para("substring 是 H# 的内置函数,用于提取字符串的子串。"
           "它接收三个参数:substring(字符串, 起始位置, 截取长度)。"
           "注意第三个参数是\"长度\"而非\"结束位置\"。")
    H.code(r'''let text = "Hello World";
print(substring(text, 0, 5));
print(substring(text, 6, 5));
print(substring(text, 0, 11));
print(substring(text, 3, 4));''')
    H.output('''Hello
World
Hello World
lo W''')
    H.para("逐行分析(substring(字符串, 起始, 长度)):")
    H.bullet("substring(text, 0, 5) = \"Hello\":从位置 0 开始截取 5 个字符。")
    H.bullet("substring(text, 6, 5) = \"World\":从位置 6 开始截取 5 个字符。")
    H.bullet("substring(text, 0, 11) = \"Hello World\":从位置 0 截取全部 11 个字符。")
    H.bullet("substring(text, 3, 4) = \"lo W\":从位置 3 截取 4 个字符(包含空格)。")
    H.note("substring 的第三个参数是\"截取长度\",不是\"结束索引\"。"
           "这与某些语言的 substring(s, start, end) 不同。"
           "如果长度超过可用字符,自动截取到字符串末尾,不会报错。")

    H.h3("8.5 ord(s) 与 chr(n)")
    H.para("ord 和 chr 是字符与 ASCII/Unicode 编码之间的转换函数。"
           "ord(字符) 返回该字符的编码值(整数);chr(编码值) 返回对应的字符。"
           "这两个函数在字符处理、加密解密等场景中很有用。")
    H.code(r'''print(ord("A"));
print(ord("a"));
print(ord("0"));
print(chr(65));
print(chr(97));
print(chr(48));''')
    H.output('''65
97
48
A
a
0''')
    H.para("大写字母 A 的 ASCII 码是 65,小写 a 是 97,数字字符 0 是 48。"
           "反之,chr(65) 返回 'A',chr(97) 返回 'a',chr(48) 返回 '0'。"
           "利用 ord 和 chr 可以实现字母大小写转换等操作:"
           "大写转小写 = chr(ord(c) + 32),小写转大写 = chr(ord(c) - 32)。")

    H.h3("8.6 字符串遍历")
    H.para("可以用 for-in 循环遍历字符串中的每个字符。这在逐字符处理文本时非常方便。")
    H.code(r'''let word = "ABC";
for ch in word {
    print(ch);
}''')
    H.output('''A
B
C''')
    H.para("循环变量 ch 依次取字符串中的每个字符 'A'、'B'、'C'。"
           "结合 ord 函数,可以输出每个字符的编码值:")
    H.code(r'''let msg = "Hi";
for c in msg {
    print(c + " -> " + str(ord(c)));
}''')
    H.output('''H -> 72
i -> 105''')
    H.para("H 的编码是 72,i 的编码是 105。这种遍历方式在分析文本内容时很实用。")

    H.h3("8.7 转义字符")
    H.para("转义字符以反斜杠 \\ 开头,用于在字符串中表示特殊字符。"
           "H# 支持以下转义字符:")
    H.bullet("\\n — 换行符,将光标移到下一行开头")
    H.bullet("\\\" — 双引号,在字符串中包含双引号本身")
    H.para("其他反斜杠组合(如 \\t、\\\\)不被特殊处理,会原样保留为字面文本。"
           "下面通过示例演示:")
    H.code(r'''print("第一行\n第二行");
print("引号:\"hello\"");
print("路径C:\\Users");''')
    H.output('''第一行
第二行
引号:"hello"
路径C:\\Users''')
    H.para("第一行:\"\\n\" 被解释为换行,输出分两行。"
           "第二行:\"\\\"\" 被解释为普通双引号,输出引号:\"hello\"。"
           "第三行:\"\\\\\" 不被特殊解释,原样输出两个反斜杠 \\\\。")
    H.warning("H# 仅支持 \\n(换行)和 \\\"(双引号)两种转义序列。"
              "不要期望 \\t(制表符)或 \\\\(反斜杠)会被特殊处理——"
              "它们会原样输出。如需制表符对齐,建议用空格代替。")

    H.h3("本章小结")
    H.para("本章详细介绍了 H# 字符串操作。字符串用双引号包裹;用 + 拼接;"
           "用 [] 索引(从 0 开始),len() 取长度;substring(s, start, length) "
           "截取子串(第三参数为长度);ord/chr 在字符与编码间转换;"
           "for-in 遍历每个字符;转义字符仅支持 \\n 和 \\\"。")

    H.h3("练习题")
    H.number("声明字符串 \"Hello H#\",输出其长度和第一个字符。")
    H.number("用 substring 从 \"Programming\" 中截取 \"gram\"(从位置 3 开始,长度 4)。")
    H.number("用 ord 和 chr 将小写字母 'd' 转换为大写 'D'(提示:小写比大写大 32)。")
    H.number("遍历字符串 \"abc\",输出每个字符及其 ASCII 码。")
    H.number("用 \\n 转义字符在一行 print 中输出三行文字。")
    H.page_break()

    # ================================================================
    # 第9章 输入输出
    # ================================================================
    H.h2("第9章 输入输出")
    H.para("输入输出(I/O)是程序与外部世界交互的桥梁。本章介绍 H# 的 print 输出、"
           "字符串格式化技巧,以及文件读写(write_file/read_file)。"
           "通过本章,你将能够编写与用户交互、处理文件的实用程序。")

    H.h3("9.1 print 详解")
    H.para("print 是 H# 最常用的内置函数,用于将数据输出到终端。"
           "它可以输出各种类型的数据:字符串、数字、布尔值、列表等。"
           "每次调用 print 会自动在末尾换行。")
    H.code(r'''print("Hello");
print(42);
print(3.14);
print(true);
print([1, 2, 3]);
let x = 10;
print(x);
print(x + 5);''')
    H.output('''Hello
42
3.14
True
[1, 2, 3]
10
15''')
    H.para("print 接受一个参数,将其输出。字符串原样输出;整数和浮点数直接显示;"
           "布尔值显示为 True/False;列表显示为 [元素1, 元素2, ...] 格式。"
           "也可以输出变量或表达式的值。")
    H.note("print 每次输出后自动换行。如果不想换行,目前没有直接的参数控制——"
           "可以将多段内容拼接为一个字符串后一次性输出。")

    H.h3("9.2 字符串拼接输出")
    H.para("在实际编程中,经常需要将变量值与说明文字组合输出。"
           "通过字符串拼接(+)和 str() 转换可以实现这一需求。"
           "核心原则:拼接前将非字符串用 str() 转为字符串。")
    H.code(r'''let name = "Alice";
let age = 25;
print("姓名: " + name);
print("年龄: " + str(age));
print(name + " 今年 " + str(age) + " 岁");''')
    H.output('''姓名: Alice
年龄: 25
Alice 今年 25 岁''')
    H.para("name 已经是字符串,可以直接拼接。age 是整数,必须先用 str(age) 转为字符串"
           "才能拼接。第三行综合运用:将姓名、说明文字、年龄拼接为一句完整的输出。"
           "这是 H# 中最常用的输出格式化方式。")

    H.h3("9.3 格式化技巧(用 str() 转换)")
    H.para("H# 没有类似 C 的 printf 格式化或 Python 的 f-string,但通过 str() "
           "和字符串拼接可以实现灵活的格式化输出。关键是将所有非字符串数据"
           "转换为字符串后拼接。")
    H.code(r'''let price = 19.99;
let qty = 3;
let total = price * qty;
print("单价: " + str(price));
print("数量: " + str(qty));
print("总价: " + str(total));
print("================");
print("商品: 苹果");
print("单价: " + str(price) + " 元");
print("数量: " + str(qty) + " 个");
print("合计: " + str(total) + " 元");''')
    H.output('''单价: 19.99
数量: 3
总价: 59.97
================
商品: 苹果
单价: 19.99 元
数量: 3 个
合计: 59.97 元''')
    H.para("这个示例模拟了一个购物小票的输出。先计算总价 total = price * qty = 59.97,"
           "然后用 str() 将数字转为字符串,拼接单位(\"元\"、\"个\")和分隔线,"
           "输出格式整齐的收据信息。这种\"拼接 + str()\"的方式虽然比 f-string 稍显繁琐,"
           "但逻辑清晰,适用于所有场景。")

    H.h3("9.4 read_file / write_file 文件读写")
    H.para("H# 提供 write_file 和 read_file 两个内置函数进行文件 I/O。"
           "write_file(文件路径, 内容) 将字符串写入文件(覆盖已有内容);"
           "read_file(文件路径) 读取文件全部内容并返回字符串。")
    H.code(r'''write_file("/tmp/hs_book_test.txt", "第一行内容\n第二行内容\n第三行内容\n");
let content = read_file("/tmp/hs_book_test.txt");
print(content);
print("文件长度: " + str(len(content)));''')
    H.output('''第一行内容
第二行内容
第三行内容

文件长度: 18''')
    H.para("write_file 将三行文字写入文件(用 \\n 分隔行)。read_file 读回全部内容,"
           "包括换行符。len(content) 返回文件内容的总字符数 18"
           "(每行 5 个汉字 + 1 个换行 = 6,三行共 18)。"
           "注意输出中的空行是文件末尾最后一个 \\n 产生的。")
    H.para("下面再看一个实用示例:将数字写入文件,读回后转为整数参与运算:")
    H.code(r'''write_file("/tmp/hs_num.txt", str(42));
let num = read_file("/tmp/hs_num.txt");
print("读回的数字: " + num);
print("转成整数: " + str(int(num) + 8));''')
    H.output('''读回的数字: 42
转成整数: 50''')
    H.para("先将数字 42 用 str() 转为字符串写入文件。读回时得到字符串 \"42\","
           "再用 int() 转为整数后参与运算:int(\"42\") + 8 = 50。"
           "这种\"写入 → 读回 → 转换\"的模式在数据持久化中很常见。")
    H.warning("write_file 采用覆盖模式:如果文件已存在,旧内容会被完全替换。"
              "如需追加内容,需要先 read_file 读回旧内容,拼接新内容后再 write_file 写入。"
              "文件路径可以是绝对路径(如 /tmp/x.txt)或相对路径。")

    H.h3("9.5 命令行参数简介")
    H.para("H# 解释器目前主要面向脚本与教学场景,命令行参数的能力较为基础。"
           "程序可以通过 read_file 读取配置文件,或通过 write_file 输出结果文件,"
           "实现与外部系统的数据交换。对于需要交互式输入的场景,可以使用 input() "
           "函数从标准输入读取一行文本。")
    H.para("一个典型的 H# 程序工作流程如下:")
    H.number("通过 read_file 读取输入数据或配置文件")
    H.number("用 str/int/float 等函数解析和转换数据")
    H.number("进行计算与业务逻辑处理")
    H.number("通过 print 输出结果到终端,或用 write_file 写入结果文件")
    H.para("这种\"文件驱动\"的模式简单可靠,适用于大多数脚本自动化任务。")

    H.h3("本章小结")
    H.para("本章介绍了 H# 的输入输出机制。print 输出各种类型数据,每次自动换行;"
           "通过 str() 转换 + 字符串拼接实现格式化输出;write_file/read_file "
           "实现文件写入与读取;命令行交互以文件驱动模式为主。"
           "输入输出是程序实用化的关键,掌握它们后,你已能编写有实际价值的 H# 程序。")

    H.h3("练习题")
    H.number("编写程序,用 print 输出整数、浮点数、布尔值和列表各一个。")
    H.number("用 str() 拼接输出一条格式化的学生信息:姓名、年龄、成绩。")
    H.number("编写一个\"购物小票\"程序:定义商品名、单价、数量,计算总价并格式化输出。")
    H.number("用 write_file 将一段文字写入文件,再用 read_file 读回并输出文件长度。")
    H.number("将数字 100 写入文件,读回后转为整数,计算其平方根的近似值并输出。")
    H.page_break()
