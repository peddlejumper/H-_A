using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using Avalonia;
using Avalonia.Styling;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>应用主题(浅色/深色)</summary>
public enum AppTheme
{
    Light,
    Dark
}

/// <summary>
/// 主题服务:管理浅色/深色切换,持久化到本地 theme.json。
/// 切换时设置 <see cref="Avalonia.Application.RequestedThemeVariant"/>,Avalonia FluentTheme 与
/// Application.Resources 中 ThemeDictionaries 色板会自动跟随。
/// 持久化模式参考 <see cref="AiSettingsStore"/>:%AppData%/ZZWCodeTeacher/theme.json。
/// </summary>
public sealed class ThemeService
{
    private static readonly string SettingsDir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ZZWCodeTeacher");
    private static readonly string SettingsPath = Path.Combine(SettingsDir, "theme.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    private AppTheme _current;

    /// <summary>当前主题</summary>
    public AppTheme CurrentTheme => _current;

    /// <summary>当前主题的中文名(供 UI 显示)</summary>
    public string CurrentThemeName => _current == AppTheme.Light ? "浅色" : "深色";

    /// <summary>主题变更事件(VM 监听以刷新按钮文案等)</summary>
    public event EventHandler<AppTheme>? ThemeChanged;

    public ThemeService()
    {
        _current = Load();
        ApplyToApplication();
    }

    /// <summary>在浅色/深色之间切换并持久化</summary>
    public Task ToggleAsync()
    {
        var next = _current == AppTheme.Light ? AppTheme.Dark : AppTheme.Light;
        return SetAsync(next);
    }

    /// <summary>设置为指定主题并持久化</summary>
    public Task SetAsync(AppTheme theme)
    {
        if (_current == theme) return Task.CompletedTask;
        _current = theme;
        ApplyToApplication();
        Persist(theme);
        ThemeChanged?.Invoke(this, _current);
        return Task.CompletedTask;
    }

    private static void ApplyToApplication(AppTheme theme)
    {
        // 完整限定 Avalonia.Application,避免与 ZZW.CodeTeacher.Application 命名空间歧义
        if (Avalonia.Application.Current is null) return;
        Avalonia.Application.Current.RequestedThemeVariant =
            theme == AppTheme.Dark ? ThemeVariant.Dark : ThemeVariant.Light;
    }

    private void ApplyToApplication() => ApplyToApplication(_current);

    private static AppTheme Load()
    {
        try
        {
            if (File.Exists(SettingsPath))
            {
                var json = File.ReadAllText(SettingsPath);
                var doc = JsonSerializer.Deserialize<ThemeFile>(json, JsonOpts);
                if (doc is not null && Enum.IsDefined(doc.Theme))
                    return doc.Theme;
            }
        }
        catch
        {
            // 文件损坏则用默认(浅色)
        }
        return AppTheme.Light;
    }

    private static void Persist(AppTheme theme)
    {
        try
        {
            Directory.CreateDirectory(SettingsDir);
            var json = JsonSerializer.Serialize(new ThemeFile(theme), JsonOpts);
            File.WriteAllText(SettingsPath, json);
        }
        catch
        {
            // 持久化失败不影响内存使用
        }
    }

    /// <summary>获取配置文件路径(供 UI 显示)</summary>
    public static string GetSettingsPath() => SettingsPath;

    private sealed record ThemeFile(
        [property: JsonPropertyName("theme")] AppTheme Theme);
}
