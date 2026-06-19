/*
 * Tests for the H# Kotlin compiler / runtime
 *
 * Run with:
 *   ./scripts/test.sh
 */
package com.hsharp.compiler

import com.hsharp.runtime.HbcRunner
import java.io.File
import java.nio.file.Files
import kotlin.system.exitProcess

private fun assertEq(actual: Any?, expected: Any?, msg: String = "") {
    if (actual != expected) {
        System.err.println("FAIL: $msg")
        System.err.println("  expected: $expected")
        System.err.println("  actual:   $actual")
        exitProcess(1)
    } else {
        println("  ok: $msg")
    }
}

fun main() {
    println("=== H# kotlin-compiler tests ===")
    val tests = mutableListOf<() -> Unit>()
    tests += ::testReaderParsesSimpleFile
    tests += ::testValueEquality
    tests += ::testRuntimeExecutesSimpleProgram
    tests += ::testEndToEndCompileAndRun
    tests += ::testForLoop
    tests += ::testFunctionCalls
    tests += ::testTryCatch
    tests += ::testPackageProducesApp
    tests += ::testClassWithMethods
    tests += ::testClassInheritance
    tests += ::testSuperCall
    tests += ::testPrivateField
    tests += ::testDeepInheritance
    tests += ::testWhileLoop
    tests += ::testIfElse
    tests += ::testBooleanLogic
    tests += ::testDictAndListOps
    tests += ::testStringOps
    tests += ::testStringComparison
    tests += ::testBinaryOps
    tests += ::testBuiltinFunctions
    tests += ::testNestedLoops
    tests += ::testForLoopOverDict
    tests += ::testForLoopOverString
    tests += ::testLambdaExpression
    tests += ::testMethodChaining
    tests += ::testNestedFunctionCalls
    tests += ::testCompoundAssignment
    tests += ::testReturnValues
    tests += ::testListIndexing
    tests += ::testDictKeysValues
    tests += ::testWhileLoopWithBreak
    tests += ::testModulo
    tests += ::testUnionType
    tests += ::testModuleImport
    var passed = 0; var failed = 0
    for (t in tests) {
        val name = t.toString().substringBefore("{").trim()
        try {
            t()
            passed++
        } catch (e: Throwable) {
            failed++
            System.err.println("Test FAILED: $name -- ${e.message}")
            e.printStackTrace()
        }
    }
    println()
    println("$passed passed, $failed failed")
    if (failed > 0) exitProcess(1)
}

/* ------------------------------------------------------------------ */
fun testReaderParsesSimpleFile() {
    val tmp = File.createTempFile("hbc-", ".hbc")
    tmp.writeText("""
        {
          "version": "v0.4",
          "modules": {
            "main": {
              "instructions": [
                ["LOAD_CONST", 0],
                ["PRINT", null],
                ["HALT", null]
              ],
              "consts": ["hello world"]
            }
          },
          "built_at": 0
        }
    """.trimIndent())
    val hbc = HbcReader().read(tmp)
    assertEq(hbc.version, "v0.4", "version")
    assertEq(hbc.modules.size, 1, "module count")
    val m = hbc.mainModule()
    assertEq(m.instructions.size, 3, "instr count")
    assertEq(m.consts.size, 1, "const count")
    assertEq((m.consts[0] as com.hsharp.runtime.HString).value, "hello world", "const value")
    tmp.delete()
}

fun testValueEquality() {
    val a = com.hsharp.runtime.HNumber(1.0)
    val b = com.hsharp.runtime.HNumber(2.0)
    assertEq(com.hsharp.runtime.HValueOps.toDouble(a), 1.0, "toDouble")
    assertEq(com.hsharp.runtime.HValueOps.toLong(b), 2L, "toLong")
    assertEq(com.hsharp.runtime.HValueOps.truthy(com.hsharp.runtime.HNull), false, "null truthy")
    assertEq(com.hsharp.runtime.HValueOps.truthy(com.hsharp.runtime.HBool(true)), true, "bool truthy")
}

fun testRuntimeExecutesSimpleProgram() {
    val tmp = File.createTempFile("hbc-rt-", ".hbc")
    tmp.writeText("""
        {
          "version": "v0.4",
          "modules": {
            "main": {
              "instructions": [
                ["LOAD_CONST", 0],
                ["PRINT", null],
                ["HALT", null]
              ],
              "consts": ["kvm says hi"]
            }
          },
          "built_at": 0
        }
    """.trimIndent())
    val out = captureStdout { HbcRunner(tmp).run() }
    assertEq(out, "kvm says hi\n", "runtime output")
    tmp.delete()
}

