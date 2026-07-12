# -*- coding: utf-8 -*-
"""《H# 从入门到精通》第四部分:第六篇 高级特性(第23-27章)+ 第七篇 并发编程(第28-31章)
所有代码示例均通过 python3 interpreter.py file.hto 实机测试。
"""


def add_content(doc, H):
    # ============================================================
    # 第六篇 高级特性
    # ============================================================
    H.h1("第六篇 高级特性")

    H.para(
        "本篇深入探讨 H# 的高级语言特性,包括异常处理、Union 类型、模块系统、"
        "概念与接口,以及错误传播机制。其中部分特性(如 union 声明、? 运算符)是 "
        "Kotlin HVM 的专有语法,在 Python 树遍历解释器中以概念讲解为主,并附带"
        "可运行的模拟实现,帮助读者理解其设计思想。"
    )
    H.blank()

    # ============================================================
    # 第23章 异常处理
    # ============================================================
    H.h2("第23章 异常处理")

    H.h3("23.1 为什么需要异常处理")
    H.para(
        "在程序运行过程中,难免会遇到各种意外情况:除数为零、文件不存在、"
        "输入格式错误、数组越界等。如果没有异常处理机制,这些错误会导致"
        "程序突然崩溃,用户数据丢失,体验极差。"
    )
    H.para(
        "异常处理的核心思想是将“正常流程”与“错误处理流程”分离。"
        "正常逻辑写在 try 块中,错误处理逻辑写在 catch 块中,使代码结构清晰、"
        "易于维护。H# 提供了 try/catch/throw 三件套来实现这一机制。"
    )
    H.bullet("异常处理让错误处理代码与业务逻辑解耦")
    H.bullet("异常可以沿调用栈向上传播,直到被捕获")
    H.bullet("未捕获的异常会导致程序终止并打印错误信息")
    H.bullet("H# 的异常值可以是任意类型:字符串、数字、字典等")

    H.h3("23.2 try/catch 语法")
    H.para(
        "try/catch 是异常处理的基本结构。try 块中放置可能出错的代码,"
        "catch 块中放置错误处理代码。当 try 块中的代码抛出异常时,"
        "程序会跳转到对应的 catch 块执行。"
    )
    H.code(
        "# try/catch 基本用法\n"
        "try {\n"
        "    let x = 10;\n"
        "    let y = 0;\n"
        "    let result = x / y;\n"
        '    print(result);\n'
        "} catch (e) {\n"
        '    print("Error: " + e);\n'
        "}"
    )
    H.output("Error: Division by zero")
    H.para(
        "在这个例子中,10 / 0 触发了除零错误,解释器自动抛出异常。"
        "catch 块捕获异常,变量 e 绑定到异常值(此处为字符串),"
        "程序打印错误信息后继续执行,不会崩溃。"
    )
    H.note("catch 后的变量名(e)可以任意命名,它绑定的是 throw 抛出的值。如果 try 块中没有异常,catch 块不会执行。")

    H.h3("23.3 throw 抛出异常")
    H.para(
        "throw 语句用于主动抛出异常。你可以 throw 任何值:字符串、数字、"
        "字典甚至列表。throw 执行后,当前函数立即中断,异常沿调用栈向上传播,"
        "直到被某个 try/catch 捕获。"
    )
    H.code(
        "# 主动抛出异常\n"
        "fn check_age(age) {\n"
        "    if (age < 0) {\n"
        '        throw "Age cannot be negative";\n'
        "    }\n"
        "    return age;\n"
        "}\n"
        "try {\n"
        "    print(check_age(25));\n"
        "    print(check_age(-5));\n"
        "} catch (e) {\n"
        '    print("Caught: " + e);\n'
        "}"
    )
    H.output(
        "25\n"
        "Caught: Age cannot be negative"
    )
    H.para(
        "check_age(25) 正常返回 25 并打印。check_age(-5) 触发 throw,"
        "函数中断,异常被外层 try/catch 捕获,打印错误信息。"
    )

    H.h3("23.4 异常对象")
    H.para(
        "throw 字符串虽然简单,但携带的信息有限。实际开发中,我们常"
        "用字典来构造结构化的异常对象,包含错误码、错误消息、上下文信息等。"
    )
    H.code(
        "# 使用字典构造异常对象\n"
        "fn make_error(code, msg) {\n"
        '    return {"code": code, "message": msg};\n'
        "}\n"
        "fn validate_age(age) {\n"
        "    if (age < 0) {\n"
        '        throw make_error(400, "Age cannot be negative");\n'
        "    }\n"
        "    if (age > 150) {\n"
        '        throw make_error(400, "Age too large");\n'
        "    }\n"
        "    return age;\n"
        "}\n"
        "try {\n"
        "    print(validate_age(25));\n"
        "    print(validate_age(-5));\n"
        "} catch (e) {\n"
        '    print("Code: " + e["code"]);\n'
        '    print("Msg: " + e["message"]);\n'
        "}"
    )
    H.output(
        "25\n"
        "Code: 400\n"
        "Msg: Age cannot be negative"
    )
    H.para(
        "通过字典构造异常对象,catch 块可以访问 e[\"code\"] 和 e[\"message\"],"
        "实现结构化的错误处理。这种模式在实际项目中非常实用。"
    )

    H.h3("23.5 自定义错误类型")
    H.para(
        "为了更好地组织错误,我们可以定义一组错误创建函数,模拟自定义错误类型。"
        "每种错误类型对应一个工厂函数,生成带有特定标签的字典。"
    )
    H.code(
        "# 自定义错误类型(用字典标签区分)\n"
        'fn value_error(msg) { return {"type": "ValueError", "message": msg}; }\n'
        'fn type_error(msg) { return {"type": "TypeError", "message": msg}; }\n'
        'fn range_error(msg) { return {"type": "RangeError", "message": msg}; }\n'
        "\n"
        "fn process(data) {\n"
        "    if (data == nullptr) {\n"
        '        throw type_error("data is null");\n'
        "    }\n"
        "    if (len(data) == 0) {\n"
        '        throw value_error("data is empty");\n'
        "    }\n"
        "    if (len(data) > 100) {\n"
        '        throw range_error("data too large");\n'
        "    }\n"
        '    return "processed: " + data;\n'
        "}\n"
        "\n"
        "fn handle(data) {\n"
        "    try {\n"
        "        print(process(data));\n"
        "    } catch (e) {\n"
        '        if (e["type"] == "ValueError") {\n'
        '            print("[值错误] " + e["message"]);\n'
        '        } else if (e["type"] == "TypeError") {\n'
        '            print("[类型错误] " + e["message"]);\n'
        '        } else if (e["type"] == "RangeError") {\n'
        '            print("[范围错误] " + e["message"]);\n'
        "        } else {\n"
        '            print("[未知错误] " + e["message"]);\n'
        "        }\n"
        "    }\n"
        "}\n"
        "\n"
        'handle(nullptr);\n'
        'handle("");\n'
        'handle("hello");'
    )
    H.output(
        "[类型错误] data is null\n"
        "[值错误] data is empty\n"
        "processed: hello"
    )
    H.para(
        "通过 e[\"type\"] 标签,catch 块可以根据错误类型分发到不同的处理逻辑,"
        "实现类似其他语言多 catch 子句的效果。这是 H# 中实现自定义错误类型的"
        "推荐方式。"
    )

    H.h3("23.6 嵌套 try/catch 与异常重抛")
    H.para(
        "try/catch 可以嵌套使用。内层 catch 捕获异常后,可以进行处理,"
        "然后通过 throw 重新抛出(可能附加更多信息),让外层 catch 继续处理。"
        "这种“捕获-处理-重抛”的模式在错误信息增强方面很有用。"
    )
    H.code(
        "# 嵌套 try/catch 与重抛\n"
        "fn risky_operation() {\n"
        '    throw "Something went wrong";\n'
        "}\n"
        "try {\n"
        "    try {\n"
        "        risky_operation();\n"
        "    } catch (e) {\n"
        '        print("Inner: " + e);\n'
        '        throw "Re-thrown: " + e;\n'
        "    }\n"
        "} catch (e) {\n"
        '    print("Outer: " + e);\n'
        "}"
    )
    H.output(
        "Inner: Something went wrong\n"
        "Outer: Re-thrown: Something went wrong"
    )
    H.para(
        "内层 catch 捕获原始异常,打印后用 throw 重抛,附加了“Re-thrown:”前缀。"
        "外层 catch 捕获重抛的异常并打印。这种链式处理让错误信息逐步丰富。"
    )

    H.h3("23.7 异常处理最佳实践")
    H.bullet("只捕获你预期会发生的异常,不要用 try/catch 包裹所有代码")
    H.bullet("catch 块中应做有意义的处理:记录日志、返回默认值、重试等")
    H.bullet("避免空 catch(吞掉异常),这会让 bug 难以定位")
    H.bullet("用字典构造结构化异常对象,携带错误码和上下文")
    H.bullet("在函数边界做好错误处理,内部函数可让异常向上传播")
    H.bullet("throw 的值应当能清楚描述问题,便于调试")

    H.h3("23.8 实战:安全的除法函数")
    H.para(
        "下面实现一个完整的安全除法工具,综合运用 throw、try/catch 和"
        "结构化异常对象。"
    )
    H.code(
        "# 实战:安全除法工具\n"
        "fn safe_divide(a, b) {\n"
        "    if (b == 0) {\n"
        '        throw {"code": 1, "message": "Division by zero"};\n'
        "    }\n"
        "    return a / b;\n"
        "}\n"
        "\n"
        "fn safe_sqrt(n) {\n"
        "    if (n < 0) {\n"
        '        throw {"code": 2, "message": "Cannot sqrt negative"};\n'
        "    }\n"
        "    let guess = n;\n"
        "    let i = 0;\n"
        "    while (i < 20) {\n"
        "        guess = (guess + n / guess) / 2;\n"
        "        i = i + 1;\n"
        "    }\n"
        "    return guess;\n"
        "}\n"
        "\n"
        "fn compute(a, b) {\n"
        "    try {\n"
        "        let q = safe_divide(a, b);\n"
        "        let s = safe_sqrt(q);\n"
        '        return "OK: sqrt(" + a + "/" + b + ") = " + s;\n'
        "    } catch (e) {\n"
        '        return "ERR[" + e["code"] + "]: " + e["message"];\n'
        "    }\n"
        "}\n"
        "\n"
        "print(compute(16, 4));\n"
        "print(compute(10, 0));\n"
        "print(compute(-9, 1));"
    )
    H.output(
        "OK: sqrt(16/4) = 2\n"
        "ERR[1]: Division by zero\n"
        "ERR[2]: Cannot sqrt negative"
    )
    H.para(
        "compute 函数内部用 try/catch 保护了 safe_divide 和 safe_sqrt 两个"
        "可能出错的操作。无论哪个抛出异常,都会被捕获并返回友好的错误信息,"
        "调用者无需再处理异常。这就是异常处理的价值所在。"
    )

    H.h3("23.9 小结")
    H.para(
        "本章介绍了 H# 的异常处理机制。try/catch/throw 三件套构成了完整的"
        "异常处理体系:throw 主动抛出异常,try 包裹可能出错的代码,"
        "catch 捕获并处理异常。异常值可以是任意类型,推荐用字典构造结构化"
        "异常对象以携带丰富的错误信息。嵌套 try/catch 和异常重抛可以实现"
        "链式错误处理。"
    )
    H.h3("23.10 练习")
    H.number("编写函数 parse_int_safe(s),用 try/catch 处理非法输入,返回字典 {\"ok\": true/false, \"value\": n}。")
    H.number("实现一个栈结构,pop 空栈时抛出 {\"type\": \"EmptyError\", \"message\": \"stack is empty\"}。")
    H.number("编写嵌套 try/catch,内层捕获后记录日志并重抛,外层捕获后打印最终信息。")
    H.number("实现一个支持加/减/乘/除的计算器函数,用异常处理除零错误,并返回错误码。")

    H.page_break()

    # ============================================================
    # 第24章 Union 类型
    # ============================================================
    H.h2("第24章 Union 类型")

    H.h3("24.1 Union 类型概念")
    H.para(
        "Union 类型(联合类型)是一种代数数据类型(ADT),它允许一个值"
        "属于多种“变体”(Variant)中的一种。这类似于 Rust 的 enum、"
        "Kotlin 的 sealed class、TypeScript 的联合类型。Union 类型"
        "让数据建模更加精确和安全。"
    )
    H.para(
        "例如,一个“形状”可以是圆形、矩形或三角形。用 Union 类型表示:"
        "Shape = Circle(radius) | Rectangle(width, height) | Triangle(base, height)。"
        "每个变体携带不同的数据,但它们都属于 Shape 类型。"
    )
    H.bullet("Union 类型将相关但不同的数据形态统一在一个类型下")
    H.bullet("每个变体(Variant)有唯一的标签和自己的字段")
    H.bullet("使用时通过模式匹配判断具体是哪个变体")
    H.bullet("编译器可检查匹配是否完备(exhaustive)")

    H.h3("24.2 union 声明语法(Kotlin HVM 专有)")
    H.para(
        "Kotlin HVM 中提供了原生 union 声明语法,类似 Rust 的 enum。"
        "这是 HVM 的专有特性,Python 解释器不支持该语法,仅作概念讲解。"
    )
    H.code(
        "# Kotlin HVM 专有语法(概念示例,Python 解释器不支持)\n"
        "union Shape {\n"
        "    Circle: radius;\n"
        "    Rectangle: width, height;\n"
        "    Triangle: base, height;\n"
        "}\n"
        "\n"
        "# 构造变体实例\n"
        "let c = Shape{Circle: 5};\n"
        "let r = Shape{Rectangle: 3, 4};\n"
        "\n"
        "# 模式匹配\n"
        "fn area(s) {\n"
        "    match s {\n"
        "        Shape{Circle: r}       => 3 * r * r,\n"
        "        Shape{Rectangle: w, h} => w * h,\n"
        "        Shape{Triangle: b, h}  => (b * h) / 2,\n"
        "    }\n"
        "}"
    )
    H.note("以上是 Kotlin HVM 的概念语法。Python 解释器中需用字典+标签模拟 Union,详见 24.4 节。")

    H.h3("24.3 Variant 变体")
    H.para(
        "变体是 Union 类型的组成单元。每个变体有:一个唯一的名字(标签),"
        "以及零到多个字段。例如 Option 类型有两个变体:Some(携带一个值)"
        "和 None(不携带任何值)。Result 类型有两个变体:Ok(携带成功值)"
        "和 Err(携带错误信息)。"
    )
    H.para(
        "变体的核心价值在于“标签化”:通过检查标签,程序可以安全地知道"
        "当前值是哪种形态,从而采取对应的处理逻辑。这比传统的 null 检查"
        "或错误码更加安全和表达力强。"
    )

    H.h3("24.4 用字典模拟 Union")
    H.para(
        "在 Python 解释器端,我们可以用字典来模拟 Union 类型。核心思路:"
        "用一个 \"tag\" 字段标识变体名称,其余字段存储变体数据。"
        "配合工厂函数构造变体,用 if/else 实现模式匹配。"
    )
    H.code(
        "# 用字典模拟 Union 类型\n"
        "fn circle(r) {\n"
        '    return {"type": "Shape", "variant": "Circle", "radius": r};\n'
        "}\n"
        "fn rectangle(w, h) {\n"
        '    return {"type": "Shape", "variant": "Rectangle", "width": w, "height": h};\n'
        "}\n"
        "fn triangle(b, h) {\n"
        '    return {"type": "Shape", "variant": "Triangle", "base": b, "height": h};\n'
        "}\n"
        "\n"
        "# 模式匹配:根据 variant 标签分发\n"
        "fn area(shape) {\n"
        '    if (shape["variant"] == "Circle") {\n'
        '        return 3 * shape["radius"] * shape["radius"];\n'
        '    } else if (shape["variant"] == "Rectangle") {\n'
        '        return shape["width"] * shape["height"];\n'
        '    } else if (shape["variant"] == "Triangle") {\n'
        '        return (shape["base"] * shape["height"]) / 2;\n'
        "    }\n"
        "    return 0;\n"
        "}\n"
        "\n"
        "fn describe(shape) {\n"
        '    return shape["variant"];\n'
        "}\n"
        "\n"
        "let c = circle(5);\n"
        "let r = rectangle(3, 4);\n"
        "let t = triangle(6, 8);\n"
        'print(describe(c) + " area = " + area(c));\n'
        'print(describe(r) + " area = " + area(r));\n'
        'print(describe(t) + " area = " + area(t));'
    )
    H.output(
        "Circle area = 75\n"
        "Rectangle area = 12\n"
        "Triangle area = 24"
    )
    H.para(
        "circle/rectangle/triangle 是变体工厂函数,每个返回一个带 \"variant\" "
        "标签的字典。area 函数通过检查 variant 字段实现模式匹配,"
        "对不同变体应用不同的面积公式。这就是 Union 类型的精髓。"
    )

    H.h3("24.5 Option 类型模拟")
    H.para(
        "Option 是函数式编程中最常用的 Union 类型,表示“有值”或“无值”两种"
        "状态。它有两个变体:Some(value) 表示有值,None 表示无值。"
        "Option 可以替代 null,让“可能无值”在类型层面显式化,避免空指针异常。"
    )
    H.code(
        "# 模拟 Option 类型\n"
        "fn some(value) {\n"
        '    return {"tag": "Some", "value": value};\n'
        "}\n"
        "fn none() {\n"
        '    return {"tag": "None"};\n'
        "}\n"
        "fn is_some(opt) {\n"
        '    return opt["tag"] == "Some";\n'
        "}\n"
        "fn is_none(opt) {\n"
        '    return opt["tag"] == "None";\n'
        "}\n"
        "fn unwrap(opt) {\n"
        '    if (opt["tag"] == "Some") {\n'
        '        return opt["value"];\n'
        "    }\n"
        '    throw "Called unwrap on None";\n'
        "}\n"
        "fn unwrap_or(opt, default) {\n"
        '    if (opt["tag"] == "Some") {\n'
        '        return opt["value"];\n'
        "    }\n"
        "    return default;\n"
        "}\n"
        "\n"
        "# 安全除法:返回 Option\n"
        "fn safe_divide(a, b) {\n"
        "    if (b == 0) {\n"
        "        return none();\n"
        "    }\n"
        "    return some(a / b);\n"
        "}\n"
        "\n"
        "let r1 = safe_divide(10, 2);\n"
        "let r2 = safe_divide(10, 0);\n"
        "print(is_some(r1));\n"
        "print(is_none(r2));\n"
        "print(unwrap(r1));\n"
        "print(unwrap_or(r2, -1));"
    )
    H.output(
        "True\n"
        "True\n"
        "5\n"
        "-1"
    )
    H.para(
        "safe_divide 返回 Option 类型:成功返回 Some(结果),失败返回 None。"
        "调用者通过 is_some/is_none 检查,或用 unwrap/unwrap_or 安全取值。"
        "这比直接返回 null 或抛异常更加优雅。"
    )
    H.warning("对 None 调用 unwrap 会抛出异常。生产代码中应优先使用 unwrap_or 提供默认值,避免 panic。")

    H.h3("24.6 Result 类型模拟")
    H.para(
        "Result 类型是 Option 的增强版,它不仅表示成功或失败,还能携带"
        "错误信息。有两个变体:Ok(value) 表示成功并携带结果值,"
        "Err(error) 表示失败并携带错误信息。Result 适合需要知道失败原因的场景。"
    )
    H.code(
        "# 模拟 Result 类型\n"
        "fn ok(value) {\n"
        '    return {"tag": "Ok", "value": value};\n'
        "}\n"
        "fn err(msg) {\n"
        '    return {"tag": "Err", "error": msg};\n'
        "}\n"
        "fn is_ok(r) {\n"
        '    return r["tag"] == "Ok";\n'
        "}\n"
        "fn is_err(r) {\n"
        '    return r["tag"] == "Err";\n'
        "}\n"
        "fn get_ok(r) {\n"
        '    return r["value"];\n'
        "}\n"
        "fn get_err(r) {\n"
        '    return r["error"];\n'
        "}\n"
        "\n"
        "# 用 Result 实现整数解析\n"
        "fn parse_int(s) {\n"
        "    try {\n"
        "        return ok(int(s));\n"
        "    } catch (e) {\n"
        '        return err("parse failed: " + e);\n'
        "    }\n"
        "}\n"
        "\n"
        'let p1 = parse_int("42");\n'
        'let p2 = parse_int("abc");\n'
        "print(is_ok(p1));\n"
        "print(get_ok(p1));\n"
        "print(is_err(p2));\n"
        "print(get_err(p2));"
    )
    H.output(
        "True\n"
        "42\n"
        "True\n"
        "parse failed: invalid literal for int(): abc"
    )
    H.para(
        "parse_int 用 try/catch 捕获 int() 转换异常,成功返回 Ok,失败返回 Err。"
        "调用者通过 is_ok/is_err 判断结果,分别获取值或错误信息。"
        "Result 类型让错误处理变得显式而安全。"
    )

    H.h3("24.7 小结")
    H.para(
        "本章介绍了 Union 类型的概念和模拟实现。Union 类型通过“标签+数据”的"
        "方式将多种变体统一在一个类型下,是代数数据类型的核心。"
        "Option 类型(Some/None)替代 null 表示可选值,Result 类型(Ok/Err)"
        "表示带错误信息的操作结果。在 Python 解释器中,我们用字典+标签"
        "模拟 Union,配合 if/else 实现模式匹配。Kotlin HVM 提供原生 union "
        "声明和 match 表达式,表达力更强。"
    )
    H.h3("24.8 练习")
    H.number("定义一个表示“登录状态”的 Union:Logged_in(username) | Guest | Banned(reason),并用字典模拟。")
    H.number("用 Option 类型实现 find 函数:在列表中查找元素,找到返回 Some,未找到返回 None。")
    H.number("用 Result 类型实现文件读取函数:成功返回 Ok(内容),失败返回 Err(原因)。")
    H.number("定义一个树结构的 Union:Leaf(value) | Node(left, right),并实现求深度函数。")

    H.page_break()

    # ============================================================
    # 第25章 模块与导入
    # ============================================================
    H.h2("第25章 模块与导入")

    H.h3("25.1 import 语句")
    H.para(
        "当项目规模增大时,把所有代码放在一个文件中会变得难以维护。"
        "H# 提供 import 语句,允许将代码拆分到多个 .hto 文件中,"
        "通过 import 相互引用。import 会执行目标文件,并将其中的"
        "函数和变量导入当前文件的作用域。"
    )
    H.para(
        "下面演示一个完整的多文件示例。首先创建数学工具模块文件:"
    )
    H.code(
        '# 文件: math_module.hto\n'
        "# 数学工具模块\n"
        "fn double(x) { return x * 2; }\n"
        "fn triple(x) { return x * 3; }\n"
        "fn add(a, b) { return a + b; }\n"
        "fn square(n) { return n * n; }\n"
        "let PI = 3.14159;"
    )
    H.para("然后在主文件中导入并使用:")
    H.code(
        '# 文件: main.hto\n'
        'import "math_module.hto";\n'
        "\n"
        "print(double(3));\n"
        "print(triple(10));\n"
        "print(add(2, 3));\n"
        "print(square(5));\n"
        "print(PI);"
    )
    H.output(
        "6\n"
        "30\n"
        "5\n"
        "25\n"
        "3.14159"
    )
    H.para(
        "import 语句执行了 math_module.hto,其中的 double、triple、add、"
        "square 函数和 PI 常量都被导入到当前作用域,可以直接使用。"
    )
    H.note("import 的路径是相对于当前工作目录的。运行 python3 interpreter.py main.hto 时,math_module.hto 需在同一目录。")

    H.h3("25.2 模块系统原理")
    H.para(
        "H# 的 import 机制本质上是“文件包含”:解释器读取目标文件,执行其中的"
        "顶层语句(函数定义、变量声明),然后将这些定义注入到导入者的全局"
        "环境中。这意味着:"
    )
    H.bullet("import 会执行目标文件的所有顶层代码(包括 print 语句)")
    H.bullet("导入的函数和变量与本地定义的没有区别")
    H.bullet("重复 import 同一文件会多次执行(无缓存机制)")
    H.bullet("循环导入可能导致问题,应避免 A 导入 B、B 又导入 A")

    H.h3("25.3 命名空间")
    H.para(
        "H# 的 import 是“扁平导入”:所有导出的名字直接进入当前作用域,"
        "没有模块名前缀。这与 Python 的 from module import * 类似。"
        "如果两个模块有同名函数,后导入的会覆盖先导入的。"
    )
    H.code(
        '# 文件: ns_demo.hto\n'
        "# 模拟命名空间:用字典封装\n"
        "fn create_math_ns() {\n"
        "    return {\n"
        '        "add": fn(a, b) { return a + b; },\n'
        '        "mul": fn(a, b) { return a * b; }\n'
        "    };\n"
        "}\n"
        "let Math = create_math_ns();\n"
        "print(Math[\"add\"](2, 3));\n"
        "print(Math[\"mul\"](4, 5));"
    )
    H.output(
        "5\n"
        "20"
    )
    H.para(
        "通过将函数放入字典,我们可以模拟命名空间效果:用 Module[\"func\"] "
        "访问,避免命名冲突。这是组织大型代码库的实用技巧。"
    )

    H.h3("25.4 代码组织最佳实践")
    H.bullet("按功能拆分文件:每个文件聚焦一个模块(如 string_utils.hto、math_utils.hto)")
    H.bullet("模块文件只包含函数和常量定义,避免顶层 print 等副作用")
    H.bullet("用字典封装相关函数,模拟命名空间,避免全局污染")
    H.bullet("入口文件(main.hto)负责导入模块、组织流程")
    H.bullet("避免循环导入,依赖关系应为单向的")

    H.h3("25.5 实战:多文件项目结构")
    H.para(
        "下面演示一个模拟的多文件项目。我们将创建一个字符串工具模块和一个"
        "主程序文件,展示模块化开发的完整流程。"
    )
    H.code(
        '# 文件: str_utils.hto\n'
        "# 字符串工具模块\n"
        "fn repeat(s, n) {\n"
        "    let result = \"\";\n"
        "    let i = 0;\n"
        "    while (i < n) {\n"
        "        result = result + s;\n"
        "        i = i + 1;\n"
        "    }\n"
        "    return result;\n"
        "}\n"
        "fn capitalize_first(s) {\n"
        "    if (len(s) == 0) { return s; }\n"
        "    let first = substring(s, 0, 1);\n"
        "    let rest = substring(s, 1, len(s));\n"
        "    return first + rest;\n"
        "}\n"
        "fn contains(haystack, needle) {\n"
        "    let n = len(needle);\n"
        "    let i = 0;\n"
        "    while (i <= len(haystack) - n) {\n"
        "        if (substring(haystack, i, i + n) == needle) {\n"
        "            return true;\n"
        "        }\n"
        "        i = i + 1;\n"
        "    }\n"
        "    return false;\n"
        "}"
    )
    H.code(
        '# 文件: app.hto\n'
        'import "str_utils.hto";\n'
        "\n"
        'print(repeat("ab", 3));\n'
        'print(capitalize_first("hello"));\n'
        'print(contains("hello world", "world"));\n'
        'print(contains("hello world", "xyz"));'
    )
    H.output(
        "ababab\n"
        "hello\n"
        "True\n"
        "False"
    )
    H.para(
        "str_utils.hto 提供了 repeat、capitalize_first、contains 三个字符串"
        "工具函数。app.hto 通过 import 导入后直接使用。这种“模块提供能力、"
        "主程序调用”的分层结构是大型项目的基础。"
    )

    H.h3("25.6 模块导出(讲解)")
    H.para(
        "Kotlin HVM 中设计了更完善的模块系统,支持 export 关键字显式声明"
        "导出的符号,未导出的为模块私有。这提供了更好的封装性。"
        "Python 解释器中 import 是扁平的(全部导出),通过约定(下划线前缀"
        "表示私有)来模拟封装。"
    )
    H.code(
        "# Kotlin HVM 概念语法(概念示例)\n"
        "module MathLib {\n"
        "    export fn public_func() { ... }\n"
        "    fn _private_helper() { ... }  # 不导出\n"
        "}"
    )
    H.note("Python 解释器中所有函数默认全局可见。约定以下划线开头的函数名为“私有”,仅为命名约定,不强制。")

    H.h3("25.7 小结")
    H.para(
        "本章介绍了 H# 的模块系统。import 语句实现了文件级别的代码复用,"
        "将函数和变量从一个 .hto 文件导入另一个。模块系统原理是“文件包含+"
        "全局注入”,导入的名字与本地定义无异。通过字典封装可以模拟命名空间,"
        "避免命名冲突。良好的代码组织应按功能拆分文件,模块只含定义不含副作用,"
        "依赖关系单向。"
    )
    H.h3("25.8 练习")
    H.number("创建一个 list_utils.hto 模块,实现 map/filter/reduce 三个高阶函数,并在主文件中导入使用。")
    H.number("用字典模拟命名空间,封装一组日期处理函数,通过 Date[\"format\"]() 方式调用。")
    H.number("设计一个三文件项目:config.hto(配置)、utils.hto(工具)、main.hto(入口),演示模块间依赖。")
    H.number("实现一个统计模块 stats.hto,提供 mean、median、variance 函数,导入后计算一组数据的统计量。")

    H.page_break()

    # ============================================================
    # 第26章 概念与接口
    # ============================================================
    H.h2("第26章 概念与接口")

    H.h3("26.1 concept 概念")
    H.para(
        "concept(概念)是 Kotlin HVM 中的高级特性,用于定义类型应当满足的"
        "行为契约。它类似于 TypeScript 的 interface 或 Rust 的 trait,"
        "声明了一组函数签名,任何提供了这些函数的类型都”满足“该概念。"
        "concept 实现了”静态鸭子类型“,让泛型约束更加显式。"
    )
    H.para(
        "Python 解释器中 concept 支持有限,主要作为概念讲解。实际开发中"
        "我们用类的同名方法来模拟 concept 约束。"
    )
    H.code(
        "# Kotlin HVM 概念语法(概念示例)\n"
        "concept Printable {\n"
        "    fn to_string() -> String;\n"
        "    fn print_it();\n"
        "}\n"
        "# 任何有 to_string 和 print_it 方法的类都满足 Printable"
    )
    H.note("concept 是 Kotlin HVM 专有特性。Python 解释器中用鸭子类型或类模拟,详见 26.4-26.5 节。")

    H.h3("26.2 interface 接口")
    H.para(
        "interface(接口)定义了一组方法签名,类通过实现这些方法来”满足“接口。"
        "接口是多态的基础:不同类型的对象只要实现了相同接口,就可以用统一的"
        "方式调用。H# 的 interface 在 Python 解释器中作为语法标记存在,"
        "实际多态行为由鸭子类型实现。"
    )
    H.code(
        "# Kotlin HVM 概念语法(概念示例)\n"
        "interface Drawable {\n"
        "    fn draw();\n"
        "    fn area() -> Number;\n"
        "}\n"
        "class Circle : Drawable {\n"
        "    fn draw() { ... }\n"
        "    fn area() { ... }\n"
        "}"
    )
    H.para(
        "以上是概念语法。在 Python 解释器中,我们直接定义类和方法,"
        "通过鸭子类型实现多态,无需显式声明 interface。"
    )

    H.h3("26.3 多态的多种形式")
    H.para("多态(Polymorphism)是面向对象和函数式编程的核心概念,有多种实现形式:")
    H.bullet("参数多态:泛型函数对多种类型工作,如 len() 适用于字符串/列表/字典")
    H.bullet("子类型多态:子类对象可当作父类使用(继承体系)")
    H.bullet("ad-hoc 多态:同一函数名对不同类型有不同行为(重载)")
    H.bullet("鸭子类型:不看类型声明,只看是否有需要的方法")
    H.para(
        "H# 作为动态类型语言,鸭子类型是其最主要的多态形式。"
        "只要对象有需要的方法,就可以传入函数使用,无需声明接口。"
    )

    H.h3("26.4 鸭子类型")
    H.para(
        "鸭子类型(Duck Typing)的核心理念:“如果它走起来像鸭子、叫起来像鸭子,"
        "那它就是鸭子。”在 H# 中,函数不检查参数的类型,只检查参数是否有"
        "需要的方法。这使得代码非常灵活。"
    )
    H.code(
        "# 鸭子类型:只要对象有 print_it 方法就能用\n"
        "fn print_all(items) {\n"
        "    for item in items {\n"
        "        item.print_it();\n"
        "    }\n"
        "}\n"
        "\n"
        "class Document {\n"
        "    fn init(title) {\n"
        "        self.title = title;\n"
        "    }\n"
        "    fn print_it() {\n"
        '        print("[Doc] " + self.title);\n'
        "    }\n"
        "}\n"
        "\n"
        "class Image {\n"
        "    fn init(w, h) {\n"
        "        self.w = w;\n"
        "        self.h = h;\n"
        "    }\n"
        "    fn print_it() {\n"
        '        print("[Img] " + self.w + "x" + self.h);\n'
        "    }\n"
        "}\n"
        "\n"
        'let d = new Document("Report");\n'
        "let img = new Image(800, 600);\n"
        "print_all([d, img]);"
    )
    H.output(
        "[Doc] Report\n"
        "[Img] 800x600"
    )
    H.para(
        "print_all 函数不关心 item 是 Document 还是 Image,只要它有 print_it "
        "方法就能调用。这就是鸭子类型的威力:无需接口声明,天然多态。"
    )
    H.note("H# 中 new ClassName(args) 会自动调用 init 并传入参数。这是创建对象的标准方式。")

    H.h3("26.5 用类模拟接口")
    H.para(
        "虽然 H# 支持鸭子类型,但有时我们仍希望显式定义接口契约,便于文档"
        "和约束。可以用类来模拟接口:定义一个“接口类”作为基类,实际类"
        "实现其方法。"
    )
    H.code(
        "# 用类模拟接口:可打印接口\n"
        "class Printable {\n"
        "    fn to_string() {\n"
        '        return "unknown";\n'
        "    }\n"
        "    fn print_it() {\n"
        '        print("[" + self.to_string() + "]");\n'
        "    }\n"
        "}\n"
        "\n"
        "class Document {\n"
        "    fn init(title) {\n"
        "        self.title = title;\n"
        "    }\n"
        "    fn to_string() {\n"
        '        return "Doc: " + self.title;\n'
        "    }\n"
        "    fn print_it() {\n"
        '        print("[" + self.to_string() + "]");\n'
        "    }\n"
        "}\n"
        "\n"
        "class Product {\n"
        "    fn init(name, price) {\n"
        "        self.name = name;\n"
        "        self.price = price;\n"
        "    }\n"
        "    fn to_string() {\n"
        '        return self.name + " $" + self.price;\n'
        "    }\n"
        "    fn print_it() {\n"
        '        print("[" + self.to_string() + "]");\n'
        "    }\n"
        "}\n"
        "\n"
        'let d = new Document("Report");\n'
        'let p = new Product("Pen", 5);\n'
        "d.print_it();\n"
        "p.print_it();"
    )
    H.output(
        "[Doc: Report]\n"
        "[Pen $5]"
    )
    H.para(
        "Document 和 Product 都实现了 to_string 和 print_it 方法,满足 "
        "Printable 接口契约。它们可以被统一处理,实现了多态。"
    )

    H.h3("26.6 实战:可比较接口")
    H.para(
        "下面实现一个 Comparable 接口,提供 compare 方法。然后实现一个"
        "通用的排序函数,可以对任何 Comparable 对象排序。"
    )
    H.code(
        "# 实战:可比较接口与通用排序\n"
        "class Score {\n"
        "    fn init(name, val) {\n"
        "        self.name = name;\n"
        "        self.val = val;\n"
        "    }\n"
        "    fn compare(other) {\n"
        "        if (self.val < other.val) { return -1; }\n"
        "        if (self.val > other.val) { return 1; }\n"
        "        return 0;\n"
        "    }\n"
        "    fn to_string() {\n"
        '        return self.name + ":" + self.val;\n'
        "    }\n"
        "}\n"
        "\n"
        "# 通用冒泡排序:适用于任何有 compare 方法的对象\n"
        "fn sort_by_compare(arr) {\n"
        "    let n = len(arr);\n"
        "    let i = 0;\n"
        "    while (i < n) {\n"
        "        let j = 0;\n"
        "        while (j < n - i - 1) {\n"
        "            if (arr[j].compare(arr[j + 1]) > 0) {\n"
        "                let tmp = arr[j];\n"
        "                arr[j] = arr[j + 1];\n"
        "                arr[j + 1] = tmp;\n"
        "            }\n"
        "            j = j + 1;\n"
        "        }\n"
        "        i = i + 1;\n"
        "    }\n"
        "    return arr;\n"
        "}\n"
        "\n"
        "let scores = [\n"
        '    new Score("Alice", 85),\n'
        '    new Score("Bob", 92),\n'
        '    new Score("Carol", 78)\n'
        "];\n"
        "let sorted = sort_by_compare(scores);\n"
        "for s in sorted {\n"
        "    print(s.to_string());\n"
        "}"
    )
    H.output(
        "Carol:78\n"
        "Alice:85\n"
        "Bob:92"
    )
    H.para(
        "sort_by_compare 函数通过 compare 方法比较对象大小,实现了通用排序。"
        "任何提供了 compare 方法的类都可以用这个函数排序,这就是接口的威力。"
    )

    H.h3("26.7 小结")
    H.para(
        "本章介绍了 H# 的概念与接口。concept 和 interface 是 Kotlin HVM 的"
        "高级特性,用于定义类型的行为契约。Python 解释器中通过鸭子类型和类"
        "模拟实现。鸭子类型是 H# 动态类型的优势:只要对象有需要的方法就能"
        "使用,天然多态。用类模拟接口可以显式定义契约,便于文档和约束。"
        "通用的排序/查找函数可以作用于任何满足接口的对象,体现了多态的价值。"
    )
    H.h3("26.8 练习")
    H.number("定义一个 Drawable 接口(draw/area 方法),实现 Circle 和 Rectangle 类,放入列表统一调用。")
    H.number("实现一个 Iterable 接口(has_next/next 方法),用类模拟一个 range 迭代器。")
    H.number("编写通用 max_of 函数,接受任何有 compare 方法的对象列表,返回最大值。")
    H.number("用鸭子类型实现一个日志系统:不同对象只要有 log() 方法就能记录日志。")

    H.page_break()

    # ============================================================
    # 第27章 错误传播
    # ============================================================
    H.h2("第27章 错误传播")

    H.h3("27.1 ? 运算符概念")
    H.para(
        "? 运算符是 Kotlin HVM 的专有特性,用于简化错误传播。"
        "当函数可能失败时,传统做法是用 if 检查返回值或用 try/catch 捕获异常,"
        "代码较为冗长。? 运算符将“检查-传播”浓缩为一个符号:"
        "如果操作成功,返回值;如果失败,立即将错误传播给调用者。"
    )
    H.code(
        "# Kotlin HVM 概念语法(概念示例)\n"
        "fn risky(x) {\n"
        "    if (x < 0) {\n"
        '        throw "negative";\n'
        "    }\n"
        "    return x * 2;\n"
        "}\n"
        "# ? 操作符:失败则自动传播错误\n"
        "let result = risky(5)?;\n"
        "print(result);  # 10"
    )
    H.note("? 运算符是 Kotlin HVM 专有特性。Python 解释器中用 try/catch 模拟,详见 27.4 节。")

    H.h3("27.2 propagate 机制")
    H.para(
        "错误传播(propagate)的核心思想:当一个函数内部调用另一个可能失败的"
        "函数时,如果内层失败,外层不处理错误,而是直接将错误“向上抛”给"
        "自己的调用者。这样错误会沿着调用链传递,直到某个层级决定处理它。"
    )
    H.para(
        "? 运算符的优势在于:它让“传播”成为默认行为,代码更简洁。"
        "不需要显式写 if 检查或 try/catch,只需在调用后加一个 ? 即可。"
        "只有真正需要处理错误的地方才写 catch 逻辑。"
    )
    H.bullet("? 运算符让错误传播变得简洁,减少样板代码")
    H.bullet("错误沿调用栈向上传递,直到被处理")
    H.bullet("只有需要处理错误的层级才写 catch 逻辑")
    H.bullet("代码可读性高,正常流程不被错误检查打断")

    H.h3("27.3 错误处理范式对比")
    H.para("H# 中有三种错误处理范式,各有适用场景:")
    H.bullet("异常(try/catch/throw):适合意外错误,控制流跳转明显,但可能影响性能")
    H.bullet("Result 类型(Ok/Err):适合可预期错误,显式处理,函数式风格")
    H.bullet("? 运算符:结合异常的简洁与 Result 的安全,Kotlin HVM 专有")
    H.para(
        "在 Python 解释器中,我们用 try/catch 模拟 ? 的传播行为,"
        "封装一个 propagate 辅助函数。虽然语法不如 ? 简洁,但行为等价。"
    )

    H.h3("27.4 用 try/catch 模拟 ? 传播")
    H.para(
        "下面实现一个 propagate 辅助函数,模拟 ? 运算符的行为:"
        "接受一个函数和参数,调用该函数;成功返回结果值,失败返回包含"
        "错误的字典。调用者通过检查返回值是否含 error 字段来判断成功与否。"
    )
    H.code(
        "# 用 try/catch 模拟 ? 运算符\n"
        "fn risky(x) {\n"
        "    if (x < 0) {\n"
        '        throw "negative value";\n'
        "    }\n"
        "    return x * 2;\n"
        "}\n"
        "\n"
        "# propagate:模拟 ? 的传播行为\n"
        "fn propagate(f, arg) {\n"
        "    try {\n"
        "        return f(arg);\n"
        "    } catch (e) {\n"
        '        return {"error": e};\n'
        "    }\n"
        "}\n"
        "\n"
        "let r1 = propagate(risky, 5);\n"
        "let r2 = propagate(risky, -3);\n"
        "print(r1);\n"
        'print(r2["error"]);'
    )
    H.output(
        "10\n"
        "negative value"
    )
    H.para(
        "risky(5) 成功返回 10。risky(-3) 抛出异常,propagate 捕获后返回 "
        "{\"error\": ...}。调用者通过检查返回值是否含 error 字段来"
        "决定下一步操作,实现了类似 ? 的传播效果。"
    )

    H.h3("27.5 实战:链式错误处理")
    H.para(
        "在实际项目中,一个操作常由多个步骤组成,每步都可能失败。"
        "下面实现一个管道(pipeline),用 propagate 模拟 ? 传播,"
        "实现链式错误处理:任何一步失败,整个管道立即返回错误。"
    )
    H.code(
        "# 实战:链式错误处理管道\n"
        "fn step1(x) {\n"
        "    if (x == 0) { throw \"step1 failed\"; }\n"
        "    return x + 1;\n"
        "}\n"
        "fn step2(x) {\n"
        "    if (x > 10) { throw \"step2 failed\"; }\n"
        "    return x * 2;\n"
        "}\n"
        "fn step3(x) {\n"
        "    if (x < 0) { throw \"step3 failed\"; }\n"
        "    return x - 1;\n"
        "}\n"
        "\n"
        "fn propagate(f, arg) {\n"
        "    try {\n"
        "        return f(arg);\n"
        "    } catch (e) {\n"
        '        return {"error": e};\n'
        "    }\n"
        "}\n"
        "\n"
        "fn has_error(r) {\n"
        '    return dict_has(r, "error");\n'
        "}\n"
        "\n"
        "fn pipeline(x) {\n"
        "    let r1 = propagate(step1, x);\n"
        "    if (has_error(r1)) {\n"
        '        return "Failed at step1: " + r1["error"];\n'
        "    }\n"
        "    let r2 = propagate(step2, r1);\n"
        "    if (has_error(r2)) {\n"
        '        return "Failed at step2: " + r2["error"];\n'
        "    }\n"
        "    let r3 = propagate(step3, r2);\n"
        "    if (has_error(r3)) {\n"
        '        return "Failed at step3: " + r3["error"];\n'
        "    }\n"
        '    return "OK: " + r3;\n'
        "}\n"
        "\n"
        "print(pipeline(5));\n"
        "print(pipeline(0));\n"
        "print(pipeline(20));"
    )
    H.output(
        "OK: 11\n"
        "Failed at step1: step1 failed\n"
        "Failed at step2: step2 failed"
    )
    H.para(
        "pipeline(5):step1(5)=6,step2(6)=12,step3(12)=11,成功。"
        "pipeline(0):step1(0)抛异常,立即返回失败。"
        "pipeline(20):step1(20)=21,step2(21)因 21>10 抛异常,返回失败。"
        "每一步都用 propagate 保护,任何失败都立即终止并返回错误信息。"
    )
    H.note("在 Kotlin HVM 中,以上代码可用 ? 运算符大幅简化:let r1 = step1(x)?; 一行即可完成“调用+检查+传播”。")

    H.h3("27.6 错误处理范式选择建议")
    H.bullet("简单脚本:用 try/catch,直接了当")
    H.bullet("库/API 设计:用 Result 类型,显式且安全")
    H.bullet("多步骤流程:用 propagate 模拟 ? 传播,链式处理")
    H.bullet("不可恢复错误:用 throw 向上传播直到程序顶层")
    H.bullet("可恢复错误:在就近的 catch 中处理,提供默认值或重试")

    H.h3("27.7 小结")
    H.para(
        "本章介绍了错误传播机制。? 运算符是 Kotlin HVM 的专有特性,能将"
        "\"检查-传播“浓缩为一个符号,极大简化错误处理代码。在 Python 解释器中,"
        "我们用 try/catch 封装 propagate 辅助函数模拟 ? 的行为:成功返回值,"
        "失败返回错误字典。链式错误处理管道是实战中的典型应用,任何一步失败"
        "都立即终止并传播错误。三种错误处理范式(异常/Result/?)各有适用场景,"
        "应根据项目特点选择。"
    )
    H.h3("27.8 练习")
    H.number("用 propagate 模拟 ?,实现一个文件读取管道:open -> read -> parse,任一步失败即返回错误。")
    H.number("实现一个表单验证函数,用 propagate 检查多个字段,收集所有错误或返回成功。")
    H.number("对比 try/catch 和 Result 两种方式实现同一功能(如解析配置),比较代码可读性。")
    H.number("实现一个重试包装器 retry(f, n):用 propagate 调用 f,失败则重试,最多 n 次。")

    H.page_break()

    # ============================================================
    # 第七篇 并发编程
    # ============================================================
    H.h1("第七篇 并发编程")

    H.para(
        "并发编程是现代编程语言的核心能力之一。H# 在 Kotlin HVM 中提供了"
        "完整的并发特性:async/await 异步编程、Channel 通道通信、"
        "parallel 并行计算、结构化并发等。这些特性基于 CSP(通信顺序进程)"
        "模型,强调”通过通信共享内存“而非”通过共享内存通信“。"
    )
    H.para(
        "本章介绍的并发特性(async/await、Channel、结构化并发)是 Kotlin HVM "
        "专有特性,在 Python 树遍衣解释器中为单线程模拟。如需真并行,"
        "请使用 Kotlin HVM。本篇代码示例用顺序执行模拟并发逻辑,确保在 "
        "Python 解释器中可运行,帮助读者理解并发模式的设计思想。"
    )
    H.warning("Python 解释器是单线程的,无法实现真正的并行。本篇代码示例用顺序执行模拟并发逻辑,重点在于理解并发模式和设计思想。真并行请使用 Kotlin HVM。")
    H.blank()

    # ============================================================
    # 第28章 async/await
    # ============================================================
    H.h2("第28章 async/await")

    H.h3("28.1 异步编程概念")
    H.para(
        "异步编程是一种并发编程模型,允许程序在等待 I/O 操作(如网络请求、"
        "文件读写)时不阻塞,转而执行其他任务。与同步编程(一行做完才做下一行)"
        "不同,异步编程通过”挂起-恢复“机制提高资源利用率。"
    )
    H.para(
        "异步 vs 同步的比喻:同步像在餐厅点餐后站在柜台等,异步像拿号后坐下"
        "做别的事,叫号时再去取餐。显然异步效率更高。"
    )
    H.bullet("async:声明函数为异步函数,调用后返回 Future(待完成的承诺)")
    H.bullet("await:等待 Future 完成,获取结果(期间可执行其他任务)")
    H.bullet("异步函数不阻塞线程,适合 I/O 密集型任务")
    H.bullet("CPU 密集型任务需用 parallel 实现真并行")

    H.h3("28.2 async fn 语法(Kotlin HVM 专有)")
    H.para(
        "Kotlin HVM 提供 async fn 语法声明异步函数。async 函数调用后立即"
        "返回一个 Future 对象,代表”将来会有结果“。通过 await 等待 Future "
        "完成并获取结果。这是 Kotlin HVM 专有特性,Python 解释器不支持。"
    )
    H.code(
        "# Kotlin HVM 专有语法(概念示例)\n"
        "async fn fetch_data(url) {\n"
        "    # 模拟网络请求\n"
        '    return "data from " + url;\n'
        "}\n"
        "async fn main() {\n"
        '    let result = await fetch_data("http://api.example.com");\n'
        "    print(result);\n"
        "}\n"
        "# HVM 中:async fn 立即执行,返回已完成的 Future"
    )
    H.note("async/await 是 Kotlin HVM 专有特性。Python 解释器中用回调模拟异步,详见 28.6 节。")

    H.h3("28.3 await 等待")
    H.para(
        "await 用于等待一个异步操作完成并获取结果。在 Kotlin HVM 中,"
        "await 会挂起当前协程,将控制权交还给事件循环,待 Future 完成后恢复。"
        "这使得多个异步任务可以”交替“执行,提高并发度。"
    )
    H.code(
        "# Kotlin HVM 概念语法(概念示例)\n"
        "async fn task_a() { return 10; }\n"
        "async fn task_b() { return 20; }\n"
        "async fn run() {\n"
        "    let a = await task_a();\n"
        "    let b = await task_b();\n"
        "    print(a + b);  # 30\n"
        "}"
    )

    H.h3("28.4 协程原理")
    H.para(
        "协程(Coroutine)是异步编程的底层基础。与线程不同,协程是用户态的"
        "轻量级并发单元,由程序自己调度(而非操作系统)。协程的”挂起-恢复“"
        "不涉及内核态切换,开销极小,可以轻松创建数万个协程。"
    )
    H.para("协程的执行流程:")
    H.number("调用 async 函数,创建协程并返回 Future")
    H.number("协程开始执行,遇到 await 时挂起(保存状态)")
    H.number("事件循环调度其他就绪的协程执行")
    H.number("被 await 的操作完成后,恢复挂起的协程")
    H.number("协程继续执行直到完成或再次 await")

    H.h3("28.5 事件循环")
    H.para(
        "事件循环(Event Loop)是异步编程的调度核心。它维护一个任务队列,"
        "不断取出就绪的任务执行。当所有任务都挂起时,事件循环等待 I/O 事件;"
        "当 I/O 完成时,唤醒对应的协程继续执行。事件循环让单线程也能处理"
        "大量并发连接。"
    )
    H.para(
        "Kotlin HVM 内置 WorkerPool 和调度器,自动管理事件循环。"
        "开发者只需用 async/await 编写代码,调度细节由运行时处理。"
    )

    H.h3("28.6 用回调模拟异步")
    H.para(
        "在 Python 解释器中,我们用回调函数模拟异步模式。回调(Callback)是"
        "异步编程最原始的形式:把”完成后要做的事“作为函数传入,操作完成时调用。"
        "虽然不如 async/await 优雅,但能清晰展示异步思想。"
    )
    H.code(
        "# 用回调模拟异步任务\n"
        "fn async_task(name, callback) {\n"
        '    print("Start: " + name);\n'
        '    let result = "Result of " + name;\n'
        "    callback(result);\n"
        "}\n"
        "\n"
        "fn on_complete(data) {\n"
        '    print("Callback: " + data);\n'
        "}\n"
        "\n"
        'async_task("TaskA", on_complete);\n'
        'async_task("TaskB", fn(d) { print("Inline: " + d); });'
    )
    H.output(
        "Start: TaskA\n"
        "Callback: Result of TaskA\n"
        "Start: TaskB\n"
        "Inline: Result of TaskB"
    )
    H.para(
        "async_task 接受任务名和回调函数。任务”完成“后调用 callback 传递结果。"
        "第二个调用使用了内联 Lambda 作为回调,展示了灵活的用法。"
    )

    H.h3("28.7 Future/Promise 模拟")
    H.para(
        "Future(也叫 Promise)是异步操作的”承诺“:它代表一个未来才会有结果"
        "的值。我们可以用字典模拟 Future:初始为未完成状态,poll(轮询)后"
        "执行任务并标记完成,之后可以反复获取结果。"
    )
    H.code(
        "# 用字典模拟 Future\n"
        "fn future_new(task) {\n"
        '    return {"done": false, "value": nullptr, "task": task};\n'
        "}\n"
        "fn future_poll(fut) {\n"
        '    if (not fut["done"]) {\n'
        '        fut["value"] = fut["task"]();\n'
        '        fut["done"] = true;\n'
        "    }\n"
        '    return fut["value"];\n'
        "}\n"
        "fn future_is_done(fut) {\n"
        '    return fut["done"];\n'
        "}\n"
        "\n"
        "# 创建一个”耗时“任务的 Future\n"
        "let f = future_new(fn() {\n"
        "    let sum = 0;\n"
        "    let i = 0;\n"
        "    while (i < 100) {\n"
        "        sum = sum + i;\n"
        "        i = i + 1;\n"
        "    }\n"
        "    return sum;\n"
        "});\n"
        "print(future_is_done(f));\n"
        "print(future_poll(f));\n"
        "print(future_is_done(f));\n"
        "print(future_poll(f));"
    )
    H.output(
        "False\n"
        "4950\n"
        "True\n"
        "4950"
    )
    H.para(
        "Future 初始 done=false。第一次 poll 执行任务(求和 0+1+...+99=4950)"
        "并缓存结果,done 变为 true。第二次 poll 直接返回缓存值,不重复计算。"
        "这模拟了 Future 的”惰性求值+缓存“特性。"
    )

    H.h3("28.8 实战:模拟并发任务调度")
    H.para(
        "下面模拟一个事件循环:提交多个任务,按顺序调度执行,模拟并发效果。"
        "虽然实际是顺序执行,但展示了任务调度的模式。"
    )
    H.code(
        "# 模拟事件循环与任务调度\n"
        "fn submit_task(name, work) {\n"
        '    print("[submit] " + name);\n'
        '    return {"name": name, "result": work()};\n'
        "}\n"
        "\n"
        "fn run_event_loop(tasks) {\n"
        '    print("=== Event Loop Start ===");\n'
        "    let results = [];\n"
        "    for t in tasks {\n"
        '        print("[run] " + t["name"]);\n'
        '        push(results, t["result"]);\n'
        "    }\n"
        '    print("=== Event Loop Done ===");\n'
        "    return results;\n"
        "}\n"
        "\n"
        "let tasks = [\n"
        '    submit_task("fetch", fn() { return "page.html"; }),\n'
        '    submit_task("parse", fn() { return 42; }),\n'
        '    submit_task("save", fn() { return "ok"; })\n'
        "];\n"
        "let results = run_event_loop(tasks);\n"
        "print(results);"
    )
    H.output(
        "[submit] fetch\n"
        "[submit] parse\n"
        "[submit] save\n"
        "=== Event Loop Start ===\n"
        "[run] fetch\n"
        "[run] parse\n"
        "[run] save\n"
        "=== Event Loop Done ===\n"
        "['page.html', 42, 'ok']"
    )
    H.para(
        "任务先被提交(构造),然后事件循环依次执行。在真正的异步系统中,"
        "submit 阶段创建 Future 但不执行,run 阶段才调度执行。这里用顺序"
        "执行模拟,展示了任务队列+事件循环的基本结构。"
    )

    H.h3("28.9 小结")
    H.para(
        "本章介绍了异步编程概念和 async/await 机制。async 声明异步函数,"
        "await 等待结果,底层由协程和事件循环支撑。协程是轻量级并发单元,"
        "挂起-恢复开销极小。事件循环调度任务,让单线程处理大量并发。"
        "在 Python 解释器中,我们用回调和字典模拟 Future/Promise,展示了"
        "异步编程的核心思想。Kotlin HVM 提供原生 async/await 支持,真异步。"
    )
    H.h3("28.10 练习")
    H.number("用回调模拟”下载三个文件,全部完成后汇总结果“的异步流程。")
    H.number("实现一个 LazyFuture,只在第一次 poll 时执行任务,后续返回缓存值。")
    H.number("模拟事件循环,提交 5 个任务,按优先级(高/中/低)调度执行。")
    H.number("用回调实现”串行异步“(任务A完成后启动任务B),对比并行的区别。")

    H.page_break()

    # ============================================================
    # 第29章 Channel 通道
    # ============================================================
    H.h2("第29章 Channel 通道")

    H.h3("29.1 CSP 并发模型")
    H.para(
        "CSP(Communicating Sequential Processes,通信顺序进程)是一种并发"
        "编程模型,由 Tony Hoare 于 1978 年提出。CSP 的核心理念:"
        "\"不要通过共享内存来通信,而要通过通信来共享内存。\""
        "Go 语言的并发模型即基于 CSP,Channel 是其核心原语。"
    )
    H.para(
        "在 CSP 模型中,并发单元(goroutine/协程)之间通过 Channel 传递消息,"
        "而非直接共享变量。这避免了锁竞争和数据竞争,让并发代码更安全、更易理解。"
    )
    H.bullet("CSP 强调”通信即共享“,通过 Channel 传递数据")
    H.bullet("每个并发单元独立运行,不共享可变状态")
    H.bullet("Channel 提供同步和缓冲两种模式")
    H.bullet("避免锁和数据竞争,代码更安全")

    H.h3("29.2 Channel 概念(Kotlin HVM 专有)")
    H.para(
        "Channel 是 Kotlin HVM 中的并发通信原语,类似 Go 的 channel。"
        "Channel 是一个线程安全的队列,发送方往里放数据,接收方从中取数据。"
        "Kotlin HVM 提供 chan_new/chan_send/chan_recv/chan_close 等内置函数。"
    )
    H.code(
        "# Kotlin HVM 专有语法(概念示例)\n"
        "let ch = chan_new(0);      # 0 = 无界通道\n"
        'chan_send(ch, "hello");\n'
        'chan_send(ch, "world");\n'
        "print(chan_recv(ch));       # hello\n"
        "print(chan_recv(ch));       # world\n"
        "chan_close(ch);"
    )
    H.note("Channel 是 Kotlin HVM 专有特性。Python 解释器中用字典+列表模拟,详见 29.6 节。")

    H.h3("29.3 发送与接收")
    H.para(
        "Channel 的两个基本操作:send(发送)和 recv(接收)。"
        "发送将数据放入通道,接收从通道取出数据。在无缓冲通道中,"
        "发送会阻塞直到有接收者;接收会阻塞直到有数据。这实现了同步握手。"
    )
    H.para(
        "在有缓冲通道中,发送在缓冲区未满时不阻塞;缓冲区满时阻塞等待。"
        "接收在缓冲区非空时不阻塞;缓冲区空时阻塞等待。"
    )
    H.bullet("无缓冲通道:发送和接收同步,类似面对面交接")
    H.bullet("有缓冲通道:发送在缓冲区未满时异步,类似信箱投递")
    H.bullet("通道关闭后不能再发送,但可以继续接收剩余数据")
    H.bullet("关闭且空的通道,接收会返回”通道已关闭“信号")

    H.h3("29.4 缓冲通道")
    H.para(
        "缓冲通道有一个固定容量的缓冲区。发送方在缓冲区未满时可以立即返回,"
        "不必等待接收方。这提高了并发度,但需要注意缓冲区大小权衡:"
        "太大占用内存且可能延迟发现问题,太小可能频繁阻塞。"
    )
    H.code(
        "# Kotlin HVM 概念语法(概念示例)\n"
        "let ch = chan_new(2);   # 容量为2的有界通道\n"
        "chan_send(ch, 1);       # 不阻塞\n"
        "chan_send(ch, 2);       # 不阻塞\n"
        "# chan_send(ch, 3);     # 阻塞,缓冲区已满\n"
        "print(chan_recv(ch));    # 1\n"
        "print(chan_recv(ch));    # 2"
    )

    H.h3("29.5 select 多路复用")
    H.para(
        "select 语句用于同时等待多个 Channel 操作,哪个先就绪就执行哪个。"
        "这实现了多路复用,是处理多个并发数据源的利器。"
        "Kotlin HVM 中 select 配合 match 使用,Python 解释器中用遍历模拟。"
    )
    H.code(
        "# Kotlin HVM 概念语法(概念示例)\n"
        "let ch1 = chan_new(0);\n"
        "let ch2 = chan_new(0);\n"
        'chan_send(ch2, "from-ch2");\n'
        "match select(ch1, ch2) {\n"
        '    chan recv(v) from ch1 => print("got: " + v),\n'
        '    chan recv(v) from ch2 => print("got: " + v),\n'
        "}"
    )

    H.h3("29.6 用字典模拟 Channel")
    H.para(
        "在 Python 解释器中,我们用字典+列表模拟 Channel。字典存储缓冲区"
        "(列表)、头部索引(head)和关闭标志(closed)。发送用 push 追加到末尾,"
        "接收通过 head 索引从头部取出(实现 FIFO 先进先出)。"
    )
    H.code(
        "# 用字典+列表模拟 FIFO Channel\n"
        "fn channel_new() {\n"
        '    return {"buffer": [], "head": 0, "closed": false};\n'
        "}\n"
        "fn channel_send(ch, item) {\n"
        '    if (ch["closed"]) {\n'
        '        throw "send on closed channel";\n'
        "    }\n"
        '    push(ch["buffer"], item);\n'
        "}\n"
        "fn channel_recv(ch) {\n"
        '    if (ch["head"] >= len(ch["buffer"])) {\n'
        '        throw "channel empty";\n'
        "    }\n"
        '    let item = ch["buffer"][ch["head"]];\n'
        '    ch["head"] = ch["head"] + 1;\n'
        "    return item;\n"
        "}\n"
        "fn channel_empty(ch) {\n"
        '    return ch["head"] >= len(ch["buffer"]);\n'
        "}\n"
        "fn channel_close(ch) {\n"
        '    ch["closed"] = true;\n'
        "}\n"
        "\n"
        "let ch = channel_new();\n"
        'channel_send(ch, "hello");\n'
        'channel_send(ch, "world");\n'
        'channel_send(ch, "!");\n'
        "print(channel_recv(ch));\n"
        "print(channel_recv(ch));\n"
        "print(channel_recv(ch));\n"
        "channel_close(ch);"
    )
    H.output(
        "hello\n"
        "world\n"
        "!"
    )
    H.para(
        "channel_new 创建带 buffer 列表和 head 索引的字典。send 用 push "
        "追加到末尾。recv 通过 head 索引从头部取值并递增 head,实现 FIFO。"
        "channel_empty 检查是否还有数据。channel_close 标记关闭。"
    )

    H.h3("29.7 select 多路复用模拟")
    H.para(
        "下面用遍历多个 Channel 来模拟 select:检查一组通道,返回第一个"
        "有数据的通道及其数据。这模拟了 select 的”多路等待,先就绪先执行“行为。"
    )
    H.code(
        "# 模拟 select 多路复用\n"
        "fn select(channels) {\n"
        "    for ch in channels {\n"
        "        if (not channel_empty(ch)) {\n"
        '            return {"value": channel_recv(ch)};\n'
        "        }\n"
        "    }\n"
        '    return {"value": nullptr};\n'
        "}\n"
        "\n"
        "let ch1 = channel_new();\n"
        "let ch2 = channel_new();\n"
        'channel_send(ch2, "from-ch2");\n'
        'channel_send(ch1, "from-ch1");\n'
        "\n"
        "let s1 = select([ch1, ch2]);\n"
        'print(s1["value"]);'  "\n"
        "let s2 = select([ch1, ch2]);\n"
        'print(s2["value"]);'
    )
    H.output(
        "from-ch1\n"
        "from-ch2"
    )
    H.para(
        "select 遍历通道列表,返回第一个非空通道的数据。第一次 ch1 有数据"
        "返回 from-ch1,第二次 ch1 空了,从 ch2 取出 from-ch2。"
        "真正的 select 会同时等待多个通道,这里是简化模拟。"
    )

    H.h3("29.8 小结")
    H.para(
        "本章介绍了 Channel 通道和 CSP 并发模型。CSP 强调”通过通信共享内存“,"
        "Channel 是其核心原语。Channel 分为无缓冲(同步)和有缓冲(异步)两种,"
        "发送和接收是基本操作。select 实现多路复用,同时等待多个通道。"
        "在 Python 解释器中,我们用字典+列表模拟 FIFO Channel,用遍历模拟 "
        "select。Kotlin HVM 提供原生 Channel 支持,真并发通信。"
    )
    H.h3("29.9 练习")
    H.number("用模拟 Channel 实现生产者-消费者:生产者发 5 条消息,消费者接收并打印。")
    H.number("实现一个带容量限制的有界 Channel,满时 send 应阻塞(用 throw 模拟)。")
    H.number("用 select 模拟同时等待 3 个通道,打印最先到达的数据。")
    H.number("实现一个”管道“:ch1 -> 中间处理 -> ch2 -> 最终消费,演示数据流。")

    H.page_break()

    # ============================================================
    # 第30章 并行与结构化并发
    # ============================================================
    H.h2("第30章 并行与结构化并发")

    H.h3("30.1 parallel fn 语法(讲解)")
    H.para(
        "parallel fn 是 Kotlin HVM 中声明并行函数的语法。与 async fn 不同,"
        "parallel fn 将任务提交到 WorkerPool,在独立线程上真并行执行。"
        "这适合 CPU 密集型任务(如数值计算、图像处理),能充分利用多核 CPU。"
    )
    H.code(
        "# Kotlin HVM 专有语法(概念示例)\n"
        "parallel fn heavy_compute(n) {\n"
        "    let result = 0;\n"
        "    let i = 0;\n"
        "    while (i < n) {\n"
        "        result = result + i;\n"
        "        i = i + 1;\n"
        "    }\n"
        "    return result;\n"
        "}\n"
        "let f1 = heavy_compute(1000000);  # 提交到 WorkerPool\n"
        "let f2 = heavy_compute(2000000);  # 另一个并行任务\n"
        "let r1 = await f1;                 # 等待结果\n"
        "let r2 = await f2;"
    )
    H.note("parallel fn 是 Kotlin HVM 专有特性,实现真并行。Python 解释器单线程,用顺序执行模拟。")

    H.h3("30.2 concurrent 块(讲解)")
    H.para(
        "concurrent 块是 Kotlin HVM 中结构化并发的语法。它定义一个并发作用域,"
        "块内启动的所有并发任务在块结束时必须全部完成(或出错)。"
        "这保证了不会”泄漏“悬空任务,所有并发都有明确的生命周期。"
    )
    H.code(
        "# Kotlin HVM 专有语法(概念示例)\n"
        "concurrent {\n"
        "    let f1 = async_task1();\n"
        "    let f2 = async_task2();\n"
        "    let r1 = await f1;\n"
        "    let r2 = await f2;\n"
        "    print(r1 + r2);\n"
        "}  # 块结束前,f1 和 f2 必须都完成"
    )
    H.para(
        "concurrent 块的核心约束:退出块之前,所有内部启动的任务必须完成。"
        "如果某个任务失败,块会取消其他任务并传播错误。这就是”结构化并发“。"
    )

    H.h3("30.3 线程管理")
    H.para(
        "Kotlin HVM 内置 WorkerPool 管理线程池。parallel 任务被提交到池中,"
        "由空闲线程执行。WorkerPool 的大小默认为 CPU 核心数,可根据需要调整。"
        "线程池避免了频繁创建/销毁线程的开销,复用线程提高效率。"
    )
    H.bullet("WorkerPool 管理一组工作线程,复用避免开销")
    H.bullet("parallel 任务提交到池中,由空闲线程执行")
    H.bullet("线程池大小默认为 CPU 核心数,可配置")
    H.bullet("任务队列调度:FIFO 先进先出")

    H.h3("30.4 结构化并发原则")
    H.para(
        "结构化并发(Structured Concurrency)是一种并发编程范式,要求:"
        "所有并发任务都有明确的作用域和生命周期。任务在作用域内启动,"
        "在作用域结束前必须完成(成功或失败)。这类似于结构化编程中"
        "的”花括号作用域“,避免了 goto 式的混乱控制流。"
    )
    H.para("结构化并发的三大原则:")
    H.number("作用域:并发任务在明确的代码块内启动和管理")
    H.number("完成保证:退出作用域前,所有任务必须完成")
    H.number("错误传播:任一任务失败,取消其他任务并传播错误")
    H.para(
        "结构化并发的好处:不会泄漏悬空任务,资源自动清理,错误不会丢失,"
        "代码易于推理。Kotlin HVM 的 concurrent 块是实现结构化并发的语法。"
    )

    H.h3("30.5 并发 vs 并行")
    H.para("并发(Concurrency)和并行(Parallelism)是相关但不同的概念:")
    H.bullet("并发:多任务”交替“执行(单核也能并发,靠时间片轮转)")
    H.bullet("并行:多任务”同时“执行(必须多核,真正同时)")
    H.bullet("并发是结构,并行是执行")
    H.bullet("async/await 实现并发,parallel 实现并行")
    H.para(
        "比喻:并发是一个厨师同时做三道菜(交替切换),并行是三个厨师各做一道菜。"
        "H# 中 async/await 提供并发(单线程交替),parallel 提供并行(多线程同时)。"
    )

    H.h3("30.6 实战:模拟并行计算")
    H.para(
        "下面模拟并行计算:将一个大任务拆分为多个子任务,”并行“执行后"
        "汇总结果。虽然 Python 解释器实际是顺序执行,但展示了并行计算的模式。"
    )
    H.code(
        "# 模拟并行计算:分治求和\n"
        "fn compute_chunk(start, end) {\n"
        "    let sum = 0;\n"
        "    let i = start;\n"
        "    while (i < end) {\n"
        "        sum = sum + i;\n"
        "        i = i + 1;\n"
        "    }\n"
        "    return sum;\n"
        "}\n"
        "\n"
        "# 模拟 parallel:提交多个任务,收集结果\n"
        "fn parallel_sum(n, chunks) {\n"
        '    print("Splitting " + n + " into " + chunks + " chunks");\n'
        "    let chunk_size = n / chunks;\n"
        "    let results = [];\n"
        "    let i = 0;\n"
        "    while (i < chunks) {\n"
        "        let start = i * chunk_size;\n"
        "        let end = start + chunk_size;\n"
        '        print("[worker " + i + "] " + start + ".." + end);\n'
        "        push(results, compute_chunk(start, end));\n"
        "        i = i + 1;\n"
        "    }\n"
        "    # 汇总结果\n"
        "    let total = 0;\n"
        "    for r in results {\n"
        "        total = total + r;\n"
        "    }\n"
        "    return total;\n"
        "}\n"
        "\n"
        "let result = parallel_sum(100, 4);\n"
        'print("Total: " + result);'
    )
    H.output(
        "Splitting 100 into 4 chunks\n"
        "[worker 0] 0..25\n"
        "[worker 1] 25..50\n"
        "[worker 2] 50..75\n"
        "[worker 3] 75..100\n"
        "Total: 4950"
    )
    H.para(
        "parallel_sum 将 0-99 的求和拆分为 4 个块(0-24, 25-49, 50-74, 75-99),"
        "每个 worker 计算一块,最后汇总。在 Kotlin HVM 中,这些 worker 会真正"
        "并行执行;这里顺序模拟,展示了分治-汇总的并行模式。"
    )

    H.h3("30.7 实战:模拟结构化并发")
    H.para(
        "下面用函数模拟 concurrent 块:在一个”作用域“内执行多个任务,"
        "任一失败则取消全部并返回错误。"
    )
    H.code(
        "# 模拟结构化并发:concurrent 作用域\n"
        "fn concurrent_scope(tasks) {\n"
        '    print("=== concurrent scope start ===");\n'
        "    let results = [];\n"
        "    let i = 0;\n"
        "    while (i < len(tasks)) {\n"
        "        let r = propagate(tasks[i]);\n"
        '        if (dict_has(r, "error")) {\n'
        '            print("[scope] task " + i + " failed: " + r["error"]);\n'
        '            print("[scope] cancelling remaining tasks");\n'
        '            return {"ok": false, "error": r["error"]};\n'
        "        }\n"
        "        push(results, r);\n"
        "        i = i + 1;\n"
        "    }\n"
        '    print("=== concurrent scope done ===");\n'
        '    return {"ok": true, "results": results};\n'
        "}\n"
        "\n"
        "fn propagate(task) {\n"
        "    try { return task(); }\n"
        '    catch (e) { return {"error": e}; }\n'
        "}\n"
        "\n"
        "# 成功场景\n"
        "let ok_tasks = [\n"
        '    fn() { return 10; },\n'
        '    fn() { return 20; },\n'
        '    fn() { return 30; }\n'
        "];\n"
        "let r1 = concurrent_scope(ok_tasks);\n"
        'print(r1["ok"]);\n'
        'print(r1["results"]);'  "\n"
        "\n"
        "# 失败场景\n"
        "let bad_tasks = [\n"
        '    fn() { return 1; },\n'
        '    fn() { throw "task 1 failed"; },\n'
        '    fn() { return 3; }\n'
        "];\n"
        "let r2 = concurrent_scope(bad_tasks);\n"
        'print(r2["ok"]);'
    )
    H.output(
        "=== concurrent scope start ===\n"
        "=== concurrent scope done ===\n"
        "True\n"
        "[10, 20, 30]\n"
        "=== concurrent scope start ===\n"
        "[scope] task 1 failed: task 1 failed\n"
        "[scope] cancelling remaining tasks\n"
        "False"
    )
    H.para(
        "concurrent_scope 模拟结构化并发:所有任务在作用域内执行,任一失败"
        "立即取消剩余任务并返回错误。成功时返回所有结果。这体现了结构化并发"
        "的”完成保证+错误传播“原则。"
    )

    H.h3("30.8 小结")
    H.para(
        "本章介绍了并行计算和结构化并发。parallel fn 是 Kotlin HVM 的真并行"
        "语法,提交任务到 WorkerPool 多线程执行。concurrent 块实现结构化并发,"
        "保证作用域内所有任务完成或传播错误。结构化并发的三大原则:作用域、"
        "完成保证、错误传播。并发是多任务交替执行,并行是多任务同时执行。"
        "在 Python 解释器中用顺序执行模拟并行,展示了分治-汇总和结构化作用域模式。"
    )
    H.h3("30.9 练习")
    H.number("模拟并行计算:将矩阵乘法拆分为行级子任务,”并行“计算后合并。")
    H.number("实现 concurrent_scope 的变体:收集所有错误而非遇到第一个就停止。")
    H.number("模拟 WorkerPool:固定 N 个 worker,从任务队列取任务执行。")
    H.number("对比并发与并行的模拟代码,说明二者在执行方式上的区别。")

    H.page_break()

    # ============================================================
    # 第31章 并发实战
    # ============================================================
    H.h2("第31章 并发实战")

    H.h3("31.1 生产者-消费者模式")
    H.para(
        "生产者-消费者是经典的并发模式:生产者负责生成数据放入通道,"
        "消费者负责从通道取出数据处理。两者通过 Channel 解耦,"
        "可以独立运行、速度不必一致。这是流式数据处理的基础。"
    )
    H.code(
        "# 生产者-消费者模式(用模拟 Channel)\n"
        "fn channel_new() {\n"
        '    return {"buffer": [], "head": 0, "closed": false};\n'
        "}\n"
        "fn channel_send(ch, item) {\n"
        '    push(ch["buffer"], item);\n'
        "}\n"
        "fn channel_recv(ch) {\n"
        '    let item = ch["buffer"][ch["head"]];\n'
        '    ch["head"] = ch["head"] + 1;\n'
        "    return item;\n"
        "}\n"
        "fn channel_empty(ch) {\n"
        '    return ch["head"] >= len(ch["buffer"]);\n'
        "}\n"
        "fn channel_close(ch) {\n"
        '    ch["closed"] = true;\n'
        "}\n"
        "\n"
        "# 生产者:生成数据\n"
        "fn producer(ch, count) {\n"
        "    let i = 0;\n"
        "    while (i < count) {\n"
        '        let item = "item-" + i;\n'
        '        print("[producer] sent " + item);\n'
        "        channel_send(ch, item);\n"
        "        i = i + 1;\n"
        "    }\n"
        "    channel_close(ch);\n"
        '    print("[producer] done");\n'
        "}\n"
        "\n"
        "# 消费者:处理数据\n"
        "fn consumer(ch) {\n"
        "    let count = 0;\n"
        "    while (not channel_empty(ch)) {\n"
        "        let item = channel_recv(ch);\n"
        '        print("[consumer] got " + item);\n'
        "        count = count + 1;\n"
        "    }\n"
        '    print("[consumer] processed " + count + " items");\n'
        "    return count;\n"
        "}\n"
        "\n"
        "let ch = channel_new();\n"
        "producer(ch, 4);\n"
        "consumer(ch);"
    )
    H.output(
        "[producer] sent item-0\n"
        "[producer] sent item-1\n"
        "[producer] sent item-2\n"
        "[producer] sent item-3\n"
        "[producer] done\n"
        "[consumer] got item-0\n"
        "[consumer] got item-1\n"
        "[consumer] got item-2\n"
        "[consumer] got item-3\n"
        "[consumer] processed 4 items"
    )
    H.para(
        "生产者生成 4 条数据放入通道后关闭通道。消费者从通道取出所有数据"
        "并处理。在真正的并发系统中,两者会交替执行(生产一条消费一条),"
        "这里顺序模拟展示了完整流程。"
    )

    H.h3("31.2 fan-out/fan-in 模式")
    H.para(
        "fan-out/fan-in 是另一种经典并发模式:fan-out 将一个任务拆分为多个"
        "子任务并行执行(fan-out 展开),fan-in 将所有子任务的结果合并"
        "(fan-in 汇聚)。这适合可分治的并行计算。"
    )
    H.code(
        "# fan-out/fan-in 模式\n"
        "fn fan_out(workers, data) {\n"
        '    print("[fan-out] dispatching to " + len(workers) + " workers");\n'
        "    let results = [];\n"
        "    let i = 0;\n"
        "    while (i < len(workers)) {\n"
        "        let w = workers[i];\n"
        "        let r = w(data);\n"
        '        print("[worker " + i + "] result: " + r);\n'
        "        push(results, r);\n"
        "        i = i + 1;\n"
        "    }\n"
        "    return results;\n"
        "}\n"
        "\n"
        "fn fan_in(results) {\n"
        '    print("[fan-in] merging " + len(results) + " results");\n'
        "    let total = 0;\n"
        "    for r in results {\n"
        "        total = total + r;\n"
        "    }\n"
        "    return total;\n"
        "}\n"
        "\n"
        "let workers = [\n"
        "    fn(x) { return x + 1; },\n"
        "    fn(x) { return x * 2; },\n"
        "    fn(x) { return x * x; }\n"
        "];\n"
        "let partial = fan_out(workers, 5);\n"
        "let final = fan_in(partial);\n"
        'print("Final: " + final);'
    )
    H.output(
        "[fan-out] dispatching to 3 workers\n"
        "[worker 0] result: 6\n"
        "[worker 1] result: 10\n"
        "[worker 2] result: 25\n"
        "[fan-in] merging 3 results\n"
        "Final: 41"
    )
    H.para(
        "fan_out 将数据 5 分发给 3 个 worker(分别做+1、*2、平方),"
        "得到 [6, 10, 25]。fan_in 将结果求和得到 41。"
        "在真并行系统中,3 个 worker 会同时执行,这里顺序模拟。"
    )

    H.h3("31.3 超时控制")
    H.para(
        "在并发编程中,超时控制非常重要:如果一个任务耗时过长,不能无限等待,"
        "应设置超时,超时后取消任务或返回默认值。这防止了资源被长时间占用。"
    )
    H.code(
        "# 超时控制模拟\n"
        "fn with_timeout(task, timeout_ms, default) {\n"
        '    print("[timeout] starting task, limit=" + timeout_ms);\n'
        "    let start = time_now();\n"
        "    let result = task();\n"
        "    let elapsed = time_now() - start;\n"
        '    print("[timeout] elapsed=" + elapsed);\n'
        "    if (elapsed > timeout_ms) {\n"
        '        print("[timeout] TIMEOUT, returning default");\n'
        "        return default;\n"
        "    }\n"
        '    print("[timeout] OK");\n'
        "    return result;\n"
        "}\n"
        "\n"
        "# 快任务\n"
        "let r1 = with_timeout(fn() {\n"
        "    let s = 0;\n"
        "    let i = 0;\n"
        "    while (i < 50) { s = s + i; i = i + 1; }\n"
        "    return s;\n"
        "}, 1000, -1);\n"
        "print(r1);\n"
        "\n"
        "# 默认值场景(模拟)\n"
        "let r2 = with_timeout(fn() { return 42; }, 0, -1);\n"
        "print(r2);"
    )
    H.output(
        "[timeout] starting task, limit=1000\n"
        "[timeout] elapsed=0\n"
        "[timeout] OK\n"
        "1225\n"
        "[timeout] starting task, limit=0\n"
        "[timeout] elapsed=0\n"
        "[timeout] OK\n"
        "42"
    )
    H.para(
        "with_timeout 记录开始时间,执行任务后计算耗时。如果超过限制,"
        "返回默认值;否则返回结果。这里任务执行极快(耗时约0),所以都未超时。"
        "在真实场景中,网络请求等耗时操作才会触发超时。"
    )

    H.h3("31.4 并发安全")
    H.para(
        "并发安全(Thread Safety)是指多线程并发访问共享数据时不会产生"
        "数据竞争或不一致。在 CSP 模型中,并发单元不共享可变状态,"
        "通过 Channel 通信,天然避免了数据竞争。这是 CSP 相对共享内存+锁"
        "模型的优势。"
    )
    H.bullet("CSP 模型通过 Channel 通信,不共享可变状态,天然安全")
    H.bullet("避免使用全局可变变量,减少竞争风险")
    H.bullet("如需共享状态,用 Channel 而非直接共享变量")
    H.bullet("不可变数据(如字符串、创建后的字典)天然安全")
    H.warning("Python 解释器单线程,无并发安全问题。但在 Kotlin HVM 多线程环境下,必须注意并发安全。避免多个协程同时修改同一字典/列表。")

    H.h3("31.5 实战:并发下载模拟")
    H.para(
        "下面综合运用并发模式,模拟一个并发下载场景:多个 URL 同时下载,"
        "收集所有结果,带超时控制。这是 Web 爬虫的基础模式。"
    )
    H.code(
        "# 并发下载模拟\n"
        "fn download(url) {\n"
        '    print("[download] fetching " + url);\n'
        '    let size = len(url) * 100;\n'
        '    return {"url": url, "size": size, "status": 200};\n'
        "}\n"
        "\n"
        "fn download_all(urls) {\n"
        '    print("=== Concurrent Download Start ===");\n'
        "    let results = [];\n"
        "    for url in urls {\n"
        "        let r = download(url);\n"
        '        print("[done] " + r["url"] + " -> " + r["size"] + " bytes");\n'
        "        push(results, r);\n"
        "    }\n"
        '    print("=== All Downloads Complete ===");\n'
        "    return results;\n"
        "}\n"
        "\n"
        "fn summarize(results) {\n"
        "    let total = 0;\n"
        "    let ok = 0;\n"
        "    for r in results {\n"
        '        if (r["status"] == 200) {\n'
        "            ok = ok + 1;\n"
        '            total = total + r["size"];\n'
        "        }\n"
        "    }\n"
        '    return {"count": len(results), "ok": ok, "total_bytes": total};\n'
        "}\n"
        "\n"
        'let urls = ["a.com", "b.com", "c.com", "d.com"];\n'
        "let results = download_all(urls);\n"
        "let summary = summarize(results);\n"
        'print("Downloaded: " + summary["count"]);\n'
        'print("Success: " + summary["ok"]);\n'
        'print("Total: " + summary["total_bytes"] + " bytes");'
    )
    H.output(
        "=== Concurrent Download Start ===\n"
        "[download] fetching a.com\n"
        "[done] a.com -> 500 bytes\n"
        "[download] fetching b.com\n"
        "[done] b.com -> 500 bytes\n"
        "[download] fetching c.com\n"
        "[done] c.com -> 500 bytes\n"
        "[download] fetching d.com\n"
        "[done] d.com -> 500 bytes\n"
        "=== All Downloads Complete ===\n"
        "Downloaded: 4\n"
        "Success: 4\n"
        "Total: 2000 bytes"
    )
    H.para(
        "download_all 模拟并发下载多个 URL,summarize 汇总结果。"
        "在真并行系统中,4 个下载会同时进行;这里顺序模拟展示了完整的"
        "下载-收集-汇总流程。每个”下载“返回模拟的 URL、大小、状态码。"
    )

    H.h3("31.6 综合实战:任务流水线")
    H.para(
        "下面实现一个完整的任务流水线:生产 -> 处理 -> 消费,用三个"
        "并发角色协作。这是数据处理管道的经典模式。"
    )
    H.code(
        "# 综合实战:三阶段流水线\n"
        "fn channel_new() {\n"
        '    return {"buffer": [], "head": 0, "closed": false};\n'
        "}\n"
        'fn channel_send(ch, item) { push(ch["buffer"], item); }\n'
        "fn channel_recv(ch) {\n"
        '    let item = ch["buffer"][ch["head"]];\n'
        '    ch["head"] = ch["head"] + 1;\n'
        "    return item;\n"
        "}\n"
        "fn channel_empty(ch) { return ch[\"head\"] >= len(ch[\"buffer\"]); }\n"
        "fn channel_close(ch) { ch[\"closed\"] = true; }\n"
        "\n"
        "# 阶段1:生成原始数据\n"
        "fn generate(ch, count) {\n"
        "    let i = 0;\n"
        "    while (i < count) {\n"
        "        channel_send(ch, i);\n"
        "        i = i + 1;\n"
        "    }\n"
        "    channel_close(ch);\n"
        "}\n"
        "\n"
        "# 阶段2:处理(平方)\n"
        "fn process(in_ch, out_ch) {\n"
        "    while (not channel_empty(in_ch)) {\n"
        "        let v = channel_recv(in_ch);\n"
        "        channel_send(out_ch, v * v);\n"
        "    }\n"
        "    channel_close(out_ch);\n"
        "}\n"
        "\n"
        "# 阶段3:消费(累加)\n"
        "fn consume(ch) {\n"
        "    let total = 0;\n"
        "    let count = 0;\n"
        "    while (not channel_empty(ch)) {\n"
        "        let v = channel_recv(ch);\n"
        "        total = total + v;\n"
        "        count = count + 1;\n"
        "    }\n"
        '    return {"count": count, "sum": total};\n'
        "}\n"
        "\n"
        "let ch1 = channel_new();\n"
        "let ch2 = channel_new();\n"
        "generate(ch1, 5);\n"
        "process(ch1, ch2);\n"
        "let result = consume(ch2);\n"
        'print("Processed: " + result["count"] + " items");\n'
        'print("Sum of squares: " + result["sum"]);'
    )
    H.output(
        "Processed: 5 items\n"
        "Sum of squares: 30"
    )
    H.para(
        "流水线三阶段:generate 生成 0-4,process 将每个数平方(0,1,4,9,16),"
        "consume 累加得 30。三阶段通过 Channel 连接,各司其职。"
        "在真并发系统中,三阶段会并行流水执行,提高吞吐量。"
    )

    H.h3("31.7 小结")
    H.para(
        "本章通过实战模式综合运用了并发编程知识。生产者-消费者模式是流式"
        "数据处理的基础。fan-out/fan-in 模式实现分治-汇聚的并行计算。"
        "超时控制防止任务无限等待。并发安全在 CSP 模型中通过 Channel 通信"
        "天然保证。并发下载和任务流水线是综合实战,展示了多角色协作的完整流程。"
        "这些模式在 Kotlin HVM 真并行环境下威力更大,是构建高性能并发系统的基石。"
    )
    H.h3("31.8 练习")
    H.number("实现多生产者-单消费者:2 个生产者往同一通道发数据,1 个消费者处理。")
    H.number("用 fan-out/fan-in 实现并行词频统计:多个 worker 统计不同段落,fan-in 合并结果。")
    H.number("实现带超时的并发下载:每个 URL 下载有独立超时,超时返回默认值。")
    H.number("扩展流水线为四阶段:生成 -> 过滤 -> 处理 -> 消费,演示多级管道。")


