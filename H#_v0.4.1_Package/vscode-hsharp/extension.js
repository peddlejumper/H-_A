/**
 * H# Language Support — VS Code Extension (v0.4)
 *
 * Powered by the Kotlin H# compiler/VM. The Kotlin jars are bundled under
 * `lib/` and invoked with `java -jar` on demand.
 *
 * The Python compiler/lexer from HSharp_v0.4_Tests is still used for the
 * .hto → .hbc step (this is a development convenience — the Kotlin runtime
 * is the source of truth for language semantics). If you prefer to skip the
 * .hto step, just open a pre-built .hbc file and use "H#: Run via Kotlin VM".
 *
 * Features:
 *  - Syntax highlighting (TextMate grammar)
 *  - Code snippets
 *  - Real-time diagnostics (lightweight syntax checks)
 *  - Completion (keywords, Kotlin-VM builtins, H# types)
 *  - Hover information
 *  - Signature help
 *  - Document formatting
 *  - Document symbols
 *  - Run/Compile/Package commands (all via Kotlin compiler jars)
 */

const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const cp = require('child_process');

// ── Helpers ────────────────────────────────────────────────

/** Escape a string for shell usage (single-quote on POSIX, double on Windows). */
function shellEscape(s) {
    if (process.platform === 'win32') {
        return '"' + s.replace(/"/g, '\\"') + '"';
    }
    return "'" + s.replace(/'/g, "'\\''") + "'";
}

/** Find an executable on PATH. */
function which(name) {
    const cmd = process.platform === 'win32' ? 'where' : 'which';
    try {
        const r = cp.spawnSync(cmd, [name], { encoding: 'utf8' });
        if (r.status === 0) return r.stdout.split(/\r?\n/)[0].trim();
    } catch (_) {}
    return null;
}

// ─── H# data ───────────────────────────────────────────────

const KEYWORDS = [
    'let', 'fn', 'return', 'while', 'if', 'else', 'for', 'in',
    'print', 'import', 'class', 'new', 'extends', 'private', 'static',
    'interface', 'implements', 'union', 'super', 'is', 'as',
    'module', 'concept', 'coro', 'asm', 'ptr', 'auto',
    'true', 'false', 'nullptr', 'and', 'or', 'not',
    'continue', 'break', 'try', 'catch', 'throw', 'del',
    'public', 'region', 'region_interface',
];

/**
 * Builtins exposed by the Kotlin VM (HNativeBridge). Names match the entries
 * in HNativeBridge.kt, with both the `net_*` and short aliases accepted.
 */
const BUILTINS = {
    // Core
    'len': 'Returns the length of a string, list, or dict.',
    'push': 'Appends an item to a list (mutates).',
    'pop': 'Removes and returns the last item of a list.',
    'str': 'Converts a value to its string representation.',
    'int': 'Converts a value to an integer.',
    'float': 'Converts a value to a float.',
    'type': 'Returns the type name of a value (lowercase).',
    'typeof': 'Returns the type name of a value (lowercase).',
    'abs': 'Returns the absolute value of a number.',
    'min': 'Returns the minimum value from a list.',
    'max': 'Returns the maximum value from a list.',
    'range': 'Generates a list of integers [0,n) or [a,b).',
    'input': 'Reads a line from stdin, after printing the prompt.',
    'print': 'Prints a value to stdout.',

    // Dict
    'keys': 'Returns the keys of a dict as a list.',
    'values': 'Returns the values of a dict as a list.',
    'items': 'Returns [[key,value], ...] pairs of a dict.',
    'has_key': 'Returns true if the dict has the given key.',

    // String
    'substring': 'substring(s, start, len) — slice by offset and length.',
    'ord': 'Returns the code point of the first character of a string.',
    'chr': 'Returns the single-character string for the given code point.',

    // FS / IO
    'read_file': 'Reads the entire contents of a file (utf-8).',
    'write_file': 'Writes content to a file (utf-8, overwrites).',
    'fs_exists': 'Returns true if the path exists.',
    'fs_is_file': 'Returns true if the path is a regular file.',
    'fs_is_dir': 'Returns true if the path is a directory.',
    'fs_mkdir': 'Creates a directory.',
    'fs_remove': 'Removes a file or directory.',
    'fs_list_dir': 'Lists a directory (returns a list of names).',
    'fs_get_cwd': 'Returns the current working directory.',
    'fs_chdir': 'Changes the current working directory.',
    'fs_join_path': 'Joins path components with the platform separator.',
    'fs_get_ext': 'Returns the file extension (including the leading dot).',
    'fs_get_basename': 'Returns the final path component.',
    'fs_get_dirname': 'Returns the directory portion of a path.',
    'io_append_file': 'Appends content to a file.',
    'io_read_lines': 'Returns the lines of a file as a list.',
    'io_write_lines': 'Writes a list of strings to a file (one per line).',

    // Net (Kotlin preferred + C-VM alias)
    'net_http_get': 'HTTP GET. Returns {status, body}.',
    'net_http_post': 'HTTP POST. Returns {status, body}.',
    'http_get': 'HTTP GET (alias of net_http_get).',
    'http_post': 'HTTP POST (alias of net_http_post).',
    'net_url_parse': 'Parses a URL into {scheme,host,port,path,query,fragment}.',
    'net_url_build': 'Rebuilds a URL string from its parts.',
    'url_parse': 'Alias of net_url_parse.',
    'url_build': 'Alias of net_url_build.',
    'net_tcp_connect': 'TCP connect, returns a numeric handle.',
    'net_tcp_send': 'Send bytes on a TCP handle.',
    'net_tcp_recv': 'Receive bytes on a TCP handle.',
    'net_tcp_close': 'Close a TCP handle.',
    'tcp_connect': 'Alias of net_tcp_connect.',
    'tcp_send': 'Alias of net_tcp_send.',
    'tcp_recv': 'Alias of net_tcp_recv.',
    'tcp_close': 'Alias of net_tcp_close.',
    'net_udp_create': 'Create a UDP socket, returns a numeric handle.',
    'net_udp_send': 'Send a UDP datagram.',
    'net_udp_recv': 'Receive a UDP datagram.',
    'udp_create': 'Alias of net_udp_create.',
    'udp_send': 'Alias of net_udp_send.',
    'udp_recv': 'Alias of net_udp_recv.',
    'net_base64_encode': 'Base64-encode a string.',
    'net_base64_decode': 'Base64-decode a string.',
    'base64_encode': 'Alias of net_base64_encode.',
    'base64_decode': 'Alias of net_base64_decode.',
    'net_json_stringify': 'Serialize a value to JSON text.',
    'net_json_parse': 'Parse JSON text into a value.',
    'json_stringify': 'Alias of net_json_stringify.',
    'json_parse': 'Alias of net_json_parse.',

    // DB
    'db_connect': 'Open a SQLite database, returns a handle.',
    'db_close': 'Close a database handle.',
    'db_execute': 'Execute a non-query SQL statement.',
    'db_query': 'Run a SELECT and return rows as a list of lists.',
    'db_query_one': 'Run a SELECT and return the first row.',
    'db_begin_transaction': 'Begin a transaction.',
    'db_commit': 'Commit a transaction.',
    'db_rollback': 'Roll back a transaction.',
    'db_create_table': 'Create a table from a column-spec list.',
    'db_drop_table': 'Drop a table.',
    'db_get_tables': 'List all tables in the database.',
    'db_get_table_info': 'Return column info for a table.',

    // HTable
    'htable_create': 'Create a hash-table handle.',
    'htable_set': 'Set a key in a hash-table.',
    'htable_get': 'Get a key from a hash-table.',
    'htable_has': 'Return true if a key is present.',
    'htable_delete': 'Delete a key from a hash-table.',
    'htable_size': 'Return the number of entries.',
    'htable_keys': 'Return all keys as a list.',
    'htable_values': 'Return all values as a list.',

    // DZZW (parallel computation — Kotlin VM exposes them as stubs)
    'dzzw_spawn': 'Spawns a parallel task, returns a future handle.',
    'dzzw_await': 'Blocks on a future handle, returns its result.',
    'dzzw_parallel_map': 'Applies a function to every item in a list in parallel.',
    'dzzw_worker_count': 'Returns the number of DZZW workers.',
    'dzzw_pending_count': 'Returns the number of pending tasks.',
    'dzzw_channel_create': 'Creates a channel, returns a handle.',
    'dzzw_channel_send': 'Sends a value into a channel.',
    'dzzw_channel_recv': 'Receives a value from a channel (blocking).',
    'dzzw_channel_free': 'Frees a channel handle.',
    'dzzw_mutex_create': 'Creates a mutex, returns a handle.',
    'dzzw_mutex_lock': 'Acquires a mutex (blocks).',
    'dzzw_mutex_unlock': 'Releases a mutex.',
    'dzzw_mutex_free': 'Frees a mutex handle.',
    'dzzw_try_await': 'Non-blocking await; returns true if ready.',
    'dzzw_await_any': 'Returns the first completed result from a list of handles.',
    'dzzw_await_all': 'Awaits every handle in a list.',
    'dzzw_total_completed': 'Returns the total number of completed tasks.',
    'dzzw_total_submitted': 'Returns the total number of submitted tasks.',
    'dzzw_dump_stats': 'Returns a JSON string with runtime statistics.',
};

/**
 * Signature hints — kept in sync with HNativeBridge.kt arity (the .name
 * and parameter arity must match; types are documentary).
 */
const BUILTIN_SIGNATURES = {
    'len': ['(value: any) -> int'],
    'str': ['(value: any) -> string'],
    'int': ['(value: any) -> int'],
    'float': ['(value: any) -> float'],
    'typeof': ['(value: any) -> string'],
    'print': ['(value: any) -> void'],
    'abs': ['(value: number) -> number'],
    'min': ['(values: list) -> number'],
    'max': ['(values: list) -> number'],
    'range': ['(end: int) -> list', '(start: int, end: int) -> list'],
    'input': ['(prompt: string) -> string'],
    'push': ['(list: list, item: any) -> void'],
    'pop': ['(list: list) -> any'],
    'keys': ['(dict: dict) -> list'],
    'values': ['(dict: dict) -> list'],
    'items': ['(dict: dict) -> list'],
    'has_key': ['(dict: dict, key: any) -> bool'],
    'substring': ['(s: string, start: int, len: int) -> string'],
    'ord': ['(ch: string) -> int'],
    'chr': ['(code: int) -> string'],
    'read_file': ['(path: string) -> string'],
    'write_file': ['(path: string, content: string) -> void'],
    'net_http_get': ['(url: string) -> {status:int, body:string}',
                     '(url: string, headers: dict) -> {status:int, body:string}'],
    'http_get': ['(url: string) -> {status:int, body:string}'],
    'net_http_post': ['(url: string, body: string) -> {status:int, body:string}'],
    'http_post': ['(url: string, body: string) -> {status:int, body:string}'],
    'net_tcp_connect': ['(host: string, port: int) -> int'],
    'tcp_connect': ['(host: string, port: int) -> int'],
    'net_tcp_send': ['(handle: int, data: string) -> void'],
    'tcp_send': ['(handle: int, data: string) -> void'],
    'net_tcp_recv': ['(handle: int, bufsize: int) -> string'],
    'tcp_recv': ['(handle: int, bufsize: int) -> string'],
    'net_tcp_close': ['(handle: int) -> void'],
    'tcp_close': ['(handle: int) -> void'],
    'net_udp_create': ['() -> int'],
    'udp_create': ['() -> int'],
    'net_udp_send': ['(handle: int, host: string, port: int, data: string) -> void'],
    'udp_send': ['(handle: int, host: string, port: int, data: string) -> void'],
    'net_udp_recv': ['(handle: int, bufsize: int) -> string'],
    'udp_recv': ['(handle: int, bufsize: int) -> string'],
    'net_base64_encode': ['(data: string) -> string'],
    'base64_encode': ['(data: string) -> string'],
    'net_base64_decode': ['(data: string) -> string'],
    'base64_decode': ['(data: string) -> string'],
    'net_json_stringify': ['(value: any) -> string'],
    'json_stringify': ['(value: any) -> string'],
    'net_json_parse': ['(text: string) -> any'],
    'json_parse': ['(text: string) -> any'],
    'db_connect': ['(path: string) -> int'],
    'db_query': ['(handle: int, sql: string) -> list'],
    'dzzw_spawn': ['(fn: function, args: list) -> int'],
    'dzzw_await': ['(handle: int) -> any'],
    'dzzw_parallel_map': ['(fn: function, items: list) -> list'],
    'dzzw_channel_create': ['() -> int'],
    'dzzw_mutex_create': ['() -> int'],
    'dzzw_mutex_lock': ['(handle: int) -> void'],
    'dzzw_mutex_unlock': ['(handle: int) -> void'],
};

const KEYWORD_DESCRIPTIONS = {
    'let': 'Declares a new variable with block scope.',
    'fn': 'Defines a function. All H# functions are implicitly curried.',
    'return': 'Returns a value from a function.',
    'while': 'Repeats a block while a condition is true.',
    'if': 'Conditional execution.',
    'else': 'Alternative branch for if.',
    'for': 'Iterates over an iterable.',
    'in': 'Used in for-in loops.',
    'class': 'Defines a class.',
    'union': 'Defines a union type (sum type).',
    'import': 'Imports a module by name (Python) or file path (.hbc/.hto).',
    'new': 'Instantiates a class.',
    'extends': 'Specifies a parent class.',
    'super': 'References the parent class (CALL_SUPER opcode).',
    'is': 'Type check operator (INSTANCEOF opcode).',
    'as': 'Type cast operator (CAST opcode).',
    'and': 'Logical AND (short-circuit).',
    'or': 'Logical OR (short-circuit).',
    'not': 'Logical NOT.',
    'true': 'Boolean true constant.',
    'false': 'Boolean false constant.',
    'nullptr': 'Null pointer / nil value.',
    'try': 'Begins a try-catch block.',
    'catch': 'Catches an exception.',
    'throw': 'Throws an exception (RAISE opcode).',
    'module': 'Defines a module namespace (MAKE_MODULE opcode).',
    'concept': 'Defines a concept (type class).',
    'coro': 'Defines a coroutine (is_coro flag on HFunction).',
    'asm': 'Inline assembly block (ASM opcode).',
    'ptr': 'Pointer type annotation.',
    'auto': 'Automatic type inference.',
    'private': 'Private access modifier (enforced by HVM STORE_ATTR/LOAD_ATTR).',
    'static': 'Static member modifier (stored under __static__ on the class).',
    'public': 'Public access modifier.',
    'interface': 'Defines an interface (compile-time only).',
    'implements': 'Specifies an interface implementation.',
    'continue': 'Skips to the next iteration of a loop.',
    'break': 'Exits the current loop (BREAK opcode scans for the next backward JUMP).',
    'del': 'Deletes a variable or attribute.',
};

// ─── Output channel ────────────────────────────────────────

let outChannel = null;
function getOut() {
    if (!outChannel) outChannel = vscode.window.createOutputChannel('H#');
    return outChannel;
}
function out(line) { getOut().appendLine(line); }

// ─── Locating the Kotlin toolchain ─────────────────────────

function resolveJar(configKey, fallbackName) {
    const cfg = vscode.workspace.getConfiguration('hsharp');
    const override = cfg.get(configKey, '');
    if (override && fs.existsSync(override)) return override;
    const bundled = path.join(__dirname, 'lib', fallbackName);
    if (fs.existsSync(bundled)) return bundled;
    return null;
}

function ensureJava() {
    const java = process.env['JAVA_HOME']
        ? path.join(process.env['JAVA_HOME'], 'bin', process.platform === 'win32' ? 'java.exe' : 'java')
        : which('java');
    if (!java || !fs.existsSync(java)) {
        vscode.window.showErrorMessage(
            'H#: Java runtime not found. Install JDK 11+ and set JAVA_HOME, or add `java` to PATH.',
            'Open Setup Guide'
        ).then(sel => {
            if (sel === 'Open Setup Guide') {
                vscode.env.openExternal(vscode.Uri.parse('https://github.com/peddlejumper/H-_A#setup'));
            }
        });
        return null;
    }
    return java;
}

function runJar(java, jar, args, opts = {}) {
    return new Promise(resolve => {
        const cmd = [java, '-jar', jar, ...args];
        out(`$ ${cmd.join(' ')}`);
        const proc = cp.spawn(cmd[0], cmd.slice(1), {
            cwd: opts.cwd,
            env: process.env,
        });
        let stdout = '', stderr = '';
        proc.stdout.on('data', d => { const s = d.toString(); stdout += s; out(s.replace(/\n$/, '')); });
        proc.stderr.on('data', d => { const s = d.toString(); stderr += s; out(s.replace(/\n$/, '')); });
        proc.on('error', err => { out(`process error: ${err.message}`); resolve({ code: -1, stdout, stderr }); });
        proc.on('close', code => resolve({ code, stdout, stderr }));
    });
}

// ─── Activation ────────────────────────────────────────────

function activate(context) {
    out('H# Language Support v0.4 activated (Kotlin H# compiler)');

    // ── Diagnostics ──
    const diagnosticCollection = vscode.languages.createDiagnosticCollection('hsharp');
    context.subscriptions.push(diagnosticCollection);

    function updateDiagnostics(document) {
        const config = vscode.workspace.getConfiguration('hsharp');
        if (!config.get('diagnostics.enabled', true)) return;

        const diagnostics = [];
        const text = document.getText();
        const lines = text.split('\n');

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmed = line.trim();
            if (trimmed.length === 0 || trimmed.startsWith('#')) continue;

            // Check for &&, ||, ! instead of and, or, not
            const logicalOps = trimmed.match(/(&&|\|\||(?<!!)!(?!=))/);
            if (logicalOps) {
                const suggestion = logicalOps[0] === '&&' ? 'and' :
                                   logicalOps[0] === '||' ? 'or' : 'not';
                const idx = line.indexOf(logicalOps[0]);
                diagnostics.push(new vscode.Diagnostic(
                    new vscode.Range(i, idx, i, idx + logicalOps[0].length),
                    `Use "${suggestion}" instead of "${logicalOps[0]}" in H#`,
                    vscode.DiagnosticSeverity.Warning
                ));
            }

            // Check for missing braces after control structures
            const controlMatch = trimmed.match(/^(if|else|while|for|fn\s+\w+\s*\([^)]*\))\s*[^{]/);
            if (controlMatch) {
                let nextLine = '';
                for (let j = i + 1; j < lines.length; j++) {
                    const nl = lines[j].trim();
                    if (nl.length > 0 && !nl.startsWith('#')) { nextLine = nl; break; }
                }
                if (nextLine && !nextLine.startsWith('{')) {
                    diagnostics.push(new vscode.Diagnostic(
                        new vscode.Range(i, 0, i, line.length),
                        `"${controlMatch[1]}" should be followed by an opening brace '{'`,
                        vscode.DiagnosticSeverity.Warning
                    ));
                }
            }
        }
        diagnosticCollection.set(document.uri, diagnostics);
    }

    vscode.workspace.onDidOpenTextDocument(updateDiagnostics);
    vscode.workspace.onDidChangeTextDocument(e => updateDiagnostics(e.document));
    vscode.workspace.onDidCloseTextDocument(doc => diagnosticCollection.delete(doc.uri));
    vscode.workspace.textDocuments.forEach(updateDiagnostics);

    // ── Completion Provider ──
    const completionProvider = vscode.languages.registerCompletionItemProvider('hsharp', {
        provideCompletionItems() {
            const items = [];
            for (const kw of KEYWORDS) {
                const item = new vscode.CompletionItem(kw, vscode.CompletionItemKind.Keyword);
                item.detail = 'H# keyword';
                if (KEYWORD_DESCRIPTIONS[kw]) {
                    item.documentation = new vscode.MarkdownString(KEYWORD_DESCRIPTIONS[kw]);
                }
                items.push(item);
            }
            for (const [name, desc] of Object.entries(BUILTINS)) {
                const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Function);
                item.detail = desc;
                items.push(item);
            }
            const snippets = [
                { label: 'fn', insertText: 'fn ${1:name}(${2:args}) {\n\t${0}\n}', detail: 'Function definition' },
                { label: 'if', insertText: 'if (${1:condition}) {\n\t${0}\n}', detail: 'If statement' },
                { label: 'ifelse', insertText: 'if (${1:condition}) {\n\t${2}\n} else {\n\t${0}\n}', detail: 'If-else statement' },
                { label: 'while', insertText: 'while (${1:condition}) {\n\t${0}\n}', detail: 'While loop' },
                { label: 'forin', insertText: 'for ${1:i} in ${2:iterable} {\n\t${0}\n}', detail: 'For-in loop' },
                { label: 'class', insertText: 'class ${1:Name} {\n\t${0}\n}', detail: 'Class definition' },
                { label: 'classext', insertText: 'class ${1:Name} extends ${2:Base} {\n\t${0}\n}', detail: 'Class with inheritance' },
                { label: 'union', insertText: 'union ${1:Name} { ${0:variants} }', detail: 'Union type definition' },
                { label: 'let', insertText: 'let ${1:name} = ${0:value};', detail: 'Variable declaration' },
                { label: 'main', insertText: 'fn main() {\n\t${0}\n}\n\nmain();', detail: 'Main function entry point' },
                { label: 'spawn', insertText: 'let h = dzzw_spawn(${1:fn}, [${2:args}]);\nlet result = dzzw_await(h);', detail: 'Spawn a parallel task and await its result' },
                { label: 'pmap', insertText: 'let results = dzzw_parallel_map(${1:fn}, ${2:items});', detail: 'Apply a function to every item in parallel' },
                { label: 'try', insertText: 'try {\n\t${1}\n} catch (${2:e}) {\n\t${0}\n}', detail: 'Try-catch block' },
            ];
            for (const s of snippets) {
                const item = new vscode.CompletionItem(s.label, vscode.CompletionItemKind.Snippet);
                item.insertText = new vscode.SnippetString(s.insertText);
                item.detail = s.detail;
                items.push(item);
            }
            return items;
        }
    }, '.', '(', ' ');
    context.subscriptions.push(completionProvider);

    // ── Hover Provider ──
    const hoverProvider = vscode.languages.registerHoverProvider('hsharp', {
        provideHover(document, position) {
            const wordRange = document.getWordRangeAtPosition(position);
            if (!wordRange) return null;
            const word = document.getText(wordRange);
            if (BUILTINS[word]) {
                const sigs = BUILTIN_SIGNATURES[word];
                const sigLine = sigs ? `\n\n*Signature:* \`${sigs[0]}\`` : '';
                return new vscode.Hover(
                    new vscode.MarkdownString(`### \`${word}\`\n\n${BUILTINS[word]}${sigLine}\n\n*Kotlin H# built-in*`)
                );
            }
            if (KEYWORD_DESCRIPTIONS[word]) {
                return new vscode.Hover(
                    new vscode.MarkdownString(`### \`${word}\`\n\n${KEYWORD_DESCRIPTIONS[word]}\n\n*H# keyword*`)
                );
            }
            return null;
        }
    });
    context.subscriptions.push(hoverProvider);

    // ── Signature Help Provider ──
    const signatureProvider = vscode.languages.registerSignatureHelpProvider('hsharp', {
        provideSignatureHelp(document, position) {
            const line = document.lineAt(position.line).text;
            const beforeCursor = line.substring(0, position.character);
            const match = beforeCursor.match(/(\w+)\s*\([^)]*$/);
            if (!match) return null;
            const funcName = match[1];
            const sigs = BUILTIN_SIGNATURES[funcName];
            if (!sigs) return null;
            const sigInfos = sigs.map(s => {
                const paramsPart = s.replace(/^\(|\)[^)]*$/g, '');
                const paramNames = paramsPart.split(',').map(p => p.trim()).filter(p => p.length > 0);
                const paramInfos = paramNames.map(p => {
                    const [name, type] = p.split(':').map(x => x.trim());
                    return new vscode.ParameterInformation(`${name}: ${type || 'any'}`);
                });
                return new vscode.SignatureInformation(s, undefined, ...paramInfos);
            });
            const help = new vscode.SignatureHelp();
            help.signatures = sigInfos;
            help.activeSignature = 0;
            help.activeParameter = 0;
            return help;
        },
    }, '(', ',');
    context.subscriptions.push(signatureProvider);

    // ── Document Symbols ──
    const symbolProvider = vscode.languages.registerDocumentSymbolProvider('hsharp', {
        provideDocumentSymbols(document) {
            const symbols = [];
            const text = document.getText();
            const patterns = [
                { regex: /^\s*fn\s+(\w+)\s*\([^)]*\)/gm, kind: vscode.SymbolKind.Function },
                { regex: /^\s*class\s+(\w+)/gm, kind: vscode.SymbolKind.Class },
                { regex: /^\s*union\s+(\w+)/gm, kind: vscode.SymbolKind.Enum },
                { regex: /^\s*interface\s+(\w+)/gm, kind: vscode.SymbolKind.Interface },
                { regex: /^\s*module\s+(\w+)/gm, kind: vscode.SymbolKind.Module },
            ];
            for (const { regex, kind } of patterns) {
                let m;
                while ((m = regex.exec(text)) !== null) {
                    const pos = document.positionAt(m.index);
                    const range = new vscode.Range(
                        pos,
                        new vscode.Position(pos.line, pos.character + m[0].length)
                    );
                    symbols.push(new vscode.DocumentSymbol(m[1], '', kind, range, range));
                }
            }
            return symbols;
        }
    });
    context.subscriptions.push(symbolProvider);

    // ── Formatter ──
    const formatter = vscode.languages.registerDocumentFormattingEditProvider('hsharp', {
        provideDocumentFormattingEdits(document) {
            const config = vscode.workspace.getConfiguration('hsharp');
            if (!config.get('format.enabled', true)) return [];
            const edits = [];
            for (let i = 0; i < document.lineCount; i++) {
                const line = document.lineAt(i);
                const text = line.text;
                if (text.trim().length === 0) continue;
                const trimmed = text.replace(/\s+$/, '');
                if (trimmed !== text) {
                    edits.push(vscode.TextEdit.replace(line.range, trimmed));
                }
            }
            return edits;
        }
    });
    context.subscriptions.push(formatter);

    // ── Definition Provider ──
    const definitionProvider = vscode.languages.registerDefinitionProvider('hsharp', {
        provideDefinition(document, position) {
            const wordRange = document.getWordRangeAtPosition(position);
            if (!wordRange) return null;
            const word = document.getText(wordRange);
            const text = document.getText();
            const patterns = [
                new RegExp(`\\bfn\\s+(${word})\\b`),
                new RegExp(`\\bclass\\s+(${word})\\b`),
                new RegExp(`\\bunion\\s+(${word})\\b`),
                new RegExp(`\\binterface\\s+(${word})\\b`),
            ];
            for (const regex of patterns) {
                const match = regex.exec(text);
                if (match) {
                    const pos = document.positionAt(match.index + match[0].indexOf(word));
                    return new vscode.Location(
                        document.uri,
                        new vscode.Range(pos, new vscode.Position(pos.line, pos.character + word.length))
                    );
                }
            }
            return null;
        }
    });
    context.subscriptions.push(definitionProvider);

    // ── Commands ──
    context.subscriptions.push(
        vscode.commands.registerCommand('hsharp.showInfo', () => {
            vscode.window.showInformationMessage(
                'H# v0.4 — Space-Oriented & Concept-Oriented Programming Language',
                'Open GitHub'
            ).then(sel => {
                if (sel === 'Open GitHub') {
                    vscode.env.openExternal(vscode.Uri.parse('https://github.com/peddlejumper/H-_A'));
                }
            });
        })
    );

    // hsharp.openOutput — show our output channel on demand
    context.subscriptions.push(
        vscode.commands.registerCommand('hsharp.openOutput', () => { getOut().show(); })
    );

    // ── Run: .hbc directly via Kotlin runtime
    async function runHbcFile(hbcPath) {
        const java = ensureJava(); if (!java) return;
        const runtime = resolveJar('hsharp.kotlinRuntime.jar', 'hsharp-runtime.jar');
        if (!runtime) {
            vscode.window.showErrorMessage('hsharp-runtime.jar not found. Configure hsharp.kotlinRuntime.jar in settings.');
            return;
        }
        const term = vscode.window.createTerminal('H# Run');
        term.show();
        term.sendText(`${shellEscape(java)} -jar ${shellEscape(runtime)} ${shellEscape(hbcPath)}`);
    }

    /**
     * Resolve the directory containing the bundled Python source files
     * (hsharp_compile.py + lexer/parser/compiler/tokens/h_ast.py).
     * Falls back to a temp dir we lazily populate from the extension dir.
     */
    let _pythonSrcDir = null;
    function getPythonSrcDir() {
        if (_pythonSrcDir) return _pythonSrcDir;
        // 1. Try the extension's own python/ dir (shipped inside the .vsix)
        const bundled = path.join(__dirname, 'python');
        if (fs.existsSync(path.join(bundled, 'hsharp_compile.py'))) {
            _pythonSrcDir = bundled;
            return _pythonSrcDir;
        }
        // 2. User override: hsharp.pythonSrcDir
        const cfg = vscode.workspace.getConfiguration('hsharp');
        const override = cfg.get('pythonSrcDir', '');
        if (override && fs.existsSync(path.join(override, 'hsharp_compile.py'))) {
            _pythonSrcDir = override;
            return _pythonSrcDir;
        }
        // 3. Last resort: extract bundled python/ to a temp dir. This
        //    should not normally happen, but makes the extension robust
        //    if someone relocates the .py files.
        const tmp = require('os').tmpdir();
        const dst = path.join(tmp, 'hsharp-vsix-python');
        if (!fs.existsSync(path.join(dst, 'hsharp_compile.py'))) {
            fs.mkdirSync(dst, { recursive: true });
            for (const f of ['hsharp_compile.py', 'lexer.py', 'parser.py', 'compiler.py', 'tokens.py', 'h_ast.py']) {
                const src = path.join(bundled, f);
                if (fs.existsSync(src)) fs.copyFileSync(src, path.join(dst, f));
            }
        }
        _pythonSrcDir = dst;
        return _pythonSrcDir;
    }

    /**
     * Compile a .hto file to a .hbc using the bundled Python compiler,
     * then optionally run the .hbc via the bundled Kotlin runtime.
     */
    async function compileAndRunHto(filePath) {
        const java = ensureJava(); if (!java) return false;
        const cfg = vscode.workspace.getConfiguration('hsharp');
        const py = cfg.get('pythonCompiler.path', 'python3');
        const srcDir = getPythonSrcDir();
        if (!fs.existsSync(srcDir) || !fs.existsSync(path.join(srcDir, 'hsharp_compile.py'))) {
            vscode.window.showErrorMessage(
                'H#: bundled Python compiler not found in extension. ' +
                'Please reinstall the extension or set hsharp.pythonSrcDir.'
            );
            return false;
        }
        const runtime = resolveJar('hsharp.kotlinRuntime.jar', 'hsharp-runtime.jar');
        if (!runtime) {
            vscode.window.showErrorMessage(
                'hsharp-runtime.jar not found. Configure hsharp.kotlinRuntime.jar in settings.'
            );
            return false;
        }
        const hbcPath = filePath.replace(/\.hto$/i, '.hbc');

        // Stage the .hbc next to the source so IMPORT_FILE works with
        // relative paths. If the source is not on disk (untitled doc), we
        // fall back to a tmp dir.
        let workDir = path.dirname(filePath);
        if (!fs.existsSync(filePath)) {
            const tmp = require('os').tmpdir();
            workDir = path.join(tmp, 'hsharp-untitled');
            fs.mkdirSync(workDir, { recursive: true });
            fs.copyFileSync(filePath, path.join(workDir, path.basename(filePath)));
            fs.writeFileSync(path.join(workDir, path.basename(hbcPath)), '');
        }

        const pyCmd = `${shellEscape(py)} -B hsharp_compile.py ` +
            `${shellEscape(filePath)} ${shellEscape(hbcPath)}`;
        const javaCmd = `${shellEscape(java)} -jar ${shellEscape(runtime)} ${shellEscape(hbcPath)}`;

        const term = vscode.window.createTerminal('H# Run');
        term.show();
        term.sendText(`cd ${shellEscape(srcDir)} && ${pyCmd} && cd ${shellEscape(workDir)} && ${javaCmd}`);
        return true;
    }

    // hsharp.runFile — supports both .hto (compile first then run) and .hbc
    context.subscriptions.push(
        vscode.commands.registerCommand('hsharp.runFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) { vscode.window.showErrorMessage('No active editor'); return; }
            const filePath = editor.document.uri.fsPath;
            const ext = path.extname(filePath).toLowerCase();

            if (ext === '.hbc') {
                await runHbcFile(filePath);
                return;
            }
            if (ext !== '.hto' && ext !== '.hsi') {
                vscode.window.showErrorMessage(`H#: unsupported extension '${ext}'. Use .hto or .hbc.`);
                return;
            }
            await compileAndRunHto(filePath);
        })
    );

    // hsharp.compileFile — .hto → .hbc via bundled Python compiler
    context.subscriptions.push(
        vscode.commands.registerCommand('hsharp.compileFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) { vscode.window.showErrorMessage('No active editor'); return; }
            const filePath = editor.document.uri.fsPath;
            const ext = path.extname(filePath).toLowerCase();
            if (ext !== '.hto' && ext !== '.hsi') {
                vscode.window.showErrorMessage('H# compile: open a .hto file first.');
                return;
            }
            const cfg = vscode.workspace.getConfiguration('hsharp');
            const py = cfg.get('pythonCompiler.path', 'python3');
            const srcDir = getPythonSrcDir();
            if (!fs.existsSync(srcDir) || !fs.existsSync(path.join(srcDir, 'hsharp_compile.py'))) {
                vscode.window.showErrorMessage(
                    'H#: bundled Python compiler not found. Set hsharp.pythonSrcDir in settings.'
                );
                return;
            }
            const hbcPath = filePath.replace(/\.hto$/i, '.hbc');
            const term = vscode.window.createTerminal('H# Compile');
            term.show();
            term.sendText(`cd ${shellEscape(srcDir)} && ${shellEscape(py)} -B hsharp_compile.py ${shellEscape(filePath)} ${shellEscape(hbcPath)}`);
        })
    );

    // hsharp.packageApp — produce .app/.exe via Kotlin compiler
    context.subscriptions.push(
        vscode.commands.registerCommand('hsharp.packageApp', async () => {
            let hbcPath = null;
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const p = editor.document.uri.fsPath;
                if (p.toLowerCase().endsWith('.hbc')) hbcPath = p;
                else if (p.toLowerCase().endsWith('.hto')) hbcPath = p.replace(/\.hto$/i, '.hbc');
            }
            if (!hbcPath) {
                hbcPath = await vscode.window.showInputBox({
                    prompt: 'Path to the .hbc file to package',
                    placeHolder: 'e.g. /Users/me/myapp/app.hbc',
                });
            }
            if (!hbcPath) return;
            if (!fs.existsSync(hbcPath)) {
                vscode.window.showErrorMessage(`H#: .hbc not found at ${hbcPath}`);
                return;
            }
            const java = ensureJava(); if (!java) return;
            const compiler = resolveJar('hsharp.kotlinCompiler.jar', 'hsharp-kotlin-compiler.jar');
            if (!compiler) {
                vscode.window.showErrorMessage('hsharp-kotlin-compiler.jar not found. Configure hsharp.kotlinCompiler.jar in settings.');
                return;
            }
            const cfg = vscode.workspace.getConfiguration('hsharp');
            const target = cfg.get('package.target', 'mac');
            const ptype = cfg.get('package.type', 'image');
            const name = path.basename(hbcPath, path.extname(hbcPath));
            const outDir = path.join(path.dirname(hbcPath), 'dist');

            getOut().show();
            out(`Packaging ${name} (target=${target}, type=${ptype}) → ${outDir}`);
            const res = await runJar(java, compiler,
                ['compile', hbcPath, '-o', outDir, '--name', name,
                 '--target', target, '--type', ptype, '--app-version', '1.0.0'],
                { cwd: path.dirname(hbcPath) });

            if (res.code === 0) {
                const appPath = path.join(outDir, `${name}.app`);
                if (fs.existsSync(appPath)) {
                    vscode.window.showInformationMessage(
                        `H#: packaged ${name}.app into ${outDir}`,
                        'Reveal in Finder'
                    ).then(sel => {
                        if (sel === 'Reveal in Finder') {
                            vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(appPath));
                        }
                    });
                } else {
                    vscode.window.showInformationMessage(`H#: package built (portable runnable) at ${outDir}/${name}-app`);
                }
            } else {
                vscode.window.showErrorMessage(`H#: package failed (rc=${res.code}). See H# output channel.`);
            }
        })
    );

    // ── Status Bar ──
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '$(code) H# (Kotlin)';
    statusBarItem.tooltip = 'H# Language Support v0.4 — powered by the Kotlin H# compiler/VM';
    statusBarItem.command = 'hsharp.showInfo';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
}

function deactivate() {}

module.exports = { activate, deactivate };
