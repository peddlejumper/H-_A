namespace ZZW.CodeTeacher.Infrastructure.Judging;

using System.Diagnostics;
using System.Globalization;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using ZZW.CodeTeacher.Application.Interfaces;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.ValueObjects;

/// <summary>
/// 进程隔离 + 资源限制的多语言代码评测器。
///
/// 设计要点:
///  - 每次评测在独立临时目录中进行,完成后清理
///  - 子进程通过 stdin 接收测试输入,stdout 产出实际输出
///  - 时间限制:单用例超时 = max(TimeLimitMs * 2, 5000ms)
///  - 内存限制:运行期轮询 Process.WorkingSet64 / PeakWorkingSet64(物理内存,
///    非 RSS,但桌面开发期跨平台够用),超过 MemoryLimitKb 即 Kill 并标记 MLE
///  - 编译型语言先编译,失败返回 CompileError
///  - H# 走 IHSharpScriptRunner(若注入);其余走本类的进程模型
///  - 并发限流:静态 SemaphoreSlim 限制最多 MaxConcurrentJudges 个并发评测,排队等待不拒绝
///
/// 安全性:开发期单机够用;生产环境建议替换为 Docker 沙箱实现。
/// </summary>
public sealed class ProcessIsolatedCodeJudgeRunner : ICodeJudgeRunner
{
    /// <summary>最大并发评测数(防并发爆机)。如需调整可改为读取配置。</summary>
    private const int MaxConcurrentJudges = 2;

    /// <summary>跨实例(Scoped)共享的并发闸门:同时只允许 MaxConcurrentJudges 个评测进入。</summary>
    private static readonly SemaphoreSlim _judgeSemaphore = new(MaxConcurrentJudges, MaxConcurrentJudges);

    private readonly ILogger<ProcessIsolatedCodeJudgeRunner> _logger;
    private readonly IHSharpScriptRunner? _hsharpRunner;

    public ProcessIsolatedCodeJudgeRunner(ILogger<ProcessIsolatedCodeJudgeRunner> logger,
        IHSharpScriptRunner? hsharpRunner = null)
    {
        _logger = logger;
        _hsharpRunner = hsharpRunner;
    }

    public bool IsLanguageAvailable(SupportedLanguage language)
        => ResolveRuntime(language) is not null;

    public IReadOnlyList<SupportedLanguage> GetAvailableLanguages()
    {
        var list = new List<SupportedLanguage>();
        foreach (SupportedLanguage lang in Enum.GetValues<SupportedLanguage>())
        {
            if (IsLanguageAvailable(lang)) list.Add(lang);
        }
        return list;
    }

    public async Task<(bool Success, string? Error)> CompileAsync(
        SupportedLanguage language, string code, CancellationToken ct = default)
    {
        if (!language.IsCompiled()) return (true, null);

        var workDir = CreateWorkDir();
        try
        {
            var srcPath = Path.Combine(workDir, "main" + language.FileExtension());
            await File.WriteAllTextAsync(srcPath, code, ct);

            return language switch
            {
                SupportedLanguage.Java => await RunCompileAsync(workDir, "javac", "main.java", ct),
                SupportedLanguage.C => await RunCompileAsync(workDir, "cc", "-O2 -o main main.c", ct),
                SupportedLanguage.Cpp => await RunCompileAsync(workDir, "c++", "-O2 -std=c++20 -o main main.cpp", ct),
                SupportedLanguage.CSharp => await RunCompileAsync(workDir, "dotnet", "script publish main.cs --output .", ct),
                SupportedLanguage.Go => await RunCompileAsync(workDir, "go", "build -o main main.go", ct),
                SupportedLanguage.Rust => await RunCompileAsync(workDir, "rustc", "-O main.rs", ct),
                SupportedLanguage.Swift => await RunCompileAsync(workDir, "swiftc", "-O main.swift", ct),
                SupportedLanguage.Kotlin => await RunCompileAsync(workDir, "kotlinc", "main.kt -include-runtime -d main.jar", ct),
                SupportedLanguage.Scala => await RunCompileAsync(workDir, "scalac", "main.scala", ct),
                SupportedLanguage.TypeScript => await RunCompileAsync(workDir, "tsc", "main.ts", ct),
                _ => (true, null)
            };
        }
        finally
        {
            TryCleanup(workDir);
        }
    }

