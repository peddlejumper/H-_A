/*
 * HbcRunner
 * ---------
 * Stand-alone application entry: reads an .hbc file, sets up the runtime,
 * pre-loads all library modules into the global namespace, and runs the
 * designated entry module.
 *
 * This is what gets shipped inside the cross-platform .app / .exe bundle.
 */
package com.hsharp.runtime

import com.hsharp.compiler.HbcFile
import com.hsharp.compiler.HbcModule
import com.hsharp.compiler.HbcReader
import java.io.File

class HbcRunner(private val hbcFile: File) {

    fun run(): HValue {
        val hbc = HbcReader().read(hbcFile)
        return runOn(hbc, hbc.mainModule().name)
    }

    fun runOn(hbc: HbcFile, entryName: String): HValue {
        val vm = HVM(hbc, entryName, hbcDir = hbcFile.parentFile?.absoluteFile?.let {
            if (it.path.isEmpty()) File(".") else it
        })
        // Pre-load every non-entry module's STORE_NAME definitions into globals
        for ((mname, mod) in hbc.modules) {
            if (mname == entryName) continue
            loadModuleExports(vm, mod)
        }
        return vm.run()
    }

    /**
     * Walk the top-level instructions of a library module and copy any
     * STORE_NAME result into the VM's globals. Only a tiny subset of opcodes
     * is honoured because real library modules are short setup scripts.
     */
    private fun loadModuleExports(vm: HVM, mod: HbcModule) {
        val frame = HFrame(null, mod.consts, mod.instructions, mutableMapOf())
        var pc = 0
        while (pc < mod.instructions.size) {
            val (op, arg) = mod.instructions[pc]
            pc++
            when (op) {
                "HALT", "RETURN_VALUE" -> break
                "LOAD_CONST" -> frame.stack.addLast(frame.consts[(arg as Number).toInt()])
                "LOAD_NAME" -> {
                    val name = arg as String
                    frame.stack.addLast(
                        frame.env[name]
                            ?: vm.globals[name]
                            ?: HNativeBridge.builtins[name]
                            ?: HNull
                    )
                }
                "STORE_NAME" -> frame.env[arg as String] = frame.stack.removeLast()
                "MAKE_LIST" -> {
                    val n = (arg as Number).toInt()
                    val items = ArrayList<HValue>(n)
                    repeat(n) { items.add(0, frame.stack.removeLast()) }
                    frame.stack.addLast(HList(items))
                }
                "MAKE_DICT" -> {
                    val n = (arg as Number).toInt()
                    val d = LinkedHashMap<String, HValue>()
                    repeat(n) {
                        val v = frame.stack.removeLast()
                        val k = frame.stack.removeLast()
                        d[coerceKey(k)] = v
                    }
                    frame.stack.addLast(HDict(d))
                }
                "POP_TOP" -> frame.stack.removeLast()
                "PRINT" -> println(frame.stack.removeLast().toDisplayString())
                else -> { /* unknown op in setup — skip */ }
            }
        }
        for ((k, v) in frame.env) vm.globals.putIfAbsent(k, v)
    }

    private fun coerceKey(v: HValue): String = when (v) {
        is HString -> v.value
        is HNumber -> v.toDisplayString()
        is HBool -> if (v.value) "true" else "false"
        is HNull -> "null"
        else -> v.toDisplayString()
    }
}
