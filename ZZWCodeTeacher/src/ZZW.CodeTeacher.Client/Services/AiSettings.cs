using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>AI 提供商类型(均走 OpenAI 兼容 Chat Completions 协议)</summary>
public enum AiProvider
{
    /// <summary>豆包(火山方舟 ARK)</summary>
    Doubao,
    /// <summary>飞书智能体(OpenAI 兼容模式 / 自定义 webhook)</summary>
    Feishu,
    /// <summary>OpenAI 官方</summary>
    OpenAI,
    /// <summary>其他 OpenAI 兼容服务(DeepSeek/通义/Kimi 等)</summary>
    Custom
}

/// <summary>
/// AI 配置(用户自行接入)。所有提供商统一走 OpenAI Chat Completions 兼容协议。
/// 持久化到本地 ai_settings.json。
/// </summary>
public sealed class AiSettings
{
    /// <summary>是否启用 AI(未配置 Key 时自动 false)</summary>
    public bool Enabled { get; set; }

    /// <summary>当前提供商</summary>
    public AiProvider Provider { get; set; } = AiProvider.Doubao;

    /// <summary>Chat Completions 端点(完整 URL)</summary>
    public string Endpoint { get; set; } = "";

    /// <summary>API Key / 接入点凭证</summary>
    public string ApiKey { get; set; } = "";

    /// <summary>模型 ID / 接入点 ID(豆包填 ep-xxx 或 model id;飞书填智能体模型名)</summary>
    public string Model { get; set; } = "";

    /// <summary>温度(0-2,默认 0.3 偏稳定)</summary>
    public double Temperature { get; set; } = 0.3;

    /// <summary>最大输出 token(默认 1024)</summary>
    public int MaxTokens { get; set; } = 1024;

    /// <summary>自定义系统提示(可空;为空时用内置教学 prompt)</summary>
    public string SystemPrompt { get; set; } = "";

    /// <summary>请求超时(秒)</summary>
    public int TimeoutSeconds { get; set; } = 60;

    /// <summary>是否已配置(有 Endpoint 且有 ApiKey 且有 Model)</summary>
    [JsonIgnore]
    public bool IsConfigured =>
        !string.IsNullOrWhiteSpace(Endpoint) &&
        !string.IsNullOrWhiteSpace(ApiKey) &&
        !string.IsNullOrWhiteSpace(Model);

    /// <summary>按提供商返回默认配置(用户切 provider 时预填)</summary>
    public static AiSettings DefaultFor(AiProvider p) => p switch
    {
        AiProvider.Doubao => new AiSettings
        {
            Provider = p,
            Endpoint = "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            Model = "doubao-seed-1-6-251015",
            Temperature = 0.3,
            MaxTokens = 1024
        },
        AiProvider.Feishu => new AiSettings
        {
            Provider = p,
            // 飞书智能体 OpenAI 兼容网关(用户在飞书开放平台创建智能体后获取)
            Endpoint = "https://open.feishu.cn/open-apis/bot/v2/hook/",
            Model = "feishu-bot",
            Temperature = 0.3,
            MaxTokens = 1024
        },
        AiProvider.OpenAI => new AiSettings
        {
            Provider = p,
            Endpoint = "https://api.openai.com/v1/chat/completions",
            Model = "gpt-4o-mini",
            Temperature = 0.3,
            MaxTokens = 1024
        },
        _ => new AiSettings()
    };
}

/// <summary>
/// AI 配置本地持久化。存到 %AppData%/ZZWCodeTeacher/ai_settings.json。
/// 单例,通过 <see cref="Changed"/> 事件通知 AiService 重新加载。
/// </summary>
public sealed class AiSettingsStore
{
    private static readonly string SettingsDir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ZZWCodeTeacher");
    private static readonly string SettingsPath = Path.Combine(SettingsDir, "ai_settings.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    private AiSettings _current = new();

    /// <summary>当前配置(内存副本,修改后需调用 Save)</summary>
    public AiSettings Current
    {
        get => _current;
        private set
        {
            _current = value;
            Changed?.Invoke(this, _current);
        }
    }

    /// <summary>配置变更事件(AiService 监听以重建 HttpClient)</summary>
    public event EventHandler<AiSettings>? Changed;

    public AiSettingsStore()
    {
        Load();
    }

    /// <summary>从磁盘加载;文件不存在或损坏时返回默认配置</summary>
    public void Load()
    {
        try
        {
            if (File.Exists(SettingsPath))
            {
                var json = File.ReadAllText(SettingsPath);
                var s = JsonSerializer.Deserialize<AiSettings>(json, JsonOpts);
                if (s is not null)
                {
                    _current = s;
                    // Enabled 状态由是否配置决定
                    _current.Enabled = s.Enabled && s.IsConfigured;
                    return;
                }
            }
        }
        catch
        {
            // 损坏则忽略,用默认
        }
        _current = new AiSettings();
    }

    /// <summary>保存到磁盘并触发 Changed 事件</summary>
    public void Save(AiSettings settings)
    {
        // 强制约束:未配置完整则禁用
        settings.Enabled = settings.Enabled && settings.IsConfigured;
        _current = settings;

        try
        {
            Directory.CreateDirectory(SettingsDir);
            var json = JsonSerializer.Serialize(settings, JsonOpts);
            File.WriteAllText(SettingsPath, json);
        }
        catch
        {
            // 持久化失败不影响内存使用
        }

        Changed?.Invoke(this, _current);
    }

    /// <summary>获取配置文件路径(供 UI 显示)</summary>
    public static string GetSettingsPath() => SettingsPath;
}
