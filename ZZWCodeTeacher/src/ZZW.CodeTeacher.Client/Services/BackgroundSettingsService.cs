using System.Text.Json;
using System.Text.Json.Serialization;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>自定义背景图片本地配置。存到 %AppData%/ZZWCodeTeacher/background.json。</summary>
public sealed class BackgroundSettingsService
{
    private static readonly string SettingsDir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ZZWCodeTeacher");
    private static readonly string SettingsPath = Path.Combine(SettingsDir, "background.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    public string? ImagePath { get; private set; }
    public double Opacity { get; private set; } = 0.24;

    public event EventHandler<string?>? Changed;
    public event EventHandler<double>? OpacityChanged;

    public BackgroundSettingsService()
    {
        var file = Load();
        ImagePath = file.ImagePath;
        Opacity = file.Opacity;
    }

    public void SetImage(string path)
    {
        ImagePath = string.IsNullOrWhiteSpace(path) ? null : path;
        Persist(ImagePath, Opacity);
        Changed?.Invoke(this, ImagePath);
    }

    public void SetOpacity(double opacity)
    {
        Opacity = Math.Clamp(opacity, 0.0, 0.6);
        Persist(ImagePath, Opacity);
        OpacityChanged?.Invoke(this, Opacity);
    }

    public void Clear()
    {
        ImagePath = null;
        Persist(null, Opacity);
        Changed?.Invoke(this, null);
    }

    public static string GetSettingsPath() => SettingsPath;

    private static BackgroundFile Load()
    {
        try
        {
            if (!File.Exists(SettingsPath)) return new BackgroundFile(null, 0.24);
            var json = File.ReadAllText(SettingsPath);
            var file = JsonSerializer.Deserialize<BackgroundFile>(json, JsonOpts);
            if (file is not null)
            {
                return file with
                {
                    ImagePath = string.IsNullOrWhiteSpace(file.ImagePath) ? null : file.ImagePath,
                    Opacity = Math.Clamp(file.Opacity <= 0 ? 0.24 : file.Opacity, 0.0, 0.6)
                };
            }
        }
        catch
        {
        }
        return new BackgroundFile(null, 0.24);
    }

    private static void Persist(string? imagePath, double opacity)
    {
        try
        {
            Directory.CreateDirectory(SettingsDir);
            var json = JsonSerializer.Serialize(new BackgroundFile(imagePath, Math.Clamp(opacity, 0.0, 0.6)), JsonOpts);
            File.WriteAllText(SettingsPath, json);
        }
        catch
        {
            // 背景偏好保存失败不影响应用使用。
        }
    }

    private sealed record BackgroundFile(
        [property: JsonPropertyName("imagePath")] string? ImagePath,
        [property: JsonPropertyName("opacity")] double Opacity);
}
