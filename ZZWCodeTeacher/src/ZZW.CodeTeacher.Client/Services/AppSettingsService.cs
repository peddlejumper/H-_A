using System.Text.Json;
using System.Text.Json.Serialization;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>应用级本地设置:API 地址/HTTPS/语言运行环境。存到 %AppData%/ZZWCodeTeacher/app_settings.json。</summary>
public sealed class AppSettingsService
{
    private static readonly string SettingsDir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ZZWCodeTeacher");
    private static readonly string SettingsPath = Path.Combine(SettingsDir, "app_settings.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    private static readonly string[] s_windowsExeExtensions = { ".exe", ".bat", ".cmd", "" };
    private static readonly string[] s_unixExtensions = { "" };

    public AppSettings Current { get; private set; }

    public event EventHandler<AppSettings>? Changed;

    public AppSettingsService()
    {
        Current = Load();
    }

    public void Save(AppSettings settings)
    {
        Current = settings with
        {
            ApiBaseUrl = NormalizeApiBase(settings.ApiBaseUrl, settings.UseHttps)
        };
        Persist(Current);
        Changed?.Invoke(this, Current);
    }

    public string GetRuntimePath(SupportedLanguage language)
    {
        return Current.RuntimePaths.TryGetValue(language.ToString(), out var path) ? path : "";
    }

    /// <summary>编辑器字号(默认 13,范围 10~22)</summary>
    public int GetEditorFontSize() => Current.EditorFontSize;

    /// <summary>编辑器 Tab 宽度(默认 4,范围 2~8)</summary>
    public int GetEditorTabWidth() => Current.EditorTabWidth;

    /// <summary>默认编程语言(新建代码时默认选中)</summary>
    public SupportedLanguage GetDefaultLanguage() =>
        Enum.IsDefined<SupportedLanguage>((SupportedLanguage)Current.DefaultLanguage)
            ? (SupportedLanguage)Current.DefaultLanguage
            : SupportedLanguage.Python;

    /// <summary>提交失败时是否自动让 AI 解释错误</summary>
    public bool GetAutoAiExplain() => Current.AutoAiExplain;

    public static string GetSettingsPath() => SettingsPath;

    /// <summary>
    /// 自动检测系统 PATH 中已安装的各语言运行环境。
    /// 遍历 <see cref="SupportedLanguage"/> 全部 15 种语言的默认命令名,
    /// 在 PATH 各目录中查找可执行文件,返回找到的绝对路径字典(未找到则值为空字符串)。
    /// </summary>
    public static async Task<Dictionary<SupportedLanguage, string>> DetectAllRuntimeAsync(CancellationToken ct = default)
    {
        return await Task.Run(() =>
        {
            var result = new Dictionary<SupportedLanguage, string>();
            var defaults = AppSettings.Default.RuntimePaths;
            var pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
            // 跨平台 PATH 分隔符:Windows 用 ';',Unix 用 ':'
            var separator = OperatingSystem.IsWindows() ? ';' : ':';
            var dirs = pathEnv.Split(separator, StringSplitOptions.RemoveEmptyEntries);
            // Windows 上可执行文件通常带 .exe/.bat/.cmd 后缀
            var extensions = OperatingSystem.IsWindows()
                ? s_windowsExeExtensions
                : s_unixExtensions;

            foreach (SupportedLanguage lang in Enum.GetValues<SupportedLanguage>())
            {
                ct.ThrowIfCancellationRequested();

                var cmd = defaults.TryGetValue(lang.ToString(), out var c) ? c : "";
                var found = "";

                if (!string.IsNullOrWhiteSpace(cmd))
                {
                    if (Path.IsPathRooted(cmd))
                    {
                        // 用户已配置绝对路径,直接校验存在性
                        found = File.Exists(cmd) ? cmd : "";
                    }
                    else
                    {
                        // 在 PATH 各目录中查找 cmd 或 cmd+扩展名
                        foreach (var dir in dirs)
                        {
                            if (string.IsNullOrWhiteSpace(dir)) continue;
                            foreach (var ext in extensions)
                            {
                                var full = Path.Combine(dir, cmd + ext);
                                if (File.Exists(full))
                                {
                                    found = full;
                                    break;
                                }
                            }
                            if (!string.IsNullOrEmpty(found)) break;
                        }
                    }
                }

                result[lang] = found;
            }
            return result;
        }, ct);
    }

    public static string NormalizeApiBase(string? value, bool useHttps)
    {
        var trimmed = string.IsNullOrWhiteSpace(value) ? "localhost:5000" : value.Trim();
        if (!trimmed.StartsWith("http://", StringComparison.OrdinalIgnoreCase)
            && !trimmed.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            trimmed = (useHttps ? "https://" : "http://") + trimmed;
        }

        if (useHttps && trimmed.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
            trimmed = "https://" + trimmed["http://".Length..];
        if (!useHttps && trimmed.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            trimmed = "http://" + trimmed["https://".Length..];

        return trimmed.TrimEnd('/');
    }

    private static AppSettings Load()
    {
        try
        {
            if (File.Exists(SettingsPath))
            {
                var json = File.ReadAllText(SettingsPath);
                var file = JsonSerializer.Deserialize<AppSettings>(json, JsonOpts);
                if (file is not null)
                    return file with { ApiBaseUrl = NormalizeApiBase(file.ApiBaseUrl, file.UseHttps) };
            }
        }
        catch
        {
            // 设置文件损坏时回落默认值。
        }

        return AppSettings.Default;
    }

    private static void Persist(AppSettings settings)
    {
        try
        {
            Directory.CreateDirectory(SettingsDir);
            var json = JsonSerializer.Serialize(settings, JsonOpts);
            File.WriteAllText(SettingsPath, json);
        }
        catch
        {
            // 持久化失败不影响本次运行。
        }
    }
}

public sealed record AppSettings(
    [property: JsonPropertyName("apiBaseUrl")] string ApiBaseUrl,
    [property: JsonPropertyName("useHttps")] bool UseHttps,
    [property: JsonPropertyName("runtimePaths")] Dictionary<string, string> RuntimePaths,
    [property: JsonPropertyName("editorFontSize")] int EditorFontSize = 13,
    [property: JsonPropertyName("editorTabWidth")] int EditorTabWidth = 4,
    [property: JsonPropertyName("defaultLanguage")] int DefaultLanguage = 0,
    [property: JsonPropertyName("autoAiExplain")] bool AutoAiExplain = true)
{
    public static AppSettings Default => new(
        "http://127.0.0.1:5050",
        false,
        new Dictionary<string, string>
        {
            [SupportedLanguage.Python.ToString()] = "python3",
            [SupportedLanguage.JavaScript.ToString()] = "node",
            [SupportedLanguage.TypeScript.ToString()] = "ts-node",
            [SupportedLanguage.Java.ToString()] = "java",
            [SupportedLanguage.C.ToString()] = "clang",
            [SupportedLanguage.Cpp.ToString()] = "clang++",
            [SupportedLanguage.CSharp.ToString()] = "dotnet",
            [SupportedLanguage.Go.ToString()] = "go",
            [SupportedLanguage.Rust.ToString()] = "rustc",
            [SupportedLanguage.Ruby.ToString()] = "ruby",
            [SupportedLanguage.PHP.ToString()] = "php",
            [SupportedLanguage.Swift.ToString()] = "swift",
            [SupportedLanguage.Kotlin.ToString()] = "kotlinc",
            [SupportedLanguage.Scala.ToString()] = "scala",
            [SupportedLanguage.HSharp.ToString()] = "hsharp"
        });
}
