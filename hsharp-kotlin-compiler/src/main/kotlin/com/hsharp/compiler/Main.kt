
package com.hsharp.compiler

import com.hsharp.platform.Packager
import java.io.File
import kotlin.system.exitProcess

object CompilerVersion {
    const val VERSION = "0.1.0"
    const val SUPPORTED_HBC_VERSION = "v0.4"
}

fun main(args: Array<String>) {
    if (args.isEmpty()) { printUsage(); exitProcess(1) }
    try {
        when (args[0]) {
            "version", "-v", "--version" -> printVersion()
            "help", "-h", "--help" -> printUsage()
            "info" -> cmdInfo(args.drop(1))
            "validate" -> cmdValidate(args.drop(1))
            "compile" -> cmdCompile(args.drop(1))
            "run" -> cmdRun(args.drop(1))
            else -> {
                System.err.println("Unknown command: ${args[0]}")
                printUsage()
                exitProcess(1)
            }
        }
    } catch (e: Throwable) {
        System.err.println("Error: ${e.message}")
        if (System.getenv("HSHARP_DEBUG") != null) e.printStackTrace()
        exitProcess(1)
    }
}

private fun cmdInfo(args: List<String>) {
    val path = args.firstOrNull() ?: error("usage: info <file.hbc>")
    val file = HbcReader().read(File(path))
    println("HBC file        : $path")
    println("Format version  : ${file.version}")
    println("Built at        : ${file.builtAt} (epoch)")
    println("Modules         : ${file.modules.size}")
    for ((mname, mod) in file.modules) {
        println("  ▸ $mname")
        println("     instructions: ${mod.instructions.size}")
        println("     constants:   ${mod.consts.size}")
    }
}

private fun cmdValidate(args: List<String>) {
    val path = args.firstOrNull() ?: error("usage: validate <file.hbc>")
    val file = HbcReader().read(File(path))
    var ok = true
    for ((mname, mod) in file.modules) {
        for ((i, ins) in mod.instructions.withIndex()) {
            if (ins.first.isBlank()) { System.err.println("[$mname #$i] empty opcode"); ok = false }
        }
    }
    if (ok) {
        println("OK — ${file.modules.size} module(s), ${file.modules.values.sumOf { it.instructions.size }} instructions")
    } else {
        error("Validation failed")
    }
}

private fun cmdCompile(args: List<String>) {
    val positional = mutableListOf<String>()
    var hbcPath: String? = null
    var outDir: String? = null
    var target: String = detectHost()
    var entry: String? = null
    var name: String? = null
    var appIcon: String? = null
    var bundleType: String = "image"      // for jpackage
    var appVersion: String = "1.0.0"      // for jpackage (must not start with 0)

    var i = 0
    while (i < args.size) {
        when (val a = args[i]) {
            "-o", "--output" -> { outDir = args[++i] }
            "--target" -> { target = args[++i] }
            "--entry" -> { entry = args[++i] }
            "--name" -> { name = args[++i] }
            "--icon" -> { appIcon = args[++i] }
            "--type" -> { bundleType = args[++i] }
            "--app-version" -> { appVersion = args[++i] }
            else -> positional.add(a)
        }
        i++
    }
    hbcPath = hbcPath ?: positional.firstOrNull() ?: error("usage: compile <file.hbc> -o <out> [--target mac|win|linux]")
    outDir = outDir ?: error("missing --output/-o directory")
    name = name ?: File(hbcPath).nameWithoutExtension

    val hbc = HbcReader().read(File(hbcPath))
    Packager(hbc, File(hbcPath), File(outDir), name, target, entry, appIcon, bundleType, appVersion).packageAll()
}

private fun cmdRun(args: List<String>) {
    val path = args.firstOrNull() ?: error("usage: run <file.hbc>")
    com.hsharp.runtime.HbcRunner(File(path)).run()
}

private fun detectHost(): String {
    val os = System.getProperty("os.name").lowercase()
    return when {
        "mac" in os -> "mac"
        "win" in os -> "win"
        "nix" in os || "nux" in os -> "linux"
        else -> "linux"
    }
}

private fun printVersion() {
    println("h# kotlin-compiler ${CompilerVersion.VERSION}")
    println("supports .hbc format: ${CompilerVersion.SUPPORTED_HBC_VERSION}")
    println("java: ${System.getProperty("java.version")} (${System.getProperty("java.vendor")})")
}

private fun printUsage() {
    println("""
        h# kotlin-compiler ${CompilerVersion.VERSION}
        Compile .hbc bytecode into cross-platform applications.

        Usage:
          hsharp-kotlin-compiler info     <file.hbc>
          hsharp-kotlin-compiler validate <file.hbc>
          hsharp-kotlin-compiler run      <file.hbc>
          hsharp-kotlin-compiler compile  <file.hbc> -o <out-dir> [options]
          hsharp-kotlin-compiler version

        Compile options:
          -o, --output <dir>      output directory (required)
              --target <mac|win|linux>   target platform (default: host)
              --entry  <module>         module name to use as the program entry
                                        (default: 'main' or first module)
              --name   <appname>        application / bundle name
              --icon   <path>           platform icon (.icns/.ico/.png)
              --type   <image|exe|app|msi|dmg|rpm|deb>
                                        bundle type (jpackage)

        Examples:
          hsharp-kotlin-compiler info bootstrap/test_simple.hbc
          hsharp-kotlin-compiler run   bootstrap/test_simple.hbc
          hsharp-kotlin-compiler compile app.hbc -o dist/app
    """.trimIndent())
}