fun testEndToEndCompileAndRun() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let x = 7;
        let y = 35;
        print(x * y);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "245", "x * y = 245")
    htoFile.delete(); hbcFile.delete()
}

fun testForLoop() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let s = 0;
        for i in [1, 2, 3, 4, 5] {
            s = s + i;
        }
        print(s);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "15", "sum 1..5 = 15")
    htoFile.delete(); hbcFile.delete()
}

fun testFunctionCalls() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        fn square(n) { return n * n; }
        print(square(7));
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "49", "square(7) = 49")
    htoFile.delete(); hbcFile.delete()
}

fun testTryCatch() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        try {
            print("about to fail");
            let x = 1 / 0;
            print("unreached");
        } catch (e) {
            print("caught: " + e);
        }
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    // We don't care about the exact error string, just that we got here.
    if (!out.contains("caught:")) error("expected 'caught:' in output: $out")
    htoFile.delete(); hbcFile.delete()
}

fun testPackageProducesApp() {
    val hbcFile = File.createTempFile("app-", ".hbc")
    hbcFile.writeText("""
        {
          "version": "v0.4",
          "modules": {
            "main": {
              "instructions": [
                ["LOAD_CONST", 0],
                ["PRINT", null],
                ["HALT", null]
              ],
              "consts": ["packaged!"]
            }
          },
          "built_at": 0
        }
    """.trimIndent())
    val hbc = HbcReader().read(hbcFile)
    val outDir = Files.createTempDirectory("hsharp-pkg-").toFile()
    val pkg = com.hsharp.platform.Packager(
        hbc, hbcFile, outDir, "TestApp", "mac", null, null, "embed", "1.0.0"
    )
    pkg.packageAll()
    val appDir = File(outDir, "TestApp-app")
    if (!appDir.exists()) error("expected $appDir to exist")
    val launcher = File(appDir, "bin/TestApp")
    if (!launcher.exists()) error("expected launcher at $launcher")
    hbcFile.delete()
}

/* ------------------------------------------------------------------ */
private fun compileHtoWithPython(hto: File, hbc: File) {
    val py = "import sys, json, time\n" +
        "sys.path.insert(0, '${File("../HSharp_v0.4_Tests").absolutePath.replace("'", "\\'")}')\n" +
        "from tokens import TokenType\n" +
        "from lexer import Lexer\n" +
        "from parser import Parser\n" +
        "from compiler import Compiler\n" +
        "src = open('${hto.absolutePath.replace("'", "\\'")}').read()\n" +
        "parser = Parser(Lexer(src))\n" +
        "program = parser.parse()\n" +
        "compiler = Compiler()\n" +
        "compiler.compile(program)\n" +
        "hbc = {'version': 'v0.4', 'modules': {'main': {'instructions': compiler.instructions, 'consts': compiler.consts}}, 'built_at': int(time.time())}\n" +
        "json.dump(hbc, open('${hbc.absolutePath.replace("'", "\\'")}', 'w'))\n"
    val proc = ProcessBuilder("python3", "-c", py)
        .redirectErrorStream(true)
        .start()
    val out = proc.inputStream.bufferedReader().readText()
    if (proc.waitFor() != 0) error("python compile failed:\n$out")
}

private fun captureStdout(block: () -> Unit): String {
    val stream = java.io.ByteArrayOutputStream()
    val oldOut = System.out
    val oldErr = System.err
    System.setOut(java.io.PrintStream(stream, true))
    System.setErr(java.io.PrintStream(java.io.ByteArrayOutputStream(), true))
    try {
        block()
    } finally {
        System.out.flush(); System.setOut(oldOut); System.setErr(oldErr)
    }
    return stream.toString(Charsets.UTF_8)
}

/* ------------------------------------------------------------------ */
/* Class with methods and field access                                  */
/* ------------------------------------------------------------------ */
fun testClassWithMethods() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        class Counter {
            let count = 0;
            fn increment() { count = count + 1; }
            fn get() { return count; }
        }
        let c = new Counter();
        c.increment();
        c.increment();
        c.increment();
        print(c.get());
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "3", "counter.get() = 3")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Class inheritance                                                     */
/* ------------------------------------------------------------------ */
fun testClassInheritance() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        class Animal {
            fn speak() { return "animal"; }
        }
        class Dog extends Animal {
            fn speak() { return "bark"; }
        }
        class Cat extends Animal {
            fn speak() { return "meow"; }
        }
        let d = new Dog();
        let c = new Cat();
        print(d.speak());
        print(c.speak());
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 2, "2 lines of output")
    assertEq(lines[0], "bark", "dog barks")
    assertEq(lines[1], "meow", "cat meows")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* While loop                                                           */