    public async Task<JudgeReport> JudgeAsync(
        SupportedLanguage language, string code,
        IReadOnlyList<TestCase> testCases,
        int timeLimitMs, int memoryLimitKb,
        CheckerType checkerType = CheckerType.Exact,
        CancellationToken ct = default)
    {
        if (testCases.Count == 0)
        {
            return new JudgeReport(0, 0, 0, 0, []);
        }

        // 评测队列:限制并发评测数,队列满时排队等待(不拒绝),防并发爆机
        await _judgeSemaphore.WaitAsync(ct);
        try
        {
            // H# 走独立 runner(如果可用)
            if (language == SupportedLanguage.HSharp && _hsharpRunner is not null)
            {
                return await JudgeHSharpAsync(code, testCases, timeLimitMs, checkerType, ct);
            }

            var workDir = CreateWorkDir();
            try
            {
                // 写源码并编译
                var srcPath = Path.Combine(workDir, "main" + language.FileExtension());
                await File.WriteAllTextAsync(srcPath, code, ct);

                if (language.IsCompiled())
                {
                    var (ok, err) = await CompileAsync(language, code, ct);
                    if (!ok)
                    {
                        // 编译失败:所有用例都算失败
                        var failResults = testCases.Select((tc, i) => TestCaseResult.Fail(
                            i + 1, 0, 0, tc.ExpectedOutput, "", "CompileError: " + err)).ToList();
                        return new JudgeReport(testCases.Count, 0, 0, 0, failResults);
                    }
                    // 重新在工作目录中编译(CompileAsync 已在自己的临时目录里编译过,这里再编一次以保证 workDir 有产物)
                    // 为简化:直接在 workDir 中编译
                    await CompileInDirAsync(language, workDir, ct);
                }

                var results = new List<TestCaseResult>();
                long totalElapsed = 0;
                long maxMemoryBytes = 0; // 跨用例峰值(字节)
                int passed = 0;
                var memLimitBytes = (long)memoryLimitKb * 1024;

                foreach (var tc in testCases)
                {
                    var (psi, _) = BuildProcessSpec(language, workDir, timeLimitMs);
                    psi.WorkingDirectory = workDir;

                    using var proc = new Process { StartInfo = psi, EnableRaisingEvents = true };
                    var stdoutB = new StringBuilder();
                    var stderrB = new StringBuilder();
                    proc.OutputDataReceived += (_, e) => { if (e.Data is not null) stdoutB.AppendLine(e.Data); };
                    proc.ErrorDataReceived += (_, e) => { if (e.Data is not null) stderrB.AppendLine(e.Data); };

                    var sw = Stopwatch.StartNew();
                    proc.Start();
                    if (!string.IsNullOrEmpty(tc.Input))
                    {
                        await proc.StandardInput.WriteLineAsync(tc.Input);
                        await proc.StandardInput.FlushAsync(ct);
                    }
                    proc.StandardInput.Close();
                    proc.BeginOutputReadLine();
                    proc.BeginErrorReadLine();

                    // 单用例超时:timeLimitMs * 2 (允许少量误差)
                    var caseTimeout = Math.Max(timeLimitMs * 2, 5000);
                    // 轮询采集内存 + 超时/超内存强制终止
                    // 说明:WorkingSet64 为当前物理内存(非 RSS),PeakWorkingSet64 为进程峰值;
                    //       跨平台(macOS/Linux/Windows)均可用,桌面开发期精度够用。
                    var mle = false;
                    var tle = false;
                    var caseMaxMem = 0L;
                    while (!proc.WaitForExit(PollIntervalMs))
                    {
                        var mem = ReadProcessMemory(proc);
                        if (mem > caseMaxMem) caseMaxMem = mem;
                        if (memLimitBytes > 0 && mem > memLimitBytes)
                        {
                            try { proc.Kill(entireProcessTree: true); } catch { /* ignore */ }
                            mle = true;
                            break;
                        }
                        if (sw.ElapsedMilliseconds > caseTimeout)
                        {
                            try { proc.Kill(entireProcessTree: true); } catch { /* ignore */ }
                            tle = true;
                            break;
                        }
                    }
                    // 确保异步输出缓冲刷完 & 取最终峰值
                    try { proc.WaitForExit(); } catch { /* ignore */ }
                    var finalPeak = ReadProcessMemory(proc);
                    if (finalPeak > caseMaxMem) caseMaxMem = finalPeak;
                    if (caseMaxMem > maxMemoryBytes) maxMemoryBytes = caseMaxMem;
                    sw.Stop();

                    var memKb = caseMaxMem / 1024;

                    if (tle)
                    {
                        results.Add(TestCaseResult.Fail(
                            results.Count + 1, sw.ElapsedMilliseconds, memKb,
                            tc.ExpectedOutput ?? "", stdoutB.ToString(), "TLE: 超时"));
                        totalElapsed += sw.ElapsedMilliseconds;
                        continue;
                    }
                    if (mle)
                    {
                        results.Add(TestCaseResult.Fail(
                            results.Count + 1, sw.ElapsedMilliseconds, memKb,
                            tc.ExpectedOutput ?? "", stdoutB.ToString(),
                            $"MLE: 内存超限({memKb} KB > {memoryLimitKb} KB)"));
                        totalElapsed += sw.ElapsedMilliseconds;
                        continue;
                    }

                    var actual = stdoutB.ToString().TrimEnd('\n', '\r');
                    var expected = (tc.ExpectedOutput ?? "").TrimEnd('\n', '\r');
                    var passedThis = CompareOutput(expected, actual, checkerType);
                    if (passedThis) passed++;

                    var errStr = stderrB.Length > 0 ? stderrB.ToString() : null;
                    results.Add(passedThis
                        ? TestCaseResult.Pass(results.Count + 1, sw.ElapsedMilliseconds, memKb)
                        : TestCaseResult.Fail(results.Count + 1, sw.ElapsedMilliseconds, memKb,
                            expected, actual,
                            string.IsNullOrEmpty(errStr) ? null : "RuntimeError: " + errStr));

                    totalElapsed += sw.ElapsedMilliseconds;
                }

                return new JudgeReport(testCases.Count, passed, totalElapsed, maxMemoryBytes / 1024, results);
            }
            finally
            {
                TryCleanup(workDir);
            }
        }
        finally
        {
            _judgeSemaphore.Release();
        }
    }

