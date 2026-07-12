# -*- coding: utf-8 -*-
"""《H# 从入门到精通》第三篇(函数式编程)+ 第四篇(面向对象)内容生成

本文件包含第 10-17 章的全部正文内容。所有代码示例均通过
`python3 interpreter.py file.hto` 实机测试。
"""


def add_content(doc, H):
    # H.h1(text)        篇标题(大标题,居中,自动分页)
    # H.h2(text)        章标题
    # H.h3(text)        节标题
    # H.para(text)      正文段落
    # H.code(text)      代码块(多行字符串)
    # H.output(text)    程序输出(绿色)
    # H.note(text)      提示(橙色斜体)
    # H.warning(text)   警告(红色粗体)
    # H.bullet(text)    项目符号
    # H.number(text)    编号列表项
    # H.page_break()    分页
    # H.blank()         空行

    # ============================================================
    # 第三篇 函数式编程
    # ============================================================
    H.h1("第三篇 函数式编程")

    H.para(
        "函数式编程是 H# 最重要的编程范式之一。H# 把函数视为一等公民(first-class citizen),"
        "函数既可以作为参数传递,也可以作为返回值返回,还可以保存在变量和数据结构中。"
        "本篇将系统讲解函数定义、作用域、闭包、Lambda 表达式,以及函数式编程的工程实践。"
    )
    H.para(
        "学习完本篇,你将能够编写出简洁、可复用、易测试的函数式代码,并理解 H# 闭包捕获的底层机制,"
        "为后续学习面向对象和并发编程打下坚实基础。"
    )

    # ============================================================
    # 第10章 函数定义与调用
    # ============================================================
    H.h2("第10章 函数定义与调用")

    H.para(
        "函数是组织代码的基本单位。通过函数,我们可以把一段具有特定功能的代码封装起来,"
        "赋予名字,并在需要的地方反复调用。本章从最简单的函数定义出发,逐步讲解参数、返回值、"
        "默认参数、可变参数、递归以及函数作为值传递等核心概念。"
    )

    # --- 10.1 ---
    H.h3("10.1 fn 关键字定义函数")
    H.para(
        "在 H# 中,使用 fn 关键字定义函数。函数由函数名、参数列表和用花括号 {} 包裹的函数体组成。"
        "函数体内的语句以分号 ; 结尾。下面是一个最简单的函数定义与调用示例:"
    )
    H.code(
        "fn greet(name) {\n"
        "    print(\"Hello, \" + name + \"!\");\n"
        "}\n"
        "greet(\"Alice\");\n"
        "greet(\"Bob\");"
    )
    H.output(
        "Hello, Alice!\n"
        "Hello, Bob!"
    )
    H.para(
        "greet 是函数名,name 是形参。调用时传入的 \"Alice\"、\"Bob\" 是实参。"
        "函数体使用 print 输出问候语。函数定义本身不会执行,只有在被调用时才会运行。"
    )
    H.note("函数名必须以字母或下划线开头,建议使用小写字母加下划线的 snake_case 风格命名。")

    # --- 10.2 ---
    H.h3("10.2 参数与返回值")
    H.para(
        "函数可以接收多个参数,并用 return 语句返回计算结果。return 之后的语句不会被执行。"
        "如果函数没有 return 语句,或 return 后不跟表达式,则函数返回空值 nullptr。"
    )
    H.code(
        "fn add(a, b) {\n"
        "    return a + b;\n"
        "}\n"
        "let result = add(3, 4);\n"
        "print(result);"
    )
    H.output("7")
    H.para(
        "上例中,add 函数接收两个参数 a 和 b,通过 return 返回它们的和。"
        "调用 add(3, 4) 时,实参 3 和 4 分别绑定到形参 a 和 b,函数返回 7。"
    )
    H.para("return 语句会立即结束函数执行并返回值,因此常用于提前返回:")
    H.code(
        "fn check_age(age) {\n"
        "    if (age < 0) {\n"
        "        return \"invalid\";\n"
        "    }\n"
        "    if (age >= 18) {\n"
        "        return \"adult\";\n"
        "    }\n"
        "    return \"minor\";\n"
        "}\n"
        "print(check_age(20));\n"
        "print(check_age(15));\n"
        "print(check_age(-5));"
    )
    H.output(
        "adult\n"
        "minor\n"
        "invalid"
    )

    # --- 10.3 ---
    H.h3("10.3 函数调用")
    H.para(
        "函数调用通过 \"函数名(实参列表)\" 的形式完成。调用时实参按位置依次绑定到形参,"
        "因此实参的个数和顺序必须与形参一致。下面演示多参数函数的调用:"
    )
    H.code(
        "fn introduce(name, age, city) {\n"
        "    return name + \" is \" + age + \" years old, from \" + city;\n"
        "}\n"
        "print(introduce(\"Alice\", 30, \"Beijing\"));\n"
        "print(introduce(\"Bob\", 25, \"Shanghai\"));"
    )
    H.output(
        "Alice is 30 years old, from Beijing\n"
        "Bob is 25 years old, from Shanghai"
    )
    H.para(
        "函数可以在任何表达式中被调用,包括作为另一个函数的实参。"
        "这种嵌套调用是构建复杂逻辑的常用手段。"
    )

    # --- 10.4 ---
    H.h3("10.4 默认参数(通过判断 null 实现)")
    H.para(
        "H# 不直接支持在形参列表中写默认值(如 fn f(x = 10))。但我们可以通过判断参数是否为 nullptr"
        "来实现默认参数的效果:调用时若不想指定该参数,就传入 nullptr,函数内部检测到 nullptr 后使用默认值。"
    )
    H.code(
        "fn greet(name, greeting) {\n"
        "    if (greeting == nullptr) {\n"
        "        greeting = \"Hello\";\n"
        "    }\n"
        "    print(greeting + \", \" + name + \"!\");\n"
        "}\n"
        "greet(\"Alice\", nullptr);\n"
        "greet(\"Bob\", \"Hi\");\n"
        "greet(\"Carol\", \"Good morning\");"
    )
    H.output(
        "Hello, Alice!\n"
        "Hi, Bob!\n"
        "Good morning, Carol!"
    )
    H.note(
        "这种 \"null 检测\" 模式是 H# 实现默认参数的标准做法,简单且直观。"
        "调用方只需在不需指定时传入 nullptr 即可。"
    )

    # --- 10.5 ---
    H.h3("10.5 可变参数(用列表传递)")
    H.para(
        "当函数需要接收任意多个参数时,H# 推荐的做法是把它们打包成一个列表传入。"
        "这样函数内部可以用 for 循环遍历列表,处理所有参数。这种方式比变长参数语法更灵活、更可控。"
    )
    H.code(
        "fn sum_all(nums) {\n"
        "    let total = 0;\n"
        "    for n in nums {\n"
        "        total = total + n;\n"
        "    }\n"
        "    return total;\n"
        "}\n"
        "print(sum_all([1, 2, 3, 4, 5]));\n"
        "print(sum_all([10, 20]));\n"
        "print(sum_all([]));"
    )
    H.output(
        "15\n"
        "30\n"
        "0"
    )
    H.para(
        "上例中,sum_all 接收一个列表参数 nums,遍历求和。传入空列表时返回 0(初始值),"
        "体现了函数对边界情况的处理。"
    )

    # --- 10.6 ---
    H.h3("10.6 递归")
    H.para(
        "递归是指函数在函数体内部调用自身。递归必须有一个终止条件(也叫基线条件),"
        "否则会无限递归导致栈溢出。递归特别适合处理具有自相似结构的问题。"
    )
    H.para("经典示例一:阶乘。n 的阶乘 n! = n * (n-1) * ... * 1,且 0! = 1。")
    H.code(
        "fn factorial(n) {\n"
        "    if (n <= 1) {\n"
        "        return 1;\n"
        "    }\n"
        "    return n * factorial(n - 1);\n"
        "}\n"
        "print(factorial(5));\n"
        "print(factorial(10));"
    )
    H.output(
        "120\n"
        "3628800"
    )
    H.para(
        "当 n <= 1 时直接返回 1(终止条件);否则返回 n 乘以 (n-1) 的阶乘。"
        "factorial(5) 的展开过程是 5 * 4 * 3 * 2 * 1 = 120。"
    )
    H.para("经典示例二:斐波那契数列。fib(n) = fib(n-1) + fib(n-2),fib(0)=0, fib(1)=1。")
    H.code(
        "fn fib(n) {\n"
        "    if (n < 2) {\n"
        "        return n;\n"
        "    }\n"
        "    return fib(n - 1) + fib(n - 2);\n"
        "}\n"
        "print(fib(0));\n"
        "print(fib(1));\n"
        "print(fib(10));\n"
        "print(fib(15));"
    )
    H.output(
        "0\n"
        "1\n"
        "55\n"
        "610"
    )
    H.warning(
        "递归斐波那契的时间复杂度是 O(2^n),n 较大时会非常慢。"
        "实际工程中应使用循环或记忆化优化,这里仅用于演示递归思想。"
    )

    # --- 10.7 ---
    H.h3("10.7 函数作为值传递")
    H.para(
        "在 H# 中,函数是一等公民,可以像普通值一样赋值给变量、存入列表、作为参数传递给其他函数。"
        "这是函数式编程的基础。下面把一个命名函数赋值给变量,再通过变量调用它:"
    )
    H.code(
        "fn double(x) {\n"
        "    return x * 2;\n"
        "}\n"
        "let f = double;\n"
        "print(f(5));\n"
        "\n"
        "fn apply(func, x) {\n"
        "    return func(x);\n"
        "}\n"
        "print(apply(double, 10));"
    )
    H.output(
        "10\n"
        "20"
    )
    H.para(
        "把 double 赋值给 f 后,f(5) 等价于 double(5)。"
        "apply 函数接收一个函数 func 和一个值 x,返回 func(x) 的结果。"
        "这种接收函数作为参数的函数称为高阶函数,将在第 12 章深入讲解。"
    )

    # 小结 + 练习
    H.h3("本章小结")
    H.bullet("fn 关键字定义函数,函数名(形参) { 函数体 } 是基本语法。")
    H.bullet("return 返回值,无 return 时返回 nullptr。")
    H.bullet("默认参数通过判断 nullptr 实现,调用时传 nullptr 表示用默认值。")
    H.bullet("可变参数用列表传递,函数内部 for 遍历。")
    H.bullet("递归必须有终止条件,阶乘和斐波那契是经典递归案例。")
    H.bullet("函数是一等公民,可赋值给变量、作为参数传递。")

    H.h3("练习题")
    H.number("编写函数 max_of_three(a, b, c),返回三个数中的最大值。")
    H.number("编写函数 is_prime(n),判断 n 是否为素数,返回 true/false。")
    H.number("用递归实现函数 power(base, exp),计算 base 的 exp 次方。")
    H.number("编写函数 reverse_list(lst),返回列表的逆序副本(不修改原列表)。")
    H.number("编写高阶函数 apply_twice(f, x),返回 f(f(x))。")

    H.page_break()

    # ============================================================
    # 第11章 作用域与闭包
    # ============================================================
    H.h2("第11章 作用域与闭包")

    H.para(
        "作用域决定了变量在何处可见、何时存在。闭包是函数与其捕获环境的结合体,是 H# 函数式编程的核心机制。"
        "理解作用域和闭包,才能写出正确的有状态函数,避免变量捕获中的常见陷阱。"
        "本章将揭示 H# 中命名函数与 Lambda 在捕获行为上的关键差异。"
    )

    # --- 11.1 ---
    H.h3("11.1 词法作用域")
    H.para(
        "H# 采用词法作用域(lexical scoping):变量的作用域由它在源代码中书写的位置决定,"
        "而非调用时的位置。简单来说,内层代码块可以访问外层定义的变量,但外层不能访问内层的局部变量。"
    )
    H.code(
        "let x = 10;\n"
        "fn show_x() {\n"
        "    print(x);\n"
        "}\n"
        "show_x();"
    )
    H.output("10")
    H.para(
        "函数 show_x 内部并没有定义 x,但它能访问外层(全局)的 x。"
        "这是因为词法作用域允许函数引用定义时所在环境中的变量。"
    )

    # --- 11.2 ---
    H.h3("11.2 全局变量与局部变量")
    H.para(
        "在函数内部用 let 声明的变量是局部变量,只在函数体内有效,不会影响外层同名变量。"
        "未用 let 声明而直接赋值的变量,会修改当前作用域中已存在的同名变量。"
    )
    H.code(
        "let g = 100;\n"
        "fn test_scope() {\n"
        "    let g = 200;\n"
        "    print(g);\n"
        "}\n"
        "test_scope();\n"
        "print(g);"
    )
    H.output(
        "200\n"
        "100"
    )
    H.para(
        "test_scope 内部用 let 声明了一个新的局部变量 g,值为 200,它遮蔽(shadow)了外层的全局 g。"
        "但函数结束后局部 g 消失,外层 g 仍然是 100。这就是局部变量不会污染全局作用域的原因。"
    )

    # --- 11.3 ---
    H.h3("11.3 __closure__ 机制原理讲解")
    H.para(
        "H# 的闭包底层依赖 __closure__ 机制:当一个 Lambda 表达式被创建时,解释器会把它当前环境中"
        "引用到的外层变量打包成一个闭包环境(closure),与函数对象绑定在一起。"
        "这样即使外层函数已经返回,闭包仍然持有对这些变量的引用,变量不会被回收。"
    )
    H.para("闭包环境的核心特点:")
    H.bullet("捕获的是变量的引用,而非值的副本,因此闭包可以读取和修改外层变量。")
    H.bullet("每次创建闭包都会产生一个独立的环境,不同闭包互不干扰。")
    H.bullet("只有 Lambda 表达式(fn(x) {...})才会创建闭包,命名内层函数不会捕获外层变量。")
    H.warning(
        "这是 H# 闭包最易踩坑的地方:命名内层函数(用 fn name() {...} 定义在函数内部的函数)"
        "不捕获外层作用域变量!只有匿名 Lambda 才具备闭包捕获能力。详见 11.7 节。"
    )

    # --- 11.4 ---
    H.h3("11.4 闭包捕获外层变量(用 Lambda)")
    H.para(
        "下面用工厂函数 make_adder 演示闭包捕获。make_adder 接收参数 n,返回一个 Lambda,"
        "该 Lambda 捕获了 n,形成了一个 \"加 n\" 的函数。"
    )
    H.code(
        "fn make_adder(n) {\n"
        "    let adder = fn(x) {\n"
        "        return x + n;\n"
        "    };\n"
        "    return adder;\n"
        "}\n"
        "let add5 = make_adder(5);\n"
        "let add10 = make_adder(10);\n"
        "print(add5(3));\n"
        "print(add10(3));"
    )
    H.output(
        "8\n"
        "13"
    )
    H.para(
        "make_adder(5) 返回的 Lambda 捕获了 n=5,所以 add5(3) = 3 + 5 = 8。"
        "make_adder(10) 创建了另一个独立闭包,n=10,所以 add10(3) = 13。"
        "两次调用产生两个互不干扰的闭包环境。"
    )

    # --- 11.5 ---
    H.h3("11.5 闭包修改外层变量")
    H.para(
        "由于闭包捕获的是变量引用,闭包内部可以修改外层变量的值。"
        "利用这一特性,我们可以实现有状态的计数器:"
    )
    H.code(
        "fn counter() {\n"
        "    let count = 0;\n"
        "    let increment = fn() {\n"
        "        count = count + 1;\n"
        "        return count;\n"
        "    };\n"
        "    return increment;\n"
        "}\n"
        "let c = counter();\n"
        "print(c());\n"
        "print(c());\n"
        "print(c());"
    )
    H.output(
        "1\n"
        "2\n"
        "3"
    )
    H.para(
        "每次调用 c() 时,Lambda 内部修改的是 counter 函数作用域中的 count 变量。"
        "由于闭包持有 count 的引用,count 在 counter 返回后仍然存活,从而实现了状态保持。"
        "这是闭包最经典的应用:用函数封装可变状态。"
    )
    H.para("再看一个共享状态的例子 —— 模拟银行账户存取款:")
    H.code(
        "fn make_account(balance) {\n"
        "    let deposit = fn(amount) {\n"
        "        balance = balance + amount;\n"
        "        return balance;\n"
        "    };\n"
        "    return deposit;\n"
        "}\n"
        "let acct = make_account(100);\n"
        "print(acct(50));\n"
        "print(acct(-30));"
    )
    H.output(
        "150\n"
        "120"
    )
    H.para(
        "acct 闭包持有 balance 变量,acct(50) 存入 50 后余额变为 150,"
        "acct(-30) 取出 30 后余额变为 120。状态在多次调用间持续累加。"
    )

    # --- 11.6 ---
    H.h3("11.6 循环变量捕获(重要:需 Lambda 副本)")
    H.para(
        "在循环中创建闭包时,如果直接捕获循环变量,所有闭包会共享同一个变量引用,"
        "最终都指向循环结束时的值。要解决这个问题,必须通过中间变量和工厂函数为每次迭代创建独立副本。"
    )
    H.para("错误做法(所有闭包共享最后一个值)的本质:循环变量只有一个,闭包捕获的是它的引用。")
    H.para("正确做法 —— 用 Lambda 工厂函数创建独立环境:")
    H.code(
        "let fns = [];\n"
        "let i = 0;\n"
        "while (i < 3) {\n"
        "    let captured = i;\n"
        "    let make_fn = fn(c) {\n"
        "        return fn() { return c; };\n"
        "    };\n"
        "    push(fns, make_fn(captured));\n"
        "    i = i + 1;\n"
        "}\n"
        "print(fns[0]());\n"
        "print(fns[1]());\n"
        "print(fns[2]());"
    )
    H.output(
        "0\n"
        "1\n"
        "2"
    )
    H.para(
        "关键在于 make_fn 这个工厂 Lambda:它接收参数 c,每次调用都创建一个新的闭包环境,"
        "把当前 captured 的值绑定到 c。这样三个闭包分别捕获了 0、1、2,互不干扰。"
    )
    H.warning(
        "循环变量捕获是闭包最隐蔽的 bug 来源。记住口诀:循环里造闭包,先用工厂函数把循环变量"
        "作为参数传入,让它成为闭包的独立副本。"
    )

    # --- 11.7 ---
    H.h3("11.7 命名函数 vs Lambda 的区别(命名内层函数不捕获!)")
    H.para(
        "这是 H# 闭包机制中最重要的一条规则:在函数内部用 \"fn 名字() {...}\" 定义的命名内层函数,"
        "不会捕获外层作用域的变量!它只能访问自己的参数和全局变量。"
        "只有匿名 Lambda(fn() {...} 或 fn(x) {...})才具备真正的闭包捕获能力。"
    )
    H.para("下面用 try/catch 演示命名内层函数访问外层变量时的报错:")
    H.code(
        "try {\n"
        "    fn bad() {\n"
        "        let n = 42;\n"
        "        fn inner() {\n"
        "            return n;\n"
        "        }\n"
        "        return inner();\n"
        "    }\n"
        "    print(bad());\n"
        "} catch (e) {\n"
        "    print(\"Error: \" + e);\n"
        "}"
    )
    H.output("Error: Undefined variable: 'n'")
    H.para(
        "inner 是命名内层函数,它尝试访问外层变量 n,但解释器报 \"Undefined variable: 'n'\"。"
        "这证明命名内层函数没有捕获外层作用域。"
    )
    H.para("改为 Lambda 即可正常工作:")
    H.code(
        "fn good() {\n"
        "    let n = 42;\n"
        "    let inner = fn() { return n; };\n"
        "    return inner();\n"
        "}\n"
        "print(good());"
    )
    H.output("42")
    H.note(
        "结论:在 H# 中,凡是需要捕获外层变量的场景,一律使用 Lambda(fn(参数) { ... }) 赋值给变量,"
        "而不是用命名内层函数。这是 H# 闭包的硬性规则。"
    )

    # 小结 + 练习
    H.h3("本章小结")
    H.bullet("H# 采用词法作用域,内层可访问外层变量,外层不能访问内层局部变量。")
    H.bullet("let 声明的局部变量会遮蔽外层同名变量,但不修改外层。")
    H.bullet("闭包 = Lambda + 捕获的环境,环境中的变量以引用方式持有,可被修改。")
    H.bullet("每次创建 Lambda 都产生独立闭包环境,不同闭包互不干扰。")
    H.bullet("循环中捕获变量必须用工厂 Lambda 创建副本,避免共享。")
    H.bullet("命名内层函数不捕获外层变量,只有 Lambda 才有闭包能力。")

    H.h3("练习题")
    H.number("编写闭包工厂 make_multiplier(factor),返回一个把输入乘以 factor 的函数。")
    H.number("用闭包实现一个累加器 accumulator(),每次调用把参数累加并返回当前总和。")
    H.number("用闭包实现 make_counter(start),返回从 start 开始的计数器函数。")
    H.number("在循环中创建 5 个闭包,分别返回 0 到 4,验证每个闭包捕获独立的值。")
    H.number("对比命名内层函数与 Lambda 捕获外层变量的差异,用代码验证并解释原因。")

    H.page_break()

    # ============================================================
    # 第12章 Lambda 表达式
    # ============================================================
    H.h2("第12章 Lambda 表达式")

    H.para(
        "Lambda 表达式(匿名函数)是函数式编程的基石。它允许我们在需要函数的地方直接写出函数,"
        "而无需事先用 fn 命名。Lambda 天然支持闭包捕获,是 H# 中实现高阶函数、回调、工厂模式的利器。"
        "本章将系统讲解 Lambda 语法及其在 map、filter、reduce 三大经典高阶函数中的应用。"
    )

    # --- 12.1 ---
    H.h3("12.1 Lambda 语法")
    H.para(
        "Lambda 的语法是 fn(参数列表) { 函数体 },它是一个表达式,可以出现在任何值可以出现的位置。"
        "通常我们会把它赋值给变量,以便后续调用。"
    )
    H.code(
        "let square = fn(x) {\n"
        "    return x * x;\n"
        "};\n"
        "print(square(5));\n"
        "\n"
        "let greet = fn(name) {\n"
        "    return \"Hi, \" + name;\n"
        "};\n"
        "print(greet(\"Alice\"));"
    )
    H.output(
        "25\n"
        "Hi, Alice"
    )
    H.para(
        "square 是一个 Lambda,接收参数 x,返回 x 的平方。Lambda 赋值给变量后,用法和命名函数完全一致。"
        "注意 Lambda 语句末尾要有分号(因为赋值是一条语句)。"
    )

    # --- 12.2 ---
    H.h3("12.2 Lambda 作为一等公民")
    H.para(
        "Lambda 是值,可以存入列表、字典,也可以作为数组元素按索引取出调用。"
        "这种灵活性使 Lambda 成为构建策略模式、回调队列的理想工具。"
    )
    H.code(
        "let fns = [\n"
        "    fn(x) { return x + 1; },\n"
        "    fn(x) { return x * 2; },\n"
        "    fn(x) { return x - 3; }\n"
        "];\n"
        "print(fns[0](10));\n"
        "print(fns[1](10));\n"
        "print(fns[2](10));"
    )
    H.output(
        "11\n"
        "20\n"
        "7"
    )
    H.para(
        "列表 fns 存了三个 Lambda,分别做加一、乘二、减三。通过索引取出后立即调用,"
        "体现了 \"函数即数据\" 的思想。"
    )

    # --- 12.3 ---
    H.h3("12.3 高阶函数(函数作参数)")
    H.para(
        "高阶函数是接收函数作为参数、或返回函数的函数。H# 中最常见的高阶函数模式是:"
        "把一个操作(用 Lambda 表示)传给一个通用处理函数,让通用函数负责遍历,具体操作由 Lambda 决定。"
    )
    H.code(
        "fn apply(f, x) {\n"
        "    return f(x);\n"
        "}\n"
        "print(apply(fn(x) { return x * 3; }, 4));\n"
        "print(apply(fn(x) { return x + 10; }, 5));"
    )
    H.output(
        "12\n"
        "15"
    )
    H.para(
        "apply 是高阶函数,它不关心 f 具体做什么,只负责调用 f(x)。"
        "调用方通过传入不同 Lambda 来复用 apply 的调用框架。"
    )

    # --- 12.4 ---
    H.h3("12.4 map 实现")
    H.para(
        "map(映射)是函数式编程的经典操作:对一个列表的每个元素应用同一个函数,收集结果形成新列表。"
        "下面我们用 H# 手写一个 map 函数:"
    )
    H.code(
        "fn map(lst, f) {\n"
        "    let result = [];\n"
        "    for x in lst {\n"
        "        push(result, f(x));\n"
        "    }\n"
        "    return result;\n"
        "}\n"
        "let nums = [1, 2, 3, 4, 5];\n"
        "let doubled = map(nums, fn(x) { return x * 2; });\n"
        "print(doubled);\n"
        "\n"
        "let squared = map(nums, fn(x) { return x * x; });\n"
        "print(squared);"
    )
    H.output(
        "[2, 4, 6, 8, 10]\n"
        "[1, 4, 9, 16, 25]"
    )
    H.para(
        "map 把遍历逻辑和变换逻辑分离:map 负责遍历和收集,Lambda 负责具体的变换规则。"
        "换一个 Lambda 就能得到不同结果,代码复用性极高。"
    )

    # --- 12.5 ---
    H.h3("12.5 filter 实现")
    H.para(
        "filter(过滤)用于从列表中筛选出满足条件的元素。它接收一个列表和一个谓词函数"
        "(返回 true/false 的函数),保留谓词返回 true 的元素。"
    )
    H.code(
        "fn filter(lst, pred) {\n"
        "    let result = [];\n"
        "    for x in lst {\n"
        "        if (pred(x)) {\n"
        "            push(result, x);\n"
        "        }\n"
        "    }\n"
        "    return result;\n"
        "}\n"
        "let evens = filter([1, 2, 3, 4, 5, 6], fn(x) { return x % 2 == 0; });\n"
        "print(evens);\n"
        "\n"
        "let big = filter([3, 10, 7, 20, 5], fn(x) { return x > 8; });\n"
        "print(big);"
    )
    H.output(
        "[2, 4, 6]\n"
        "[10, 20]"
    )
    H.para(
        "第一个 filter 选出偶数,第二个选出大于 8 的数。谓词 Lambda 决定了筛选标准,"
        "filter 本身只负责遍历和判断收集。"
    )

    # --- 12.6 ---
    H.h3("12.6 reduce 实现")
    H.para(
        "reduce(归约)把列表中的所有元素用一个二元函数合并成一个值。"
        "它接收列表、合并函数和初始值,依次用合并函数把每个元素累计到结果中。"
    )
    H.code(
        "fn reduce(lst, f, init) {\n"
        "    let acc = init;\n"
        "    for x in lst {\n"
        "        acc = f(acc, x);\n"
        "    }\n"
        "    return acc;\n"
        "}\n"
        "let total = reduce([1, 2, 3, 4, 5], fn(a, b) { return a + b; }, 0);\n"
        "print(total);\n"
        "\n"
        "let product = reduce([1, 2, 3, 4], fn(a, b) { return a * b; }, 1);\n"
        "print(product);"
    )
    H.output(
        "15\n"
        "24"
    )
    H.para(
        "求和时初始值为 0,合并函数是加法;求积时初始值为 1,合并函数是乘法。"
        "reduce 把列表 \"归约\" 成单个值,是统计计算的核心工具。"
    )
    H.note(
        "map、filter、reduce 是函数式编程的三大神器,它们组合使用可以替代大部分循环,"
        "让代码更声明式、更易读。下一章将展示它们的组合应用。"
    )

    # 小结 + 练习
    H.h3("本章小结")
    H.bullet("Lambda 语法 fn(参数) { 函数体 },是匿名函数表达式,可赋值、可传参。")
    H.bullet("Lambda 是一等公民,可存入列表、字典,按索引取出调用。")
    H.bullet("高阶函数接收函数作参数,把遍历逻辑与变换逻辑分离。")
    H.bullet("map 对每个元素应用函数,返回新列表。")
    H.bullet("filter 按谓词筛选元素,返回满足条件的子列表。")
    H.bullet("reduce 用二元函数把列表归约为单个值。")

    H.h3("练习题")
    H.number("用 map 把列表 [1,2,3,4] 的每个元素加 100。")
    H.number("用 filter 从 [10, 15, 20, 25, 30] 中筛出能被 20 整除的数。")
    H.number("用 reduce 求列表 [3, 1, 4, 1, 5, 9] 的最大值。")
    H.number("用 map 和 filter 组合:先筛出偶数,再把偶数平方。")
    H.number("编写高阶函数 forEach(lst, f),对每个元素执行 f 但不返回结果。")

    H.page_break()

    # ============================================================
    # 第13章 函数式编程实践
    # ============================================================
    H.h2("第13章 函数式编程实践")

    H.para(
        "本章把前几章学到的函数、闭包、Lambda、高阶函数综合运用到实际场景中。"
        "我们将实现函数组合、柯里化、不可变数据处理流程,以及一个函数式风格的小型计算器。"
        "通过这些实战,你将真正体会函数式编程的简洁与力量。"
    )

    # 辅助函数声明(书中作为前置工具)
    H.para("本章示例会用到上一章实现的 map、filter、reduce,为方便阅读,先在文件顶部声明它们:")
    H.code(
        "fn map(lst, f) {\n"
        "    let result = [];\n"
        "    for x in lst { push(result, f(x)); }\n"
        "    return result;\n"
        "}\n"
        "fn filter(lst, pred) {\n"
        "    let result = [];\n"
        "    for x in lst { if (pred(x)) { push(result, x); } }\n"
        "    return result;\n"
        "}\n"
        "fn reduce(lst, f, init) {\n"
        "    let acc = init;\n"
        "    for x in lst { acc = f(acc, x); }\n"
        "    return acc;\n"
        "}"
    )

    # --- 13.1 ---
    H.h3("13.1 函数组合")
    H.para(
        "函数组合是把两个函数 f 和 g 合并成一个新函数 h,使得 h(x) = f(g(x))。"
        "组合后的函数可以像管道一样串联多个处理步骤,是函数式编程的核心抽象。"
    )
    H.code(
        "fn compose(f, g) {\n"
        "    return fn(x) { return f(g(x)); };\n"
        "}\n"
        "let addOne = fn(x) { return x + 1; };\n"
        "let timesTwo = fn(x) { return x * 2; };\n"
        "let addThenDouble = compose(timesTwo, addOne);\n"
        "print(addThenDouble(3));"
    )
    H.output("8")
    H.para(
        "compose(timesTwo, addOne) 返回的新函数,先对输入加一,再乘二。"
        "输入 3:先 3+1=4,再 4*2=8。函数组合让我们用简单的积木搭建出复杂的数据处理流水线。"
    )

    # --- 13.2 ---
    H.h3("13.2 柯里化(currying)实现")
    H.para(
        "柯里化是把一个多参数函数转换成一系列单参数函数的过程。例如 f(a, b, c) 柯里化后变成"
        "f(a)(b)(c),每次只接收一个参数,返回一个接收下一个参数的函数。"
    )
    H.code(
        "fn curry_add(a) {\n"
        "    return fn(b) {\n"
        "        return fn(c) {\n"
        "            return a + b + c;\n"
        "        };\n"
        "    };\n"
        "}\n"
        "let step1 = curry_add(1);\n"
        "let step2 = step1(2);\n"
        "print(step2(3));\n"
        "\n"
        "print(curry_add(10)(20)(30));"
    )
    H.output(
        "6\n"
        "60"
    )
    H.para(
        "curry_add(1) 返回一个接收 b 的函数,该函数又返回一个接收 c 的函数,最终计算 a+b+c。"
        "这种逐级返回闭包的形式就是柯里化。它可以让我们部分应用参数,创建预设了部分参数的新函数。"
    )

    # --- 13.3 ---
    H.h3("13.3 不可变思维")
    H.para(
        "函数式编程强调不可变(immutable)数据:不修改原始数据,而是返回包含变换结果的新数据。"
        "这样可以避免副作用,让程序行为更可预测、更易调试。"
    )
    H.code(
        "fn immutable_map(lst, f) {\n"
        "    let result = [];\n"
        "    for x in lst {\n"
        "        push(result, f(x));\n"
        "    }\n"
        "    return result;\n"
        "}\n"
        "let original = [1, 2, 3];\n"
        "let mapped = immutable_map(original, fn(x) { return x * 10; });\n"
        "print(original);\n"
        "print(mapped);"
    )
    H.output(
        "[1, 2, 3]\n"
        "[10, 20, 30]"
    )
    H.para(
        "immutable_map 不修改 original,而是新建一个列表存结果。调用后 original 仍然是 [1, 2, 3],"
        "mapped 是 [10, 20, 30]。原始数据得以保留,这正是不可变思维的核心。"
    )
    H.note(
        "不可变思维的好处:函数没有副作用,相同输入永远产生相同输出,便于测试和并发。"
    )

    # --- 13.4 ---
    H.h3("13.4 实战:用函数式风格处理列表")
    H.para(
        "下面用 map、filter、reduce 组合,实现一个数据处理管道:"
        "从一组数中筛出正数,平方后求和。每一步都返回新数据,前一步的输出是后一步的输入。"
    )
    H.code(
        "fn pipeline(data) {\n"
        "    let step1 = filter(data, fn(x) { return x > 0; });\n"
        "    let step2 = map(step1, fn(x) { return x * x; });\n"
        "    let step3 = reduce(step2, fn(a, b) { return a + b; }, 0);\n"
        "    return step3;\n"
        "}\n"
        "print(pipeline([-2, -1, 1, 2, 3]));"
    )
    H.output("14")
    H.para(
        "数据 [-2, -1, 1, 2, 3] 经过三步处理:"
        "step1 筛出正数 [1, 2, 3];step2 平方得到 [1, 4, 9];step3 求和得到 14。"
        "整个管道清晰表达了 \"筛选 → 变换 → 汇总\" 的处理意图,没有任何显式循环。"
    )

    # --- 13.5 ---
    H.h3("13.5 实战:计算器")
    H.para(
        "最后用一个函数式计算器综合演示:把运算符映射到对应的 Lambda,根据传入的运算符选择对应函数执行。"
        "这种 \"数据驱动\" 的设计避免了冗长的 if/else,扩展时只需增加映射项。"
    )
    H.code(
        "fn calculate(a, op, b) {\n"
        "    if (op == \"+\") { return a + b; }\n"
        "    if (op == \"-\") { return a - b; }\n"
        "    if (op == \"*\") { return a * b; }\n"
        "    if (op == \"/\") { return a / b; }\n"
        "    return 0;\n"
        "}\n"
        "print(calculate(10, \"+\", 5));\n"
        "print(calculate(10, \"-\", 3));\n"
        "print(calculate(10, \"*\", 4));\n"
        "print(calculate(20, \"/\", 4));"
    )
    H.output(
        "15\n"
        "7\n"
        "40\n"
        "5"
    )
    H.para(
        "calculate 接收两个操作数和运算符,返回运算结果。函数式风格让逻辑一目了然。"
        "在第 17 章我们会用面向对象方式重写这个计算器,对比两种范式的差异。"
    )

    # 小结 + 练习
    H.h3("本章小结")
    H.bullet("函数组合 compose 把 f(g(x)) 封装成新函数,构建处理管道。")
    H.bullet("柯里化用嵌套闭包把多参数函数拆成单参数链。")
    H.bullet("不可变思维:不修改原数据,返回新数据,避免副作用。")
    H.bullet("map/filter/reduce 组合可构建声明式数据处理管道。")
    H.bullet("函数式计算器用映射替代分支,扩展性好。")

    H.h3("练习题")
    H.number("编写 compose3(f, g, h),实现三函数组合 f(g(h(x)))。")
    H.number("用柯里化实现 curry_mul(a)(b)(c) = a * b * c。")
    H.number("用函数式管道:从字符串列表中筛出长度大于 3 的,拼接成一个字符串。")
    H.number("用 reduce 实现拼接函数,把列表 [\"a\",\"b\",\"c\"] 拼成 \"abc\"。")
    H.number("用不可变方式实现函数 double_all(lst),返回每个元素翻倍的新列表。")

    H.page_break()

    # ============================================================
    # 第四篇 面向对象
    # ============================================================
    H.h1("第四篇 面向对象")

    H.para(
        "面向对象编程(OOP)是 H# 的另一大编程范式。它通过类和对象把数据与操作数据的方法封装在一起,"
        "支持继承、多态、封装等特性,非常适合构建中大型程序。本篇将从类与对象的基础语法讲起,"
        "逐步深入继承、封装,最后通过图书管理、学生成绩管理等实战项目巩固所学。"
    )
    H.para(
        "H# 的 OOP 语法简洁:用 class 定义类,new 创建对象,extends 实现继承,private 控制访问。"
        "方法参数列表中不含 self(由解释器自动绑定),书写十分自然。"
    )

    # ============================================================
    # 第14章 类与对象
    # ============================================================
    H.h2("第14章 类与对象")

    H.para(
        "类是对象的蓝图,对象是类的实例。本章讲解 class 关键字、字段定义、方法定义、"
        "对象创建、init 初始化方法、self 自动绑定机制,以及 static fn 静态方法。"
        "掌握这些,你就能用 H# 写出结构清晰的面向对象程序。"
    )

    # --- 14.1 ---
    H.h3("14.1 class 关键字")
    H.para(
        "使用 class 关键字定义类。类名建议使用大驼峰命名(如 Person、BankAccount)。"
        "类体用花括号 {} 包裹,内部可以包含字段定义和方法定义。"
    )
    H.code(
        "class Person {\n"
        "    let name = \"\";\n"
        "    let age = 0;\n"
        "    fn init(name, age) {\n"
        "        self.name = name;\n"
        "        self.age = age;\n"
        "    }\n"
        "    fn greet() {\n"
        "        return \"Hello, I am \" + self.name;\n"
        "    }\n"
        "}"
    )
    H.para(
        "上面定义了一个 Person 类,包含两个字段(name、age)和两个方法(init、greet)。"
        "字段在类体顶部用 let 声明并给出默认值。"
    )

    # --- 14.2 ---
    H.h3("14.2 字段定义(let field = val;)")
    H.para(
        "字段是对象存储数据的变量,在类体顶部用 \"let 字段名 = 默认值;\" 声明。"
        "每个对象实例都拥有这些字段的独立副本。默认值在对象创建时生效。"
    )
    H.code(
        "class Config {\n"
        "    let debug = false;\n"
        "    let level = 1;\n"
        "    let name = \"default\";\n"
        "}\n"
        "let c1 = new Config();\n"
        "print(c1.debug);\n"
        "print(c1.level);\n"
        "print(c1.name);"
    )
    H.output(
        "False\n"
        "1\n"
        "default"
    )
    H.para(
        "Config 类定义了三个带默认值的字段。new Config() 创建对象后,可以直接用 \"对象.字段\" 访问。"
        "注意此时没有 init 方法,new 也能正常工作,字段使用默认值。"
    )

    # --- 14.3 ---
    H.h3("14.3 方法定义(fn method(params){...},无 self 参数)")
    H.para(
        "方法是类中定义的函数,用于操作对象的数据。H# 的方法参数列表中不含 self —— "
        "解释器会在调用时自动把当前对象绑定到 self,方法体内通过 self 访问对象的字段和其他方法。"
    )
    H.code(
        "class Car {\n"
        "    fn init(brand, model, year) {\n"
        "        self.brand = brand;\n"
        "        self.model = model;\n"
        "        self.year = year;\n"
        "    }\n"
        "    fn describe() {\n"
        "        return self.year + \" \" + self.brand + \" \" + self.model;\n"
        "    }\n"
        "    fn is_new() {\n"
        "        return self.year >= 2024;\n"
        "    }\n"
        "}\n"
        "let car = new Car(\"Toyota\", \"Camry\", 2024);\n"
        "print(car.describe());\n"
        "print(car.is_new());"
    )
    H.output(
        "2024 Toyota Camry\n"
        "True"
    )
    H.para(
        "describe 和 is_new 方法都没有 self 参数,但方法体内可以用 self.brand、self.year 等。"
        "调用时用 \"对象.方法名(参数)\" 形式,如 car.describe()。"
    )
    H.note(
        "H# 的方法参数不含 self,这是与 Python 的重要区别。书写更简洁,自动绑定由解释器完成。"
    )

    # --- 14.4 ---
    H.h3("14.4 new 创建对象")
    H.para(
        "使用 new 关键字创建对象实例。new 会分配对象内存、初始化字段默认值,然后调用 init 方法。"
        "如果 init 方法需要参数,可以直接在 new 时传入:new ClassName(参数)。"
    )
    H.code(
        "let p = new Person(\"Alice\", 30);\n"
        "print(p.name);\n"
        "print(p.age);\n"
        "print(p.greet());"
    )
    H.output(
        "Alice\n"
        "30\n"
        "Hello, I am Alice"
    )
    H.para(
        "new Person(\"Alice\", 30) 创建 Person 对象并自动调用 init(\"Alice\", 30),"
        "把传入的值赋给 self.name 和 self.age。创建后即可访问字段和调用方法。"
    )

    # --- 14.5 ---
    H.h3("14.5 init 初始化方法")
    H.para(
        "init 是特殊的初始化方法,在 new 创建对象时被自动调用,用于设置对象的初始状态。"
        "new 时传入的参数会直接传递给 init。如果类没有定义 init,new 创建对象时仅使用字段默认值。"
    )
    H.para("下面演示有 init 和无 init 两种情况:")
    H.code(
        "# 有 init:new 时传参\n"
        "class Point {\n"
        "    fn init(x, y) {\n"
        "        self.x = x;\n"
        "        self.y = y;\n"
        "    }\n"
        "    fn show() {\n"
        "        return \"(\" + self.x + \",\" + self.y + \")\";\n"
        "    }\n"
        "}\n"
        "let p1 = new Point(3, 4);\n"
        "print(p1.show());\n"
        "\n"
        "# 无 init:new 不传参,使用字段默认值\n"
        "class Settings {\n"
        "    let volume = 50;\n"
        "    let muted = false;\n"
        "    fn toggle_mute() {\n"
        "        self.muted = not self.muted;\n"
        "        return self.muted;\n"
        "    }\n"
        "}\n"
        "let s = new Settings();\n"
        "print(s.volume);\n"
        "print(s.muted);\n"
        "print(s.toggle_mute());"
    )
    H.output(
        "(3,4)\n"
        "50\n"
        "False\n"
        "True"
    )
    H.note(
        "init 的参数个数必须与 new 传入的实参个数一致,否则会报错。"
        "如果不想在 new 时传参,可以不定义 init,或定义无参 init,再用 setter 方法设置字段。"
    )

    # --- 14.6 ---
    H.h3("14.6 self 自动绑定机制")
    H.para(
        "self 是对当前对象的引用。在 H# 中,方法定义时不需要写 self 参数,调用 \"对象.方法()\" 时,"
        "解释器自动把该对象绑定到方法内的 self 上。因此方法体内总能通过 self 访问当前对象的字段和方法。"
    )
    H.para("self 的关键用途:")
    H.bullet("self.字段名 —— 读写当前对象的字段。")
    H.bullet("self.方法名() —— 调用当前对象的其他方法。")
    H.bullet("return self —— 返回当前对象,用于方法链式调用。")
    H.para("下面用方法链(fluent interface)演示返回 self 的技巧:")
    H.code(
        "class Builder {\n"
        "    fn init() {\n"
        "        self.parts = [];\n"
        "    }\n"
        "    fn add(part) {\n"
        "        push(self.parts, part);\n"
        "        return self;\n"
        "    }\n"
        "    fn build() {\n"
        "        let result = \"\";\n"
        "        let i = 0;\n"
        "        while (i < len(self.parts)) {\n"
        "            result = result + self.parts[i];\n"
        "            i = i + 1;\n"
        "        }\n"
        "        return result;\n"
        "    }\n"
        "}\n"
        "let b = new Builder();\n"
        "let text = b.add(\"Hello\").add(\", \").add(\"World\").build();\n"
        "print(text);"
    )
    H.output("Hello, World")
    H.para(
        "add 方法返回 self,所以可以连续 .add().add().add() 链式调用,最后 .build() 得到结果。"
        "这种风格在构建复杂对象时非常优雅。"
    )

    # --- 14.7 ---
    H.h3("14.7 static fn 静态方法")
    H.para(
        "静态方法属于类本身,不属于某个对象实例。用 \"static fn\" 定义,通过 \"类名.方法名()\" 直接调用,"
        "无需创建对象。静态方法内不能使用 self(因为没有实例绑定),常用于工具函数。"
    )
    H.code(
        "class MathUtils {\n"
        "    static fn square(n) {\n"
        "        return n * n;\n"
        "    }\n"
        "    static fn cube(n) {\n"
        "        return n * n * n;\n"
        "    }\n"
        "    static fn max(a, b) {\n"
        "        if (a > b) { return a; }\n"
        "        return b;\n"
        "    }\n"
        "}\n"
        "print(MathUtils.square(5));\n"
        "print(MathUtils.cube(3));\n"
        "print(MathUtils.max(10, 20));"
    )
    H.output(
        "25\n"
        "27\n"
        "20"
    )
    H.warning(
        "H# 只支持 static fn(静态方法),不支持 static let(静态字段)。"
        "如果需要类级别的共享状态,可以用全局变量配合 static fn 来模拟,详见第 17 章单例模式。"
    )

    # 小结 + 练习
    H.h3("本章小结")
    H.bullet("class 定义类,类名用大驼峰;类体含字段和方法。")
    H.bullet("字段用 let 声明并设默认值,每个实例有独立副本。")
    H.bullet("方法参数不含 self,解释器自动绑定,self 引用当前对象。")
    H.bullet("new 创建对象并调用 init,实参直接传给 init。")
    H.bullet("无 init 时,new 使用字段默认值。")
    H.bullet("return self 实现方法链;static fn 定义静态工具方法。")

    H.h3("练习题")
    H.number("定义 Rectangle 类,含 width、height 字段和 area()、perimeter() 方法。")
    H.number("定义 Counter 类,用 init 设置初始值,提供 inc()、dec()、get() 方法。")
    H.number("用方法链实现 StringBuilder 类,支持 append、build 方法。")
    H.number("定义 StringUtils 类,包含 static fn repeat(s, n) 静态方法,返回字符串重复 n 次。")
    H.number("定义 BankAccount 类,含 owner、balance 字段,deposit 和 withdraw 方法。")

    H.page_break()

    # ============================================================
    # 第15章 继承与多态
    # ============================================================
    H.h2("第15章 继承与多态")

    H.para(
        "继承是面向对象的核心特性之一,它允许新类复用已有类的字段和方法,并在此基础上扩展或修改行为。"
        "多态则让不同类型的对象对同一消息做出各自特有的响应。本章讲解 extends 关键字、方法重写、"
        "父类访问,并通过 Shape 形状层次结构演示多态的威力。"
    )

    # --- 15.1 ---
    H.h3("15.1 extends 关键字")
    H.para(
        "使用 \"class 子类 extends 父类\" 实现继承。子类自动获得父类定义的字段和方法,"
        "可以新增自己的字段方法,也可以重写父类方法。"
    )
    H.code(
        "class Animal {\n"
        "    fn init(name) {\n"
        "        self.name = name;\n"
        "    }\n"
        "    fn speak() {\n"
        "        return self.name + \" makes a sound\";\n"
        "    }\n"
        "    fn eat() {\n"
        "        return self.name + \" is eating\";\n"
        "    }\n"
        "}\n"
        "class Cat extends Animal {\n"
        "    fn init(name) {\n"
        "        self.name = name;\n"
        "    }\n"
        "    fn speak() {\n"
        "        return self.name + \" meows\";\n"
        "    }\n"
        "}\n"
        "class Dog extends Animal {\n"
        "    fn init(name) {\n"
        "        self.name = name;\n"
        "    }\n"
        "    fn speak() {\n"
        "        return self.name + \" barks\";\n"
        "    }\n"
        "}"
    )
    H.para(
        "Cat 和 Dog 都 extends Animal,它们继承了 Animal 的 eat 方法,但各自重写了 speak 方法。"
        "下面创建实例并调用:"
    )
    H.code(
        "let a = new Animal(\"Generic\");\n"
        "let c = new Cat(\"Whiskers\");\n"
        "let d = new Dog(\"Rex\");\n"
        "print(a.speak());\n"
        "print(c.speak());\n"
        "print(d.speak());\n"
        "print(c.eat());\n"
        "print(d.eat());"
    )
    H.output(
        "Generic makes a sound\n"
        "Whiskers meows\n"
        "Rex barks\n"
        "Whiskers is eating\n"
        "Rex is eating"
    )
    H.para(
        "Cat 和 Dog 重写了 speak,各自输出猫叫、狗叫;但 eat 方法继承自 Animal,无需重新定义。"
        "这就是继承的复用价值。"
    )

    # --- 15.2 ---
    H.h3("15.2 方法重写")
    H.para(
        "子类中定义与父类同名的方法,即为重写(override)。调用时,解释器根据对象的实际类型"
        "执行对应类的方法,而非变量声明的类型。这就是动态派发。"
    )
    H.para(
        "上例中,Cat 和 Dog 都重写了 Animal 的 speak。当通过 Cat 对象调用 speak 时,执行的是 Cat 的版本;"
        "通过 Dog 对象调用时,执行 Dog 的版本。父类 Animal 的 speak 被 \"覆盖\"。"
    )
    H.note("重写方法时,方法名必须与父类完全一致,参数也建议保持一致,以保证多态行为正确。")

    # --- 15.3 ---
    H.h3("15.3 父类字段访问")
    H.para(
        "在 H# 中,子类可以直接访问从父类继承来的字段(通过 self.字段名)。"
        "子类的 init 方法通常会重新设置这些字段。下面演示子类访问父类字段:"
    )
    H.code(
        "class Vehicle {\n"
        "    fn init(name) {\n"
        "        self.name = name;\n"
        "        self.speed = 0;\n"
        "    }\n"
        "    fn move() {\n"
        "        return self.name + \" is moving at \" + self.speed;\n"
        "    }\n"
        "}\n"
        "class Car2 extends Vehicle {\n"
        "    fn init(name, speed) {\n"
        "        self.name = name;\n"
        "        self.speed = speed;\n"
        "    }\n"
        "    fn drive() {\n"
        "        return self.name + \" driving at \" + self.speed;\n"
        "    }\n"
        "}\n"
        "let car = new Car2(\"Tesla\", 120);\n"
        "print(car.move());\n"
        "print(car.drive());"
    )
    H.output(
        "Tesla is moving at 120\n"
        "Tesla driving at 120"
    )
    H.para(
        "Car2 继承了 Vehicle 的 name 和 speed 字段。Car2 的 init 重新设置了这两个字段,"
        "drive 和 move 方法都能访问它们。子类对父类字段的访问是透明的。"
    )

    # --- 15.4 ---
    H.h3("15.4 多态示例(Shape hierarchy)")
    H.para(
        "多态是 OOP 最强大的特性之一:不同类型的对象对同一方法调用做出不同响应。"
        "下面用 Shape 形状层次结构演示:Circle 和 Rectangle 都继承 Shape,各自重写 area 方法,"
        "通过统一的 describe 接口调用,展现多态魅力。"
    )
    H.code(
        "class Shape {\n"
        "    fn init() { }\n"
        "    fn area() {\n"
        "        return 0;\n"
        "    }\n"
        "    fn describe() {\n"
        "        return \"Shape area=\" + self.area();\n"
        "    }\n"
        "}\n"
        "class Circle extends Shape {\n"
        "    fn init(r) {\n"
        "        self.r = r;\n"
        "    }\n"
        "    fn area() {\n"
        "        return 3 * self.r * self.r;\n"
        "    }\n"
        "}\n"
        "class Rectangle extends Shape {\n"
        "    fn init(w, h) {\n"
        "        self.w = w;\n"
        "        self.h = h;\n"
        "    }\n"
        "    fn area() {\n"
        "        return self.w * self.h;\n"
        "    }\n"
        "}\n"
        "let shapes = [];\n"
        "push(shapes, new Circle(5));\n"
        "push(shapes, new Rectangle(4, 6));\n"
        "for s in shapes {\n"
        "    print(s.describe());\n"
        "}"
    )
    H.output(
        "Shape area=75\n"
        "Shape area=24"
    )
    H.para(
        "shapes 列表里存了 Circle 和 Rectangle 两种对象。循环中 s.describe() 对不同对象调用,"
        "Circle 的 area 返回 3*5*5=75,Rectangle 的 area 返回 4*6=24。"
        "调用方代码完全一致(for s in shapes { s.describe(); }),但行为因对象类型而异 —— 这就是多态。"
    )
    H.note("多态的价值:调用方无需关心对象的具体类型,只需知道它有 describe 方法。新增形状类型时,调用方代码无需修改。")

    # --- 15.5 ---
    H.h3("15.5 继承链")
    H.para(
        "继承可以形成多层链条:类 A 继承 B,B 继承 C。子类沿继承链可以获得所有祖先类的方法。"
        "下面演示三层继承链:Vehicle → Car → SportsCar。"
    )
    H.code(
        "class Vehicle {\n"
        "    fn init(name) {\n"
        "        self.name = name;\n"
        "    }\n"
        "    fn move() {\n"
        "        return self.name + \" is moving\";\n"
        "    }\n"
        "}\n"
        "class Car extends Vehicle {\n"
        "    fn init(name) {\n"
        "        self.name = name;\n"
        "    }\n"
        "    fn drive() {\n"
        "        return self.name + \" is driving\";\n"
        "    }\n"
        "}\n"
        "class SportsCar extends Car {\n"
        "    fn init(name) {\n"
        "        self.name = name;\n"
        "    }\n"
        "    fn turbo() {\n"
        "        return self.name + \" turbo boost!\";\n"
        "    }\n"
        "}\n"
        "let sc = new SportsCar(\"Ferrari\");\n"
        "print(sc.move());\n"
        "print(sc.drive());\n"
        "print(sc.turbo());"
    )
    H.output(
        "Ferrari is moving\n"
        "Ferrari is driving\n"
        "Ferrari turbo boost!"
    )
    H.para(
        "SportsCar 继承 Car,Car 继承 Vehicle。SportsCar 对象可以使用 move(Vehicle 的)、"
        "drive(Car 的)和 turbo(自己的)三个方法。继承链让功能逐层累加。"
    )
    H.warning("继承层次不宜过深,一般不超过 3 层。过深的继承链会增加理解难度,且容易破坏封装。")

    # 小结 + 练习
    H.h3("本章小结")
    H.bullet("extends 实现继承,子类获得父类的字段和方法。")
    H.bullet("方法重写:子类定义同名方法,调用时按对象实际类型派发。")
    H.bullet("子类可直接访问继承自父类的字段。")
    H.bullet("多态:不同对象对同一方法调用做出不同响应,调用方无需关心具体类型。")
    H.bullet("继承链可多层传递,但层次不宜过深。")

    H.h3("练习题")
    H.number("定义 Animal 及子类 Bird、Fish,各自重写 speak 和 move 方法。")
    H.number("扩展 Shape 体系,新增 Triangle 类,重写 area 方法。")
    H.number("定义 Employee 继承 Person,新增 salary 字段和 work 方法。")
    H.number("用多态实现一个动物园:把多种动物放入列表,统一调用 speak。")
    H.number("定义三层继承:Device → Computer → Laptop,每层增加一个方法。")

    H.page_break()

    # ============================================================
    # 第16章 封装与访问控制
    # ============================================================
    H.h2("第16章 封装与访问控制")

    H.para(
        "封装是面向对象的三大特性之一,它把对象内部状态隐藏起来,只通过公开的方法与外界交互。"
        "H# 通过 private 关键字实现字段保护,配合 getter/setter 方法控制读写权限。"
        "本章以 BankAccount 银行账户为案例,讲解封装的实践技巧。"
    )

    # --- 16.1 ---
    H.h3("16.1 private 字段")
    H.para(
        "用 \"private let 字段名 = 默认值;\" 声明私有字段。私有字段只能在类的方法内部通过 self 访问,"
        "外部代码不能直接读写。这防止了外部代码绕过校验逻辑随意修改内部状态。"
    )
    H.code(
        "class BankAccount {\n"
        "    private let balance = 0;\n"
        "    let owner = \"\";\n"
        "    fn init(owner, balance) {\n"
        "        self.owner = owner;\n"
        "        self.balance = balance;\n"
        "    }\n"
        "    fn get_balance() {\n"
        "        return self.balance;\n"
        "    }\n"
        "}"
    )
    H.para(
        "balance 是 private 字段,外部只能通过 get_balance() 方法读取,不能直接 acct.balance 访问。"
        "owner 是 public 字段,外部可直接读写。下面创建对象并访问:"
    )
    H.code(
        "let acct = new BankAccount(\"Alice\", 1000);\n"
        "print(acct.owner);\n"
        "print(acct.get_balance());"
    )
    H.output(
        "Alice\n"
        "1000"
    )

    # --- 16.2 ---
    H.h3("16.2 public 字段")
    H.para(
        "不加 private 修饰的字段是 public 字段,外部可以直接用 \"对象.字段\" 读写。"
        "public 字段适合存放不敏感、不需校验的数据,如姓名、标签等。"
    )
    H.para(
        "上例中 owner 是 public,可以直接 acct.owner 读取。如果需要修改,也可以直接赋值 acct.owner = \"Bob\"。"
        "但对于需要校验的数据(如余额),应该用 private 配合 setter。"
    )

    # --- 16.3 ---
    H.h3("16.3 字段保护机制")
    H.para(
        "private 的核心价值在于保护:把敏感数据的修改收敛到方法中,在方法内加入校验逻辑,"
        "确保数据始终处于合法状态。下面在 BankAccount 的存取款方法中加入金额校验:"
    )
    H.code(
        "class BankAccount {\n"
        "    private let balance = 0;\n"
        "    let owner = \"\";\n"
        "    fn init(owner, balance) {\n"
        "        self.owner = owner;\n"
        "        self.balance = balance;\n"
        "    }\n"
        "    fn deposit(amount) {\n"
        "        if (amount <= 0) {\n"
        "            throw \"Deposit must be positive\";\n"
        "        }\n"
        "        self.balance = self.balance + amount;\n"
        "        return self.balance;\n"
        "    }\n"
        "    fn withdraw(amount) {\n"
        "        if (amount <= 0) {\n"
        "            throw \"Withdraw must be positive\";\n"
        "        }\n"
        "        if (amount > self.balance) {\n"
        "            throw \"Insufficient funds\";\n"
        "        }\n"
        "        self.balance = self.balance - amount;\n"
        "        return self.balance;\n"
        "    }\n"
        "    fn get_balance() {\n"
        "        return self.balance;\n"
        "    }\n"
        "}"
    )
    H.para("deposit 和 withdraw 都校验金额合法性,非法时 throw 抛出异常。下面测试正常和异常流程:")
    H.code(
        "let acct = new BankAccount(\"Alice\", 1000);\n"
        "print(acct.get_balance());\n"
        "print(acct.deposit(500));\n"
        "print(acct.withdraw(200));\n"
        "print(acct.get_balance());\n"
        "try {\n"
        "    print(acct.withdraw(10000));\n"
        "} catch (e) {\n"
        "    print(\"Error: \" + e);\n"
        "}"
    )
    H.output(
        "1000\n"
        "1500\n"
        "1300\n"
        "1300\n"
        "Error: Insufficient funds"
    )
    H.para(
        "存入 500 余额变 1500,取出 200 余额变 1300。尝试取款 10000 超过余额,抛出异常被 catch 捕获。"
        "由于 balance 是 private,外部无法直接修改余额,只能通过 deposit/withdraw 走校验逻辑,保证了账户安全。"
    )

    # --- 16.4 ---
    H.h3("16.4 getter/setter 模式")
    H.para(
        "getter/setter 是封装的标准实践:getter 方法负责读取私有字段(可附加计算),"
        "setter 方法负责写入前校验。这样字段的读写都经过方法,便于加入额外逻辑。"
    )
    H.para("下面用 Temperature 类演示:getter 返回摄氏度,setter 校验不低于绝对零度,还提供华氏度 getter:")
    H.code(
        "class Temperature {\n"
        "    private let celsius = 0;\n"
        "    fn init(c) {\n"
        "        self.celsius = c;\n"
        "    }\n"
        "    fn get_celsius() {\n"
        "        return self.celsius;\n"
        "    }\n"
        "    fn set_celsius(c) {\n"
        "        if (c < -273) {\n"
        "            throw \"Below absolute zero\";\n"
        "        }\n"
        "        self.celsius = c;\n"
        "    }\n"
        "    fn get_fahrenheit() {\n"
        "        return self.celsius * 9 / 5 + 32;\n"
        "    }\n"
        "}\n"
        "let t = new Temperature(25);\n"
        "print(t.get_celsius());\n"
        "print(t.get_fahrenheit());"
    )
    H.output(
        "25\n"
        "77"
    )
    H.para(
        "get_celsius 读取摄氏度,get_fahrenheit 返回换算后的华氏度(25*9/5+32=77)。"
        "set_celsius 在写入前校验温度不低于绝对零度(-273°C)。通过 getter/setter,温度的读写完全可控。"
    )
    H.note(
        "注意:25 * 9 / 5 + 32 = 225 / 5 + 32 = 45 + 32 = 77。H# 中两整数相除为整数除法,"
        "225/5=45 正好整除,所以结果正确。"
    )

    # --- 16.5 ---
    H.h3("16.5 封装最佳实践")
    H.para("封装设计时应遵循以下原则:")
    H.bullet("默认字段设为 private,仅在确需外部直接访问时才设为 public。")
    H.bullet("通过 getter 暴露读取,通过 setter 控制写入并加入校验。")
    H.bullet("setter 中对非法值 throw 异常,而不是静默忽略,便于调用方发现问题。")
    H.bullet("涉及业务规则的方法(如 withdraw)把所有约束集中在一处,避免散落各处。")
    H.bullet("对外只暴露必要的方法,内部辅助方法也尽量 private(用命名约定)。")
    H.para(
        "封装的本质是 \"信息隐藏\":把变化封装在内部,对外提供稳定的接口。"
        "当内部实现改变时(比如余额改用分存储),只要接口不变,调用方代码就无需修改。"
        "这是管理软件复杂度的关键手段。"
    )

    # 小结 + 练习
    H.h3("本章小结")
    H.bullet("private let 声明私有字段,只能在类方法内通过 self 访问。")
    H.bullet("不加 private 的字段是 public,外部可直接读写。")
    H.bullet("private 配合方法校验,保证数据始终合法。")
    H.bullet("getter/setter 是封装标准模式,读写都经过可控方法。")
    H.bullet("封装 = 信息隐藏,对外稳定接口,内部自由变化。")

    H.h3("练习题")
    H.number("给 BankAccount 增加 transfer(other, amount) 方法,把金额转入另一个账户。")
    H.number("定义 Student 类,private 成绩字段,setter 校验 0-100,score 校验失败时 throw。")
    H.number("定义 Person 类,private age 字段,getter 返回年龄,setter 校验非负。")
    H.number("为 Temperature 增加 setters,使其可在摄氏与华氏间双向设置。")
    H.number("定义 Password 类,private password 字段,setter 校验长度至少 6 位。")

    H.page_break()

    # ============================================================
    # 第17章 OOP 实战
    # ============================================================
    H.h2("第17章 OOP 实战")

    H.para(
        "本章把前几章的 OOP 知识融会贯通,通过四个实战项目巩固面向对象设计能力:"
        "图书管理系统、学生成绩管理、OOP 版计算器,以及设计模式(单例、工厂)简介。"
        "每个项目都包含完整代码和运行输出,可作为你后续开发的参考模板。"
    )

    # --- 17.1 ---
    H.h3("17.1 图书管理系统设计")
    H.para(
        "图书管理系统包含两个类:Book(图书)和 Library(图书馆)。"
        "Book 封装书名、作者、借阅状态;Library 管理图书集合,支持添加、列表、查找。"
    )
    H.code(
        "class Book {\n"
        "    fn init(title, author) {\n"
        "        self.title = title;\n"
        "        self.author = author;\n"
        "        self.borrowed = false;\n"
        "    }\n"
        "    fn borrow() {\n"
        "        if (self.borrowed) {\n"
        "            return \"Already borrowed\";\n"
        "        }\n"
        "        self.borrowed = true;\n"
        "        return \"Borrowed: \" + self.title;\n"
        "    }\n"
        "    fn return_book() {\n"
        "        self.borrowed = false;\n"
        "        return \"Returned: \" + self.title;\n"
        "    }\n"
        "    fn info() {\n"
        "        return self.title + \" by \" + self.author;\n"
        "    }\n"
        "}\n"
        "class Library {\n"
        "    fn init() {\n"
        "        self.books = [];\n"
        "    }\n"
        "    fn add_book(book) {\n"
        "        push(self.books, book);\n"
        "        return self;\n"
        "    }\n"
        "    fn list_books() {\n"
        "        for b in self.books {\n"
        "            print(b.info());\n"
        "        }\n"
        "    }\n"
        "    fn find_book(title) {\n"
        "        for b in self.books {\n"
        "            if (b.title == title) {\n"
        "                return b;\n"
        "            }\n"
        "        }\n"
        "        return nullptr;\n"
        "    }\n"
        "}"
    )
    H.para("下面创建图书馆、添加图书、借阅归还,演示系统运行:")
    H.code(
        "let lib = new Library();\n"
        "lib.add_book(new Book(\"H# Primer\", \"Alice\"));\n"
        "lib.add_book(new Book(\"FP in H#\", \"Bob\"));\n"
        "lib.list_books();\n"
        "let found = lib.find_book(\"H# Primer\");\n"
        "print(found.borrow());\n"
        "print(found.borrow());\n"
        "print(found.return_book());"
    )
    H.output(
        "H# Primer by Alice\n"
        "FP in H# by Bob\n"
        "Borrowed: H# Primer\n"
        "Already borrowed\n"
        "Returned: H# Primer"
    )
    H.para(
        "lib.add_book 用方法链添加两本书;list_books 遍历打印;find_book 按书名查找。"
        "找到的书借阅一次成功,再借提示已借;归还后状态恢复。整个系统职责清晰、易于扩展。"
    )

    # --- 17.2 ---
    H.h3("17.2 学生成绩管理")
    H.para(
        "学生成绩管理包含 Student 类,封装姓名和成绩列表,支持添加成绩、计算平均分。"
        "用方法链 add_score 逐条添加成绩,average 计算平均值。"
    )
    H.code(
        "class Student {\n"
        "    fn init(name) {\n"
        "        self.name = name;\n"
        "        self.scores = [];\n"
        "    }\n"
        "    fn add_score(score) {\n"
        "        push(self.scores, score);\n"
        "        return self;\n"
        "    }\n"
        "    fn average() {\n"
        "        if (len(self.scores) == 0) { return 0; }\n"
        "        let total = 0;\n"
        "        for s in self.scores {\n"
        "            total = total + s;\n"
        "        }\n"
        "        return total / len(self.scores);\n"
        "    }\n"
        "    fn info() {\n"
        "        return self.name + \": avg=\" + self.average();\n"
        "    }\n"
        "}\n"
        "let stu = new Student(\"Alice\");\n"
        "stu.add_score(90).add_score(85).add_score(92);\n"
        "print(stu.info());"
    )
    H.output("Alice: avg=89")
    H.para(
        "add_score 返回 self 实现链式调用,一次性添加 90、85、92 三科成绩。"
        "average 计算平均:(90+85+92)/3 = 267/3 = 89(整数除法)。info 返回格式化的学生信息。"
    )

    # --- 17.3 ---
    H.h3("17.3 简单计算器(OOP 版)")
    H.para(
        "第 13 章我们用函数式风格实现了计算器,这里用 OOP 重写。Calculator 类封装历史记录,"
        "每次计算都记入历史,可随时查看。对比两种范式,体会各自的设计思路。"
    )
    H.code(
        "class Calculator {\n"
        "    fn init() {\n"
        "        self.history = [];\n"
        "    }\n"
        "    fn compute(a, op, b) {\n"
        "        let result = 0;\n"
        "        if (op == \"+\") { result = a + b; }\n"
        "        if (op == \"-\") { result = a - b; }\n"
        "        if (op == \"*\") { result = a * b; }\n"
        "        if (op == \"/\") { result = a / b; }\n"
        "        push(self.history, \"\" + a + op + b + \"=\" + result);\n"
        "        return result;\n"
        "    }\n"
        "    fn show_history() {\n"
        "        for h in self.history {\n"
        "            print(h);\n"
        "        }\n"
        "    }\n"
        "}\n"
        "let calc = new Calculator();\n"
        "print(calc.compute(10, \"+\", 5));\n"
        "print(calc.compute(20, \"-\", 8));\n"
        "print(calc.compute(3, \"*\", 4));\n"
        "print(calc.compute(20, \"/\", 4));\n"
        "calc.show_history();"
    )
    H.output(
        "15\n"
        "12\n"
        "12\n"
        "5\n"
        "10+5=15\n"
        "20-8=12\n"
        "3*4=12\n"
        "20/4=5"
    )
    H.para(
        "OOP 版计算器把历史记录作为对象状态保存,每次 compute 都追加一条记录,show_history 回顾全部计算。"
        "相比函数式版本,OOP 版天然支持状态保持,适合需要记录上下文的场景。"
    )

    # --- 17.4 ---
    H.h3("17.4 设计模式简介(单例、工厂)")
    H.para(
        "设计模式是面向对象设计中反复出现的解决方案模板。本节介绍两个常用模式:工厂模式和单例模式。"
    )
    H.para("工厂模式 —— 用 static fn 封装对象创建逻辑,把构造细节集中管理:")
    H.code(
        "class Point {\n"
        "    fn init(x, y) {\n"
        "        self.x = x;\n"
        "        self.y = y;\n"
        "    }\n"
        "    fn describe() {\n"
        "        return \"(\" + self.x + \",\" + self.y + \")\";\n"
        "    }\n"
        "    static fn origin() {\n"
        "        return new Point(0, 0);\n"
        "    }\n"
        "    static fn unit_x() {\n"
        "        return new Point(1, 0);\n"
        "    }\n"
        "}\n"
        "let o = Point.origin();\n"
        "let u = Point.unit_x();\n"
        "print(o.describe());\n"
        "print(u.describe());"
    )
    H.output(
        "(0,0)\n"
        "(1,0)"
    )
    H.para(
        "origin 和 unit_x 是工厂方法,封装了 \"创建原点\"、\"创建单位点\" 的构造逻辑。"
        "调用方无需知道 Point 的构造细节,只需调用工厂方法即可得到预设对象。"
    )
    H.para(
        "单例模式 —— 确保一个类只有一个实例,全局共享。由于 H# 不支持 static let(静态字段),"
        "我们用全局变量配合普通函数模拟单例:"
    )
    H.code(
        "let singleton_instance = nullptr;\n"
        "let singleton_call_count = 0;\n"
        "class Logger {\n"
        "    fn init() {\n"
        "        self.logs = [];\n"
        "    }\n"
        "    fn log(msg) {\n"
        "        push(self.logs, msg);\n"
        "        return self;\n"
        "    }\n"
        "    fn show() {\n"
        "        for l in self.logs {\n"
        "            print(l);\n"
        "        }\n"
        "    }\n"
        "}\n"
        "fn get_logger() {\n"
        "    if (singleton_instance == nullptr) {\n"
        "        singleton_instance = new Logger();\n"
        "    }\n"
        "    singleton_call_count = singleton_call_count + 1;\n"
        "    return singleton_instance;\n"
        "}\n"
        "let lg1 = get_logger();\n"
        "let lg2 = get_logger();\n"
        "lg1.log(\"first\").log(\"second\");\n"
        "lg2.show();\n"
        "print(lg1 == lg2);"
    )
    H.output(
        "first\n"
        "second\n"
        "True"
    )
    H.para(
        "get_logger 首次调用时创建 Logger 实例存入全局变量 singleton_instance,之后调用都返回同一实例。"
        "lg1 和 lg2 是同一个对象(lg1 == lg2 为 True),所以 lg1.log 添加的日志,lg2.show 能看到。"
        "这就是单例模式:全局唯一、状态共享。"
    )
    H.note(
        "单例适合日志器、配置中心、数据库连接池等全局共享场景。但要注意单例会增加全局状态,"
        "过度使用会降低可测试性,应谨慎使用。"
    )

    # 小结 + 练习
    H.h3("本章小结")
    H.bullet("图书管理系统演示了类间协作:Library 管理 Book 集合。")
    H.bullet("学生成绩管理用方法链优雅地添加数据,average 计算统计值。")
    H.bullet("OOP 计算器用对象状态保存历史,适合需要上下文的场景。")
    H.bullet("工厂模式用 static fn 封装构造逻辑,集中管理对象创建。")
    H.bullet("单例模式用全局变量模拟,确保全局唯一实例。")

    H.h3("练习题")
    H.number("扩展图书系统:增加 User 类,记录用户借阅的图书列表。")
    H.number("为 Student 增加 max_score() 和 min_score() 方法,返回最高最低分。")
    H.number("扩展计算器:支持取模 % 运算,并在 history 中记录时间。")
    H.number("用工厂模式为 Shape 类创建 circle_factory(r) 和 square_factory(s) 方法。")
    H.number("实现一个全局唯一的 Config 单例,支持 set(key, value) 和 get(key) 方法。")

    H.page_break()