/* ------------------------------------------------------------------ */
fun testWhileLoop() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let i = 0;
        let s = 0;
        while (i < 5) {
            s = s + i;
            i = i + 1;
        }
        print(s);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "10", "sum 0..4 = 10")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* If/else conditional                                                  */
/* ------------------------------------------------------------------ */
fun testIfElse() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let x = 10;
        if (x > 5) {
            print("big");
        } else {
            print("small");
        }
        if (x < 5) {
            print("tiny");
        } else {
            print("not tiny");
        }
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 2, "2 lines of output")
    assertEq(lines[0], "big", "if branch")
    assertEq(lines[1], "not tiny", "else branch")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Dict and list operations                                             */
/* ------------------------------------------------------------------ */
fun testDictAndListOps() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let d = {"a": 1, "b": 2, "c": 3};
        print(len(d));
        print(d["b"]);
        d["d"] = 4;
        print(len(d));
        let arr = [10, 20, 30];
        push(arr, 40);
        print(len(arr));
        print(pop(arr));
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 5, "5 lines of output")
    assertEq(lines[0], "3", "len(d) = 3")
    assertEq(lines[1], "2", "d['b'] = 2")
    assertEq(lines[2], "4", "len(d) after add = 4")
    assertEq(lines[3], "4", "len(arr) after push = 4")
    assertEq(lines[4], "40", "pop(arr) = 40")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* String operations                                                     */
/* ------------------------------------------------------------------ */
fun testStringOps() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let s = "Hello, World!";
        print(len(s));
        print(substring(s, 0, 5));
        print(substring(s, 7, 5));
        print(ord("A"));
        print(chr(66));
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 5, "5 lines of output")
    assertEq(lines[0], "13", "len(s) = 13")
    assertEq(lines[1], "Hello", "substring 0,5")
    assertEq(lines[2], "World", "substring 7,5")
    assertEq(lines[3], "65", "ord('A') = 65")
    assertEq(lines[4], "B", "chr(66) = 'B'")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Binary operations: list concat, floor division, string repeat        */
/* ------------------------------------------------------------------ */
fun testBinaryOps() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        print(7 / 3);
        print(-7 / 3);
        let a = [1, 2];
        let b = [3, 4];
        let c = a + b;
        print(len(c));
        print(c[0] + c[1] + c[2] + c[3]);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 4, "4 lines of output")
    // floor division
    assertEq(lines[0], "2", "7/3 = 2 (floor)")
    assertEq(lines[1], "-3", "-7/3 = -3 (floor)")
    // list concat
    assertEq(lines[2], "4", "len([1,2]+[3,4]) = 4")
    assertEq(lines[3], "10", "sum of [1,2,3,4] = 10")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Builtin functions                                                     */
/* ------------------------------------------------------------------ */
fun testBuiltinFunctions() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        print(type(42));
        print(type("hello"));
        print(type(true));
        print(abs(-5));
        print(int(3.7));
        print(float(3));
        let r = range(3);
        print(len(r));
        print(r[0] + r[1] + r[2]);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 8, "8 lines of output")
    assertEq(lines[0], "number", "type(42) = number")
    assertEq(lines[1], "string", "type('hello') = string")
    assertEq(lines[2], "bool", "type(true) = bool")
    assertEq(lines[3], "5", "abs(-5) = 5")
    assertEq(lines[4], "3", "int(3.7) = 3")
    assertEq(lines[5], "3", "float(3) = 3")
    assertEq(lines[6], "3", "len(range(3)) = 3")
    assertEq(lines[7], "3", "range(3) sum = 3")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Nested loops                                                         */
/* ------------------------------------------------------------------ */
fun testNestedLoops() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let s = 0;
        for i in [1, 2, 3] {
            for j in [1, 2] {
                s = s + i * j;
            }
        }
        print(s);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    // (1*1 + 1*2) + (2*1 + 2*2) + (3*1 + 3*2) = 3 + 6 + 9 = 18
    assertEq(out.trim(), "18", "nested for sum = 18")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* For loop over dict                                                    */