    // ─────────────── 私有辅助 ───────────────

    private async Task<JudgeReport> JudgeHSharpAsync(string code,
        IReadOnlyList<TestCase> testCases, int timeLimitMs, CheckerType checkerType, CancellationToken ct)
    {
        // H# 走 IHSharpScriptRunner:每次执行传入 stdin,捕获 stdout
        // 简化:直接通过 H# 服务端口跑;此处给一个占位实现
        var results = new List<TestCaseResult>();
        int passed = 0;
        long total = 0;
        foreach (var tc in testCases)
        {
            var sw = Stopwatch.StartNew();
            try
            {
                var args = new Dictionary<string, string>
                {
                    ["code"] = code,
                    ["stdin"] = tc.Input ?? ""
                };
                var output = await _hsharpRunner!.RunAsync("run", args, ct);
                sw.Stop();
                var actual = (output ?? "").TrimEnd('\n', '\r');
                var expected = (tc.ExpectedOutput ?? "").TrimEnd('\n', '\r');
                var ok = CompareOutput(expected, actual, checkerType);
                if (ok) passed++;
                results.Add(ok
                    ? TestCaseResult.Pass(results.Count + 1, sw.ElapsedMilliseconds, 0)
                    : TestCaseResult.Fail(results.Count + 1, sw.ElapsedMilliseconds, 0, expected, actual));
                total += sw.ElapsedMilliseconds;
            }
            catch (Exception ex)
            {
                sw.Stop();
                results.Add(TestCaseResult.Fail(results.Count + 1, sw.ElapsedMilliseconds, 0,
                    tc.ExpectedOutput ?? "", "", "RuntimeError: " + ex.Message));
                total += sw.ElapsedMilliseconds;
            }
        }
        return new JudgeReport(testCases.Count, passed, total, 0, results);
    }

    private static async Task<(bool Success, string? Error)> RunCompileAsync(
        string workDir, string compiler, string args, CancellationToken ct)
    {
        var psi = new ProcessStartInfo
        {
            FileName = compiler,
            Arguments = args,
            WorkingDirectory = workDir,
            UseShellExecute = false,
            RedirectStandardError = true,
            RedirectStandardOutput = true,
            CreateNoWindow = true
        };
        // 关闭 shell 启动脚本,减少编译期副作用(不在此强制内存;运行期内存限制在 JudgeAsync 轮询中处理)
        if (OperatingSystem.IsLinux() || OperatingSystem.IsMacOS())
        {
            psi.Environment["BASH_ENV"] = "/dev/null";
        }

        try
        {
            using var proc = Process.Start(psi);
            if (proc is null) return (false, "无法启动编译器: " + compiler);
            await proc.WaitForExitAsync(ct);
            if (proc.ExitCode == 0) return (true, null);
            var err = await proc.StandardError.ReadToEndAsync(ct);
            return (false, string.IsNullOrWhiteSpace(err) ? $"编译器返回 {proc.ExitCode}" : err);
        }
        catch (Exception ex)
        {
            return (false, $"编译器调用失败({compiler}): {ex.Message}");
        }
    }

