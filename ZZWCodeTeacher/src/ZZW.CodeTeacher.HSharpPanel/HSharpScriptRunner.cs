#pragma warning disable CA1848, CA1873
namespace ZZW.CodeTeacher.HSharpPanel;

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using ZZW.CodeTeacher.Application.Interfaces;

/// <summary>
/// H# 脚本执行器 —— 通过启动 Python 解释器运行 H# 脚本。
/// H# 脚本通过 http_* host 函数与 .NET 后端通信。
/// </summary>
public sealed class HSharpScriptRunner(IConfiguration config, ILogger<HSharpScriptRunner> logger)
    : IHSharpScriptRunner
{
    public async Task<string> RunAsync(string scriptPath,
        IReadOnlyDictionary<string, string>? args = null, CancellationToken ct = default)
    {
        var interpreterPath = config["HSharp:InterpreterPath"] ?? "python3";
        var interpreterArgs = config["HSharp:InterpreterArgs"] ?? "hsharp.py";
        var workDir = config["HSharp:WorkingDirectory"] ?? Directory.GetCurrentDirectory();

        // 将参数作为环境变量传给 H# 脚本
        var env = new Dictionary<string, string?>
        {
            ["HSHARP_API_BASE"] = config["HSharp:ApiBase"] ?? "http://localhost:5000",
            ["HSHARP_SCRIPT_ARGS"] = args is null ? "" :
                string.Join(";", args.Select(kv => $"{kv.Key}={kv.Value}"))
        };

        var psi = new ProcessStartInfo
        {
            FileName = interpreterPath,
            Arguments = $"{interpreterArgs} {scriptPath}",
            WorkingDirectory = workDir,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        foreach (var (k, v) in env) psi.Environment[k] = v;

        logger.LogInformation("执行 H# 脚本：{Script}", scriptPath);

        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException("无法启动 H# 解释器");

        var stdoutTask = proc.StandardOutput.ReadToEndAsync(ct);
        var stderrTask = proc.StandardError.ReadToEndAsync(ct);
        await proc.WaitForExitAsync(ct);

        var stdout = await stdoutTask;
        var stderr = await stderrTask;

        if (proc.ExitCode != 0)
        {
            logger.LogError("H# 脚本执行失败（退出码 {Code}）：{Error}", proc.ExitCode, stderr);
            throw new InvalidOperationException($"H# 脚本执行失败：{stderr}");
        }

        return stdout;
    }

    public async Task<T?> RunJsonAsync<T>(string scriptPath,
        IReadOnlyDictionary<string, string>? args = null, CancellationToken ct = default)
    {
        var output = await RunAsync(scriptPath, args, ct);
        try
        {
            return JsonSerializer.Deserialize<T>(output);
        }
        catch (JsonException ex)
        {
            logger.LogError(ex, "H# 脚本输出无法反序列化为 {Type}", typeof(T).Name);
            return default;
        }
    }
}