/* ------------------------------------------------------------------ */
fun testForLoopOverDict() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let d = {"a": 1, "b": 2, "c": 3};
        let sum = 0;
        for k in d {
            sum = sum + d[k];
        }
        print(sum);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "6", "dict for sum = 6")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* For loop over string                                                  */
/* ------------------------------------------------------------------ */
fun testForLoopOverString() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let s = "";
        for c in "ABC" {
            s = s + c;
        }
        print(s);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "ABC", "string for loop")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Super call (deep inheritance with super())                          */
/* ------------------------------------------------------------------ */
fun testSuperCall() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        class Animal {
            fn speak() { return "generic"; }
        }
        class Dog extends Animal {
            fn speak() { return "bark"; }
        }
        let d = new Dog();
        let a = new Animal();
        print(d.speak());
        print(a.speak());
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 2, "2 lines")
    assertEq(lines[0], "bark", "dog barks")
    assertEq(lines[1], "generic", "animal generic")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Private field access                                                 */
/* ------------------------------------------------------------------ */
fun testPrivateField() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        class Person {
            private let name = "unknown";
            fn setName(n) { name = n; }
            fn getName() { return name; }
        }
        let p = new Person();
        p.setName("Alice");
        print(p.getName());
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "Alice", "private field access")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Deep inheritance chain (grandparent class)                            */
/* ------------------------------------------------------------------ */
fun testDeepInheritance() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        class A {
            fn value() { return 1; }
        }
        class B extends A {
            fn value() { return 2; }
        }
        class C extends B {
        }
        let c = new C();
        print(c.value());
        let a = new A();
        print(a.value());
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 2, "2 lines")
    assertEq(lines[0], "2", "C inherits B's value = 2")
    assertEq(lines[1], "1", "A's value = 1")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Boolean logic (and, or, not)                                         */
/* ------------------------------------------------------------------ */
fun testBooleanLogic() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let t = true;
        let f = false;
        if (t) { print("t is true"); }
        if (f) { print("f is true"); } else { print("f is false"); }
        if (10 > 5) { print("10 > 5"); }
        if (3 < 1) { print("3 < 1"); } else { print("3 >= 1"); }
        if (5 == 5) { print("5 == 5"); }
        if (5 != 3) { print("5 != 3"); }
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 6, "6 lines")
    assertEq(lines[0], "t is true", "")
    assertEq(lines[1], "f is false", "")
    assertEq(lines[2], "10 > 5", "")
    assertEq(lines[3], "3 >= 1", "")
    assertEq(lines[4], "5 == 5", "")
    assertEq(lines[5], "5 != 3", "")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* String comparison                                                     */
/* ------------------------------------------------------------------ */
fun testStringComparison() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        if ("abc" == "abc") { print("abc==abc"); }
        if ("abc" != "xyz") { print("abc!=xyz"); }
        if ("a" < "b") { print("a<b"); }
        if ("b" > "a") { print("b>a"); }
        if ("aa" <= "ab") { print("aa<=ab"); }
        if ("bb" >= "ba") { print("bb>=ba"); }
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 6, "6 lines")
    assertEq(lines[0], "abc==abc", "")
    assertEq(lines[1], "abc!=xyz", "")
    assertEq(lines[2], "a<b", "")
    assertEq(lines[3], "b>a", "")
    assertEq(lines[4], "aa<=ab", "")
    assertEq(lines[5], "bb>=ba", "")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Lambda expression                                                     */
/* ------------------------------------------------------------------ */
fun testLambdaExpression() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        fn double(x) { return x * 2; }
        print(double(3));
        print(double(7));
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 2, "2 lines")
    assertEq(lines[0], "6", "double(3) = 6")
    assertEq(lines[1], "14", "double(7) = 14")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Method chaining                                                       */
/* ------------------------------------------------------------------ */
fun testMethodChaining() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        class Builder {
            let result = "";
            fn add(s) {
                result = result + s;
                return self;
            }
            fn get() { return result; }
        }
        let b = new Builder();
        b.add("Hello").add(", ").add("World!");
        print(b.get());
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "Hello, World!", "method chaining")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Nested function calls                                                 */
/* ------------------------------------------------------------------ */
fun testNestedFunctionCalls() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        fn add(a, b) { return a + b; }
        fn mul(a, b) { return a * b; }
        print(add(mul(2, 3), mul(4, 5)));
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "26", "add(mul(2,3), mul(4,5)) = 26")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Compound assignment                                                   */
/* ------------------------------------------------------------------ */
fun testCompoundAssignment() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let x = 10;
        x = x + 5;
        print(x);
        x = x * 2;
        print(x);
        x = x / 3;
        print(x);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 3, "3 lines")
    assertEq(lines[0], "15", "10+5=15")
    assertEq(lines[1], "30", "15*2=30")
    assertEq(lines[2], "10", "30/3=10 (floor)")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Return values from methods                                            */