    private static async Task CompileInDirAsync(SupportedLanguage language, string workDir, CancellationToken ct)
    {
        var ext = language.FileExtension();
        var args = language switch
        {
            SupportedLanguage.Java => "main.java",
            SupportedLanguage.C => "-O2 -o main main.c",
            SupportedLanguage.Cpp => "-O2 -std=c++20 -o main main.cpp",
            SupportedLanguage.CSharp => null,
            SupportedLanguage.Go => "build -o main main.go",
            SupportedLanguage.Rust => "-O main.rs",
            SupportedLanguage.Swift => "-O main.swift",
            SupportedLanguage.Kotlin => "main.kt -include-runtime -d main.jar",
            SupportedLanguage.Scala => "main.scala",
            SupportedLanguage.TypeScript => "main.ts",
            _ => null
        };
        if (args is null) return;
        var compiler = language switch
        {
            SupportedLanguage.Java => "javac",
            SupportedLanguage.C => "cc",
            SupportedLanguage.Cpp => "c++",
            SupportedLanguage.Go => "go",
            SupportedLanguage.Rust => "rustc",
            SupportedLanguage.Swift => "swiftc",
            SupportedLanguage.Kotlin => "kotlinc",
            SupportedLanguage.Scala => "scalac",
            SupportedLanguage.TypeScript => "tsc",
            _ => ""
        };
        await RunCompileAsync(workDir, compiler, args, ct);
    }

    private static (ProcessStartInfo Psi, string? RedirectedStdin) BuildProcessSpec(
        SupportedLanguage language, string workDir, int timeLimitMs)
    {
        // 解释型直接执行源码;编译型运行已编译产物
        var (fileName, args) = language switch
        {
            SupportedLanguage.Python => ("python3", "main.py"),
            SupportedLanguage.JavaScript => ("node", "main.js"),
            SupportedLanguage.TypeScript => ("node", "main.js"),
            SupportedLanguage.Java => ("java", "main"),
            SupportedLanguage.C => ("./main", ""),
            SupportedLanguage.Cpp => ("./main", ""),
            SupportedLanguage.CSharp => ("dotnet", "main.dll"),
            SupportedLanguage.Go => ("./main", ""),
            SupportedLanguage.Rust => ("./main", ""),
            SupportedLanguage.Ruby => ("ruby", "main.rb"),
            SupportedLanguage.PHP => ("php", "main.php"),
            SupportedLanguage.Swift => ("./main", ""),
            SupportedLanguage.Kotlin => ("java", "-jar main.jar"),
            SupportedLanguage.Scala => ("scala", "main"),
            SupportedLanguage.HSharp => ("python3", "hsharp.py"),
            _ => ("echo", "unsupported")
        };

        var psi = new ProcessStartInfo
        {
            FileName = fileName,
            Arguments = args,
            WorkingDirectory = workDir,
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };

        return (psi, null);
    }

    /// <summary>内存/超时轮询间隔(ms):在精度与 CPU 开销间折中。</summary>
    private const int PollIntervalMs = 25;

    /// <summary>
    /// 读取子进程内存峰值(字节)。取 WorkingSet64(当前物理内存)与 PeakWorkingSet64(峰值)的较大值。
    /// 注意:WorkingSet64 是物理内存而非 RSS,但跨平台可用,桌面开发期精度够用。
    /// </summary>
    private static long ReadProcessMemory(Process proc)
    {
        try
        {
            proc.Refresh();
            return Math.Max(proc.WorkingSet64, proc.PeakWorkingSet64);
        }
        catch
        {
            return 0;
        }
    }

