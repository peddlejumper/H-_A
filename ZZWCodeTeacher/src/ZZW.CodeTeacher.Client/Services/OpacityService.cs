using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using Avalonia;
using Avalonia.Media;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// 控件透明度设置(5 组:主面板/卡片、工具栏、内陷区、编辑器、边框)。
/// 默认值取 Light 主题原始 alpha 比例,用户调整前视觉无变化。
/// </summary>
public sealed record OpacitySettings(
    [property: JsonPropertyName("surface")] double Surface = 0.87,
    [property: JsonPropertyName("toolbar")] double Toolbar = 0.92,
    [property: JsonPropertyName("inset")] double Inset = 0.75,
    [property: JsonPropertyName("editor")] double Editor = 0.75,
    [property: JsonPropertyName("border")] double Border = 0.6);

/// <summary>
/// 控件透明度服务:运行时修改 4 个 Glass Brush 的 Color alpha 通道,
/// 所有引用同 Brush 的控件立即刷新(因 SolidColorBrush.Color 是 AvaloniaProperty)。
/// 主题切换时 ThemeDictionaries 会重置 Brush.Color 为新主题值,本服务订阅
/// <see cref="ThemeService.ThemeChanged"/> 在切换后重新应用用户 alpha(保留新主题 RGB)。
/// 持久化到 %AppData%/ZZWCodeTeacher/opacity.json。
/// </summary>
public sealed class OpacityService
{
    private static readonly string SettingsDir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ZZWCodeTeacher");
    private static readonly string SettingsPath = Path.Combine(SettingsDir, "opacity.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    /// <summary>默认设置(Light 主题原始 alpha 比例)</summary>
    public static OpacitySettings Defaults => new();

    public OpacitySettings Current { get; private set; }

    public event EventHandler? Changed;

    public OpacityService(ThemeService themeService)
    {
        Current = Load();
        // 主题切换后 ThemeDictionaries 会重置 Brush.Color,需重新应用用户 alpha
        themeService.ThemeChanged += (_, _) => Apply();
    }

    /// <summary>保存并立即应用到界面</summary>
    public void Save(OpacitySettings settings)
    {
        Current = settings;
        Persist(Current);
        Apply();
        Changed?.Invoke(this, EventArgs.Empty);
    }

    /// <summary>
    /// 应用当前透明度到 4 个 Glass Brush。
    /// 获取 Brush 当前 Color(主题切换后已是新主题的 RGB+alpha),提取 RGB,
    /// 用用户 alpha 重新构造 Color。Hover 跟随 Surface(避免 hover 时透明度跳变)。
    /// </summary>
    public void Apply()
    {
        if (Avalonia.Application.Current is null) return;
        ApplyBrush("GlassSurfaceBrush", Current.Surface);
        ApplyBrush("GlassSurfaceHoverBrush", Current.Surface);
        ApplyBrush("GlassToolbarBrush", Current.Toolbar);
        ApplyBrush("GlassInsetBrush", Current.Inset);
        ApplyBrush("GlassEditorBrush", Current.Editor);
        ApplyBrush("GlassBorderBrush", Current.Border);
    }

    private static void ApplyBrush(string key, double opacity)
    {
        var app = Avalonia.Application.Current;
        if (app is null) return;
        // Glass Brush 定义在 MergedDictionaries(MaterialGlassResources.axaml)主体中;
        // ResourceDictionary.TryGetResource 会递归查 MergedDictionaries。theme 传 null 用当前主题。
        if (!app.Resources.TryGetResource(key, null, out var resource) || resource is not SolidColorBrush brush) return;
        var c = brush.Color;
        var alpha = (byte)Math.Round(255 * Math.Clamp(opacity, 0.0, 1.0));
        brush.Color = new Color(alpha, c.R, c.G, c.B);
    }

    private static OpacitySettings Load()
    {
        try
        {
            if (File.Exists(SettingsPath))
            {
                var json = File.ReadAllText(SettingsPath);
                var file = JsonSerializer.Deserialize<OpacitySettings>(json, JsonOpts);
                if (file is not null)
                    return new OpacitySettings(
                        Math.Clamp(file.Surface, 0.0, 1.0),
                        Math.Clamp(file.Toolbar, 0.0, 1.0),
                        Math.Clamp(file.Inset, 0.0, 1.0),
                        Math.Clamp(file.Editor, 0.0, 1.0),
                        Math.Clamp(file.Border, 0.0, 1.0));
            }
        }
        catch
        {
            // 文件损坏则用默认值
        }
        return new OpacitySettings();
    }

    private static void Persist(OpacitySettings settings)
    {
        try
        {
            Directory.CreateDirectory(SettingsDir);
            var json = JsonSerializer.Serialize(settings, JsonOpts);
            File.WriteAllText(SettingsPath, json);
        }
        catch
        {
            // 持久化失败不影响本次运行
        }
    }

    public static string GetSettingsPath() => SettingsPath;
}
