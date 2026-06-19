/*
 * Packager
 * --------
 * Given an .hbc file, produce a runnable cross-platform application.
 *
 *  - "embed"  : copy the .hbc next to a pre-built runtime jar and write a
 *                small launcher.  The resulting directory is a portable app
 *                that can be zipped and shipped.
 *  - "image"  : call jpackage --type app-image (produces .app on mac,
 *                a directory with an .exe on Windows, a directory with a
 *                launcher script on Linux).
 *  - "exe"/"msi"/"dmg"/"deb"/"rpm" : the equivalent jpackage installer type.
 *
 * If jpackage is not available, we transparently fall back to producing a
 * runnable .jar + a launch script.  The contract is always: a directory that
 * contains something the user can double-click.
 */
package com.hsharp.platform

import com.hsharp.compiler.HbcFile
import com.hsharp.compiler.HbcModule
import com.hsharp.runtime.HbcRunner
import java.io.File
import java.io.FileWriter
import java.io.PrintWriter

class Packager(
    val hbc: HbcFile,
    val source: File,
    val outDir: File,
    val appName: String,
    val target: String,         // mac | win | linux
    val entryName: String?,     // optional entry module override
    val icon: String?,          // optional icon path
    val bundleType: String,     // image | exe | msi | dmg | deb | rpm | embed
    val appVersion: String = "1.0.0"
) {
    /** Pick the best entry module: explicit override, then "main", then the
     *  module that has the most non-setup code (i.e. has at least one
     *  CALL_FUNCTION or CALL_VALUE), falling back to the first module. */
    private fun pickEntry(): HbcModule {
        entryName?.let { hbc.modules[it]?.let { m -> return m } }
        hbc.modules["main"]?.let { return it }
        hbc.modules.values.firstOrNull { m ->
            m.instructions.any { it.first in listOf("CALL_FUNCTION", "CALL_VALUE", "CALL_NEW", "PRINT") }
        }?.let { return it }
        return hbc.modules.values.first()
    }

    fun packageAll() {
        outDir.deleteRecursively()
        outDir.mkdirs()

        val host = detectHost()
        val entry = pickEntry()
        println(">>> Packaging H# app: $appName (target=$target, type=$bundleType, host=$host)")
        println("    .hbc source: ${source.absolutePath}")
        println("    output dir : ${outDir.absolutePath}")
        println("    modules    : ${hbc.modules.size}, entry=${entry.name}")

        // 1) Always produce a "fat" directory layout that we can run from any
        //    host — useful for testing the cross-platform output.
        val embedDir = File(outDir, "$appName-app")
        copyEmbedLayout(embedDir, entry)
        println("    + portable runnable: ${embedDir.absolutePath}")

        // 2) On the matching host, try jpackage to produce a *true* platform
        //    bundle (not just a .jar inside a directory).
        if (host == target || target == "any") {
            tryJpackage(embedDir, entry)
        } else {
            println("    [skip jpackage: host=$host does not match target=$target]")
            println("    Copy the portable runnable to a $target machine and run:")
            println("        ${embedDir.absolutePath}/bin/$appName${if (host == "win") ".bat" else ""}")
        }
    }

    /* ------------------------------------------------------------------ */
    private fun copyEmbedLayout(dest: File, entry: HbcModule) {
        dest.mkdirs()
        File(dest, "hbc").apply { mkdirs() }
        File(dest, "bin").apply { mkdirs() }
        File(dest, "lib").apply { mkdirs() }
        // 1) the .hbc payload
        File(dest, "hbc/${source.name}").writeBytes(source.readBytes())
        // 2) the runtime jar (look in several well-known places, then in PATH)
        val runtimeJar: File? = locateRuntimeJar()
        if (runtimeJar != null) {
            runtimeJar.copyTo(File(dest, "lib/${runtimeJar.name}"), overwrite = true)
        }
        // 3) launch scripts
        writeLauncherScripts(dest, runtimeJar?.name)
        // 4) manifest / metadata
        FileWriter(File(dest, "app.json")).use { w ->
            w.write("""{
  "name": "${appName}",
  "hbc": "hbc/${source.name}",
  "hbcVersion": "${hbc.version}",
  "entryModule": "${entry.name}",
  "modules": [${hbc.modules.keys.joinToString(",") { "\"$it\"" }}],
  "target": "${target}",
  "compilerVersion": "${com.hsharp.compiler.CompilerVersion.VERSION}"
}""")
        }
    }

    private fun writeLauncherScripts(dest: File, runtimeJarName: String?) {
        val bin = File(dest, "bin")
        val hbcRel = "hbc/${source.name}"
        val jarLine = if (runtimeJarName != null) {
            "java -jar \"\$DIR/lib/$runtimeJarName\" \"\$DIR/$hbcRel\" \"\$@\""
        } else {
            "echo 'No runtime jar bundled. Build the compiler with ./scripts/build.sh first.' >&2; exit 1"
        }
        FileWriter(File(bin, appName)).use { w ->
            w.write("#!/bin/sh\n")
            w.write("# H# auto-generated launcher for $appName\n")
            w.write("set -e\n")
            w.write("DIR=\"\$(cd \"\$(dirname \"\$0\")/..\" && pwd)\"\n")
            w.write("if [ -z \"\$JAVA_HOME\" ] && ! command -v java >/dev/null 2>&1; then\n")
            w.write("  echo 'No java in PATH and JAVA_HOME not set' >&2; exit 1\n")
            w.write("fi\n")
            w.write(jarLine + "\n")
        }
        File(bin, appName).setExecutable(true)
        FileWriter(File(bin, "$appName.bat")).use { w ->
            w.write("@echo off\r\n")
            w.write("rem H# auto-generated launcher for $appName\r\n")
            w.write("setlocal\r\n")
            w.write("set DIR=%~dp0..\r\n")
            w.write(runtimeJarName?.let { "java -jar \"%DIR%\\lib\\$it\" \"%DIR%\\$hbcRel\" %*\r\n" }
                ?: "echo No runtime jar bundled. Build the compiler with build.sh first. & exit /b 1\r\n")
        }
    }

    private fun locateRuntimeJar(): File? {
        // 1) Adjacent to the running compiler jar (most common layout)
        val compilerHome = File(System.getProperty("java.class.path") ?: "")
            .takeIf { it.name.endsWith(".jar") }
            ?.parentFile
        if (compilerHome != null) {
            val sibling = File(compilerHome, "hsharp-runtime.jar")
            if (sibling.exists() && sibling.length() > 0) return sibling
            // 2) build/libs runtime jar
            val buildLibs = File(compilerHome, "build/libs/hsharp-runtime.jar")
            if (buildLibs.exists() && buildLibs.length() > 0) return buildLibs
        }
        // 3) CWD-relative candidates (in case compiler was run from project root)
        val candidates = listOf(
            "build/libs/hsharp-runtime.jar",
            "../build/libs/hsharp-runtime.jar",
            "hsharp-kotlin-compiler/build/libs/hsharp-runtime.jar",
            "/usr/local/share/hsharp/hsharp-runtime.jar",
            (System.getProperty("user.home") ?: "") + "/.hsharp/hsharp-runtime.jar"
        )
        for (c in candidates) {
            val f = File(c)
            if (f.exists() && f.length() > 0) return f
        }
        // 4) Embed fallback: extract `lib/hsharp-runtime.jar` from inside the
        //    compiler jar to a temp dir. This is the path VS Code users hit
        //    because the compiler jar is shipped inside the extension's `lib/`
        //    dir but the runtime jar is only embedded as a resource.
        return extractEmbeddedRuntimeJar()
    }

    /** Extract `lib/hsharp-runtime.jar` (a resource bundled inside this
     *  compiler jar) to a stable location under user.home. The first
     *  call writes the file; subsequent calls return the cached file. */
    private fun extractEmbeddedRuntimeJar(): File? {
        val home = System.getProperty("user.home") ?: return null
        val cacheDir = File(home, ".hsharp/cache")
        val cached = File(cacheDir, "hsharp-runtime.jar")
        if (cached.exists() && cached.length() > 0) return cached
        try {
            val cl = Thread.currentThread().contextClassLoader ?: return null
            val resourcePath = "lib/hsharp-runtime.jar"
            val resource = cl.getResource(resourcePath) ?: return null
            cacheDir.mkdirs()
            resource.openStream().use { input ->
                cached.outputStream().use { output -> input.copyTo(output) }
            }
            return if (cached.length() > 0) cached else null
        } catch (e: Throwable) {
            System.err.println("    [warn] failed to extract embedded runtime jar: ${e.message}")
            return null
        }
    }

    private fun tryJpackage(embedDir: File, entry: HbcModule) {
        val jp = locateOnPath("jpackage")
        if (jp == null) {
            println("    [info] jpackage not available; portable runnable produced instead.")
            println("           To produce a real .app/.exe/.msi/.deb, install JDK 16+ and rerun.")
            return
        }
        val jpkgType = jpackageType()
        val work = File(outDir, "jpackage-input")
        work.deleteRecursively(); work.mkdirs()
        File(embedDir, "lib").copyRecursively(File(work, "lib"), overwrite = true)
        File(embedDir, "hbc").copyRecursively(File(work, "hbc"), overwrite = true)
        File(embedDir, "app.json").copyTo(File(work, "app.json"), overwrite = true)
        // Embed the .hbc as a classpath resource inside the runtime jar
        embedHbcIntoRuntimeJar(work)

        val cmd = mutableListOf(
            jp,
            "--type", jpkgType,
            "--name", appName,
            "--input", work.absolutePath,
            "--main-jar", "lib/hsharp-runtime.jar",
            "--main-class", "com.hsharp.runtime.HbcLauncher",
            "--dest", outDir.absolutePath,
            "--app-version", appVersion
        )
        if (icon != null) cmd.addAll(listOf("--icon", icon))
        println("    >>> jpackage: ${cmd.joinToString(" ")}")
        val proc = ProcessBuilder(cmd).redirectErrorStream(true).start()
        val out = proc.inputStream.bufferedReader().readText()
        val rc = proc.waitFor()
        if (rc == 0) {
            println("    jpackage OK:\n$out")
        } else {
            println("    jpackage FAILED (rc=$rc):\n$out")
            println("    Falling back to portable runnable: ${embedDir.absolutePath}")
        }
    }

    /** Inject `hbc/<source.name>` and a copy named `app.hbc` into the
     *  runtime jar as classpath resources. */
    private fun embedHbcIntoRuntimeJar(work: File) {
        val libDir = File(work, "lib")
        val src = libDir.listFiles { f -> f.name.startsWith("hsharp-runtime") }?.firstOrNull()
            ?: return
        val hbcName = source.name
        val srcPath = src.absolutePath
        // Add the original name
        runJar("uf", srcPath, "-C", work.absolutePath, "hbc/$hbcName")
        // Also add a renamed copy under app.hbc
        val appHbc = File(work, "app.hbc")
        if (!appHbc.exists()) {
            File(work, "hbc/$hbcName").copyTo(appHbc, overwrite = true)
        }
        runJar("uf", srcPath, "-C", work.absolutePath, "app.hbc")
    }

    private fun runJar(vararg args: String): Boolean {
        return try {
            val cmd = mutableListOf("jar")
            cmd.addAll(args)
            val p = ProcessBuilder(cmd).redirectErrorStream(true).start()
            p.waitFor()
            true
        } catch (e: Throwable) {
            System.err.println("    [warn] jar command failed: ${e.message}")
            false
        }
    }

    private fun jpackageType(): String = when (bundleType.lowercase()) {
        "image" -> "app-image"
        "exe", "msi", "dmg", "deb", "rpm" -> bundleType
        "embed", "portable" -> "app-image"
        else -> "app-image"
    }

    private fun locateOnPath(name: String): String? {
        val path = System.getenv("PATH") ?: return null
        val sep = if (System.getProperty("os.name").lowercase().contains("win")) ";" else ":"
        for (dir in path.split(sep)) {
            val cand = File(dir, name)
            if (cand.exists() && cand.canExecute()) return cand.absolutePath
            if (System.getProperty("os.name").lowercase().contains("win")) {
                val cand2 = File(dir, "$name.exe")
                if (cand2.exists() && cand2.canExecute()) return cand2.absolutePath
            }
        }
        return null
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
}
