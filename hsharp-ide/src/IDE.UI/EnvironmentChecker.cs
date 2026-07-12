using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace IDE.UI
{
    public class EnvironmentCheckResult
    {
        public bool HasPython { get; set; }
        public bool HasPip { get; set; }
        public bool PyQt5Installed { get; set; }
        public bool HSharpPyFound { get; set; }
        public string? PythonExecutable { get; set; }
    }

    public static class EnvironmentChecker
    {
        public static async Task<EnvironmentCheckResult> CheckAsync()
        {
            var r = new EnvironmentCheckResult();

            // Determine python executable
            string? env = Environment.GetEnvironmentVariable("HSHARP_PYTHON");
            string[] candidates;
            if (!string.IsNullOrEmpty(env)) candidates = new[] { env, "python3", "python" };
            else candidates = new[] { "python3", "python" };

            foreach (var c in candidates)
            {
                if (string.IsNullOrEmpty(c)) continue;
                var (code, outp, err) = await RunProcessAsync(c, "--version", 5000);
                if (code == 0)
                {
                    r.HasPython = true;
                    r.PythonExecutable = c;
                    break;
                }
            }

            if (r.HasPython && !string.IsNullOrEmpty(r.PythonExecutable))
            {
                var (codePip, outpPip, errPip) = await RunProcessAsync(r.PythonExecutable, "-m pip --version", 5000);
                r.HasPip = codePip == 0;

                // check PyQt5 import
                var (codeQt, outQt, errQt) = await RunProcessAsync(r.PythonExecutable, "-c \"import PyQt5; print('ok')\"", 5000);
                r.PyQt5Installed = codeQt == 0;
            }

            r.HSharpPyFound = FindScript("hsharp.py") != null;

            return r;
        }

        public static string? FindScript(string name)
        {
            // If an explicit compiler is set via env or config, prefer it
            try
            {
                var envComp = Environment.GetEnvironmentVariable("HSHARP_COMPILER");
                if (!string.IsNullOrEmpty(envComp) && File.Exists(envComp))
                {
                    var bn = Path.GetFileName(envComp);
                    if (string.Equals(bn, name, StringComparison.OrdinalIgnoreCase) || name.Equals("hsharp.py", StringComparison.OrdinalIgnoreCase))
                        return Path.GetFullPath(envComp);
                }
                var cfgComp = LauncherConfig.GetSelectedCompilerPath();
                if (!string.IsNullOrEmpty(cfgComp) && File.Exists(cfgComp))
                {
                    var bn2 = Path.GetFileName(cfgComp);
                    if (string.Equals(bn2, name, StringComparison.OrdinalIgnoreCase) || name.Equals("hsharp.py", StringComparison.OrdinalIgnoreCase))
                        return Path.GetFullPath(cfgComp);
                }
            }
            catch { }

            // If an explicit package directory is set (from .hps), prefer it.
            var pkgDir = Environment.GetEnvironmentVariable("HSHARP_PKG_DIR");
            if (!string.IsNullOrEmpty(pkgDir))
            {
                try
                {
                    var candidatePkg = Path.Combine(pkgDir, name);
                    if (File.Exists(candidatePkg)) return Path.GetFullPath(candidatePkg);
                }
                catch { }
            }

            var dir = Directory.GetCurrentDirectory();
            // 1) Search upward (parent chain) first - keeps previous behavior
            for (int i = 0; i < 12; i++)
            {
                var candidate = Path.Combine(dir, name);
                if (File.Exists(candidate)) return Path.GetFullPath(candidate);
                dir = Path.GetDirectoryName(dir) ?? string.Empty;
                if (string.IsNullOrEmpty(dir)) break;
            }

            // 2) Fallback: do a bounded recursive search downwards from current directory
            //    Skip large or irrelevant folders to avoid long scans.
            try
            {
                var start = Directory.GetCurrentDirectory();
                var toVisit = new System.Collections.Generic.Stack<string>();
                toVisit.Push(start);
                int dirsVisited = 0;
                const int MaxDirs = 2000; // safety limit
                var skipNames = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase) { 
                    ".git", "node_modules", "bin", "obj", ".vs", "dist", "build", "out" };

                while (toVisit.Count > 0 && dirsVisited < MaxDirs)
                {
                    var d = toVisit.Pop();
                    dirsVisited++;
                    try
                    {
                        // check files in this directory
                        var files = Directory.GetFiles(d, name);
                        if (files != null && files.Length > 0) return Path.GetFullPath(files[0]);

                        // enqueue subdirectories
                        foreach (var sd in Directory.GetDirectories(d))
                        {
                            try
                            {
                                var dn = Path.GetFileName(sd);
                                if (skipNames.Contains(dn)) continue;
                                toVisit.Push(sd);
                            }
                            catch { }
                        }
                    }
                    catch { }
                }
            }
            catch { }

            return null;
        }

        public static async Task<bool> HasQoderAsync()
        {
            var cmd = Environment.GetEnvironmentVariable("QODER_CMD");
            var url = Environment.GetEnvironmentVariable("QODER_CN_URL");
            if (!string.IsNullOrEmpty(cmd))
            {
                var (code, outp, err) = await RunProcessAsync(cmd, "--version", 3000);
                if (code == 0) return true;
                // if starting the command fails, still consider CLI present only if command exists on PATH
            }
            // if a remote URL is configured, consider qoder available via network
            if (!string.IsNullOrEmpty(url)) return true;
            // lastly, probe default 'qoder' on PATH
            var (c2, o2, e2) = await RunProcessAsync("qoder", "--version", 3000);
            return c2 == 0;
        }

        public static async Task<(bool ok, string output)> CompileWithQoderAsync(string filePath)
        {
            if (!File.Exists(filePath)) return (false, "文件不存在: " + filePath);

            // Prefer local CLI if available
            var cmdEnv = Environment.GetEnvironmentVariable("QODER_CMD");
            string[] cliCandidates;
            if (!string.IsNullOrEmpty(cmdEnv)) cliCandidates = new[] { cmdEnv, "qoder" };
            else cliCandidates = new[] { "qoder" };

            foreach (var cmd in cliCandidates)
            {
                try
                {
                    var (c1, o1, e1) = await RunProcessAsync(cmd, $"compile \"{filePath}\"", 0);
                    if (c1 == 0) return (true, (o1 ?? string.Empty) + (e1 ?? string.Empty));

                    var (c2, o2, e2) = await RunProcessAsync(cmd, $"\"{filePath}\"", 0);
                    if (c2 == 0) return (true, (o2 ?? string.Empty) + (e2 ?? string.Empty));

                    var (c3, o3, e3) = await RunProcessAsync(cmd, $"run \"{filePath}\"", 0);
                    if (c3 == 0) return (true, (o3 ?? string.Empty) + (e3 ?? string.Empty));
                }
                catch
                {
                    // ignore and try next
                }
            }

            // Try remote qoder CN endpoint if configured
            var url = Environment.GetEnvironmentVariable("QODER_CN_URL");
            if (!string.IsNullOrEmpty(url))
            {
                try
                {
                    using var client = new HttpClient();
                    var payload = new { filename = Path.GetFileName(filePath), code = File.ReadAllText(filePath) };
                    var json = JsonSerializer.Serialize(payload);
                    var content = new StringContent(json, Encoding.UTF8, "application/json");
                    var resp = await client.PostAsync(url, content);
                    var respBody = await resp.Content.ReadAsStringAsync();
                    if (resp.IsSuccessStatusCode)
                        return (true, respBody);
                    else
                        return (false, $"远程 qoder 返回 {resp.StatusCode}: {respBody}");
                }
                catch (Exception ex)
                {
                    return (false, "远程 qoder 请求失败: " + ex.Message);
                }
            }

            return (false, "未检测到本地 qoder 可执行程序，且未配置 QODER_CN_URL。");
        }

        public static async Task<bool> TryInstallPipPackageAsync(string pythonExe, string package)
        {
            var (code, outp, err) = await RunProcessAsync(pythonExe, $"-m pip install --user {package}", 0);
            return code == 0;
        }

        public static async Task<bool> TryEnsurePipAsync(string pythonExe)
        {
            var (c1, o1, e1) = await RunProcessAsync(pythonExe, "-m ensurepip --upgrade", 0);
            // try upgrading pip
            var (c2, o2, e2) = await RunProcessAsync(pythonExe, "-m pip install --upgrade pip --user", 0);
            return c1 == 0 || c2 == 0;
        }

        public static async Task<bool> TryInstallPythonWithBrewAsync()
        {
            // check brew
            var (cb, ob, eb) = await RunProcessAsync("brew", "--version", 4000);
            if (cb != 0) return false;
            var (ci, oi, ei) = await RunProcessAsync("brew", "install python", 0);
            return ci == 0;
        }

        private static async Task<(int exitCode, string stdout, string stderr)> RunProcessAsync(string fileName, string arguments, int timeoutMs)
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = fileName,
                    Arguments = arguments,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                using var p = new Process { StartInfo = psi };
                var sbOut = new StringBuilder();
                var sbErr = new StringBuilder();

                p.OutputDataReceived += (s, e) => { if (e.Data != null) sbOut.AppendLine(e.Data); };
                p.ErrorDataReceived += (s, e) => { if (e.Data != null) sbErr.AppendLine(e.Data); };

                if (!p.Start()) return (-1, string.Empty, "failed to start");
                p.BeginOutputReadLine();
                p.BeginErrorReadLine();

                if (timeoutMs > 0)
                {
                    var finished = await Task.Run(() => p.WaitForExit(timeoutMs));
                    if (!finished)
                    {
                        try { p.Kill(true); } catch { }
                        return (-2, sbOut.ToString(), sbErr.ToString());
                    }
                }
                else
                {
                    await p.WaitForExitAsync();
                }

                return (p.ExitCode, sbOut.ToString(), sbErr.ToString());
            }
            catch (Exception ex)
            {
                return (-1, string.Empty, ex.Message);
            }
        }
    }
}
