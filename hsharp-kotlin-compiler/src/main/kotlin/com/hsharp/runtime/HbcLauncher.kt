/*
 * HbcLauncher
 * -----------
 * The "main" class that gets shipped inside the packaged app.  Its only job
 * is to take the .hbc path from the command line, hand it to the embedded
 * runtime, and exit with the runtime's return code.
 *
 * Usage:  java -jar hsharp-runtime.jar  path/to/app.hbc [args...]
 */
package com.hsharp.runtime

import java.io.File
import java.io.InputStream
import java.nio.file.Files

object HbcLauncher {
    @JvmStatic
    fun main(args: Array<String>) {
        // Resolve the .hbc source. Search order:
        //  1. command-line arg
        //  2. ./app.hbc next to the running jar
        //  3. classpath resource "app.hbc" (packaged inside the runtime jar)
        //  4. ./hbc/<arg-or-name>.hbc relative to the current dir
        val hbcFile: File? = when {
            args.isNotEmpty() -> File(args[0]).takeIf { it.exists() }
            else -> {
                val n = File("app.hbc")
                if (n.exists()) n else extractResourceToTemp("app.hbc")
            }
        }
        if (hbcFile == null) {
            System.err.println("H# launcher: no .hbc found.")
            System.err.println("  usage: HbcLauncher <file.hbc> [program-args...]")
            System.err.println("  or place 'app.hbc' next to this jar / on the classpath.")
            kotlin.system.exitProcess(2)
        }
        val runner = HbcRunner(hbcFile)
        try {
            val result = runner.run()
            if (System.getenv("HSHARP_DEBUG") != null && result !is HNull) {
                System.err.println("[h#] returned: ${result.toDisplayString()}")
            }
        } catch (e: HSharpRuntimeError) {
            System.err.println("H# runtime error: ${e.message}")
            kotlin.system.exitProcess(1)
        } catch (e: Throwable) {
            System.err.println("Fatal: ${e.message}")
            if (System.getenv("HSHARP_DEBUG") != null) e.printStackTrace()
            kotlin.system.exitProcess(1)
        }
    }

    /** Copy a classpath resource to a temp file (jpackage ships the jar
     *  without exploding it, so this is the simplest way to get at the HBC). */
    private fun extractResourceToTemp(name: String): File? {
        val stream: InputStream = HbcLauncher::class.java.classLoader
            .getResourceAsStream(name) ?: return null
        val tmp = Files.createTempFile("hsharp-app-", ".hbc").toFile()
        tmp.deleteOnExit()
        stream.use { input -> Files.newOutputStream(tmp.toPath()).use { input.copyTo(it) } }
        return tmp
    }
}