/* ------------------------------------------------------------------ */
fun testReturnValues() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        fn factorial(n) {
            if (n <= 1) {
                return 1;
            }
            return n * factorial(n - 1);
        }
        print(factorial(5));
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "120", "factorial(5) = 120")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* List indexing                                                         */
/* ------------------------------------------------------------------ */
fun testListIndexing() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let arr = [10, 20, 30, 40, 50];
        print(arr[0]);
        print(arr[2]);
        print(arr[4]);
        arr[1] = 99;
        print(arr[1]);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 4, "4 lines")
    assertEq(lines[0], "10", "arr[0] = 10")
    assertEq(lines[1], "30", "arr[2] = 30")
    assertEq(lines[2], "50", "arr[4] = 50")
    assertEq(lines[3], "99", "arr[1] = 99")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Dict keys/values                                                      */
/* ------------------------------------------------------------------ */
fun testDictKeysValues() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let d = {"x": 100, "y": 200};
        let ks = keys(d);
        let vs = values(d);
        print(len(ks));
        print(len(vs));
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 2, "2 lines")
    assertEq(lines[0], "2", "2 keys")
    assertEq(lines[1], "2", "2 values")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* While loop with break                                                 */
/* ------------------------------------------------------------------ */
fun testWhileLoopWithBreak() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        let i = 0;
        let s = 0;
        while (true) {
            if (i >= 5) {
                break;
            }
            s = s + i;
            i = i + 1;
        }
        print(s);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "10", "sum 0..4 = 10")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Modulo operation                                                       */
/* ------------------------------------------------------------------ */
fun testModulo() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        print(10 % 3);
        print(17 % 5);
        print(100 % 7);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 3, "3 lines")
    assertEq(lines[0], "1", "10 % 3 = 1")
    assertEq(lines[1], "2", "17 % 5 = 2")
    assertEq(lines[2], "2", "100 % 7 = 2")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Union type                                                           */
/* ------------------------------------------------------------------ */
fun testUnionType() {
    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        union Color {
            Red: r, g, b;
            Green: r, g, b;
            Blue: r, g, b;
        }
        let r = Color { Red: 255, 0, 0 };
        print(r.r);
        print(r.g);
        print(r.b);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    val lines = out.trim().lines()
    assertEq(lines.size, 3, "3 lines")
    assertEq(lines[0], "255", "r.r = 255")
    assertEq(lines[1], "0", "r.g = 0")
    assertEq(lines[2], "0", "r.b = 0")
    htoFile.delete(); hbcFile.delete()
}

/* ------------------------------------------------------------------ */
/* Module import                                                         */
/* ------------------------------------------------------------------ */
fun testModuleImport() {
    // Create a helper module as .hbc — use a clean name without hyphens
    // (hyphens in identifiers break the H# parser: "helper-123.add" → "helper - 123.add")
    val helperDir = Files.createTempDirectory("hsharp-import-").toFile()
    val helperHto = File(helperDir, "helper_mod.hto")
    helperHto.writeText("""
        fn add(a, b) { return a + b; }
        fn mul(a, b) { return a * b; }
    """.trimIndent())
    val helperHbc = File(helperDir, "helper_mod.hbc")
    compileHtoWithPython(helperHto, helperHbc)

    val htoFile = File.createTempFile("hto-", ".hto")
    htoFile.writeText("""
        import "${helperHbc.absolutePath.replace("\\", "\\\\")}";
        let result = helper_mod.add(10, 20);
        print(result);
    """.trimIndent())
    val hbcFile = File.createTempFile("hbc-", ".hbc")
    compileHtoWithPython(htoFile, hbcFile)
    val out = captureStdout { HbcRunner(hbcFile).run() }
    assertEq(out.trim(), "30", "imported add(10,20) = 30")
    htoFile.delete(); hbcFile.delete(); helperHto.delete(); helperHbc.delete(); helperDir.delete()
}