    /// <summary>
    /// 按 checkerType 比对期望输出与实际输出。
    ///  - Exact:行级精确匹配(先 TrimEnd 换行,再 Ordinal 比较),保持旧行为
    ///  - FloatTolerance:逐行 Trim,数字行用浮点容差,非数字行精确匹配;行数不同直接 WA
    ///  - SpecialJudge:外部 checker 脚本暂未实现,降级为 Exact(TODO)
    /// </summary>
    private static bool CompareOutput(string expected, string actual, CheckerType type)
    {
        // SpecialJudge:暂未接入外部 checker 脚本,降级为精确匹配
        // TODO: 接入 Problem 提供的 checker 脚本执行(独立沙箱)
        if (type == CheckerType.SpecialJudge)
        {
            type = CheckerType.Exact;
        }

        if (type == CheckerType.FloatTolerance)
        {
            return CompareFloatTolerance(expected, actual);
        }

        // Exact:保持与旧实现一致的 Ordinal 比较(仅 TrimEnd 换行)
        var e = (expected ?? "").TrimEnd('\n', '\r');
        var a = (actual ?? "").TrimEnd('\n', '\r');
        return string.Equals(a, e, StringComparison.Ordinal);
    }

    /// <summary>浮点容差比对:逐行 Trim,数字行用相对+绝对误差,非数字行精确匹配。</summary>
    private static bool CompareFloatTolerance(string expected, string actual)
    {
        var expLines = SplitLines(expected);
        var actLines = SplitLines(actual);
        if (expLines.Length != actLines.Length) return false;

        for (var i = 0; i < expLines.Length; i++)
        {
            var e = expLines[i].Trim();
            var a = actLines[i].Trim();

            // 两端都能解析为 double 才走浮点比对(避免把 "abc" 当数字)
            if (double.TryParse(e, NumberStyles.Float, CultureInfo.InvariantCulture, out var ev)
                && double.TryParse(a, NumberStyles.Float, CultureInfo.InvariantCulture, out var av))
            {
                // 相对误差:|a-b| <= 1e-6 * max(1, |expected|),兼顾大数与小数
                var tol = 1e-6 * Math.Max(1.0, Math.Abs(ev));
                if (Math.Abs(ev - av) > tol) return false;
            }
            else
            {
                if (!string.Equals(e, a, StringComparison.Ordinal)) return false;
            }
        }
        return true;
    }

    /// <summary>按 \r\n / \r / \n 切行,剔除尾部空行(容忍行尾换行差异)。</summary>
    private static string[] SplitLines(string s)
    {
        if (string.IsNullOrEmpty(s)) return Array.Empty<string>();
        return s.TrimEnd('\r', '\n')
                .Replace("\r\n", "\n").Replace("\r", "\n")
                .Split('\n');
    }

    private static string CreateWorkDir()
    {
        var path = Path.Combine(Path.GetTempPath(), "zzw-judge-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(path);
        return path;
    }

    private static void TryCleanup(string dir)
    {
        try
        {
            if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
        }
        catch { /* 评测沙箱清理失败不影响主流程 */ }
    }

    /// <summary>查找指定语言的运行时可执行文件(返回第一个找到的路径,或 null)</summary>
    private static string? ResolveRuntime(SupportedLanguage language)
    {
        var (exe, _) = language switch
        {
            SupportedLanguage.Python => ("python3", ""),
            SupportedLanguage.JavaScript => ("node", ""),
            SupportedLanguage.TypeScript => ("tsc", ""),
            SupportedLanguage.Java => ("javac", ""),
            SupportedLanguage.C => ("cc", ""),
            SupportedLanguage.Cpp => ("c++", ""),
            SupportedLanguage.CSharp => ("dotnet", ""),
            SupportedLanguage.Go => ("go", ""),
            SupportedLanguage.Rust => ("rustc", ""),
            SupportedLanguage.Ruby => ("ruby", ""),
            SupportedLanguage.PHP => ("php", ""),
            SupportedLanguage.Swift => ("swiftc", ""),
            SupportedLanguage.Kotlin => ("kotlinc", ""),
            SupportedLanguage.Scala => ("scalac", ""),
            SupportedLanguage.HSharp => ("python3", ""),
            _ => ("", "")
        };
        return FindInPath(exe);
    }

    /// <summary>在 PATH 中查找可执行文件</summary>
    private static string? FindInPath(string exe)
    {
        if (string.IsNullOrEmpty(exe)) return null;
        var pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
        var sep = OperatingSystem.IsWindows() ? ';' : ':';
        foreach (var dir in pathEnv.Split(sep, StringSplitOptions.RemoveEmptyEntries))
        {
            try
            {
                var full = Path.Combine(dir, exe);
                if (OperatingSystem.IsWindows() && !full.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                    full += ".exe";
                if (File.Exists(full)) return full;
            }
            catch { /* 路径访问异常,跳过 */ }
        }
        return null;
    }
}
