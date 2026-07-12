using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Client.Services;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>AI 设置面板 —— 用户自行接入飞书智能体 / 豆包 / OpenAI / 自定义 OpenAI 兼容服务。</summary>
public partial class AiSettingsViewModel : ViewModelBase
{
    private readonly AiSettingsStore _store;
    private readonly AiService _ai;

    /// <summary>提供商选项(供下拉绑定)</summary>
    public ObservableCollection<AiProvider> Providers { get; } =
        new(Enum.GetValues<AiProvider>());

    [ObservableProperty]
    private AiProvider _selectedProvider;

    [ObservableProperty]
    private string _endpoint = "";

    [ObservableProperty]
    private string _apiKey = "";

    [ObservableProperty]
    private string _model = "";

    [ObservableProperty]
    private double _temperature = 0.3;

    [ObservableProperty]
    private int _maxTokens = 1024;

    [ObservableProperty]
    private string _systemPrompt = "";

    [ObservableProperty]
    private int _timeoutSeconds = 60;

    [ObservableProperty]
    private bool _enabled;

    [ObservableProperty]
    private bool _isTesting;

    [ObservableProperty]
    private string? _testResult;

    [ObservableProperty]
    private bool _testOk;

    /// <summary>配置文件路径(显示给用户)</summary>
#pragma warning disable CA1822
    public string SettingsPath => AiSettingsStore.GetSettingsPath();
#pragma warning restore CA1822

    /// <summary>当前提供商的接入说明</summary>
    public string ProviderGuide => SelectedProvider switch
    {
        AiProvider.Doubao => "豆包(火山方舟 ARK)\n1. 访问 https://console.volcengine.com/ark 创建 API Key\n2. Endpoint 固定:https://ark.cn-beijing.volces.com/api/v3/chat/completions\n3. Model 填 Model ID(如 doubao-seed-1-6-251015)或推理接入点 ID(如 ep-2024xxx)",
        AiProvider.Feishu => "飞书智能体\n1. 在飞书开放平台 https://open.feishu.cn 创建自建应用并启用机器人\n2. 在「智能体」配置模型与权限,获取 OpenAI 兼容网关地址\n3. Endpoint 填智能体的 webhook 或 OpenAI 兼容地址\n4. ApiKey 填应用凭证(token)\n5. Model 填智能体模型标识",
        AiProvider.OpenAI => "OpenAI 官方\n1. 访问 https://platform.openai.com/api-keys 创建 Key\n2. Endpoint:https://api.openai.com/v1/chat/completions\n3. Model:如 gpt-4o-mini / gpt-4o",
        _ => "自定义 OpenAI 兼容服务\n填写完整 Endpoint / Api Key / Model,任何兼容 OpenAI Chat Completions 协议的服务均可(如 DeepSeek、通义千问、Kimi、本地 Ollama 等)。"
    };

    public AiSettingsViewModel(AiSettingsStore store, AiService ai)
    {
        _store = store;
        _ai = ai;
        LoadFrom(_store.Current);
    }

    private void LoadFrom(AiSettings s)
    {
        SelectedProvider = s.Provider;
        Endpoint = s.Endpoint;
        ApiKey = s.ApiKey;
        Model = s.Model;
        Temperature = s.Temperature;
        MaxTokens = s.MaxTokens;
        SystemPrompt = s.SystemPrompt;
        TimeoutSeconds = s.TimeoutSeconds;
        Enabled = s.Enabled;
    }

    /// <summary>切换提供商时,用默认值预填(仅在字段为空或与旧提供商默认值一致时覆盖)</summary>
    partial void OnSelectedProviderChanged(AiProvider value)
    {
        // 重新生成说明(ProviderGuide 是计算属性,XAML 绑定会自动刷新)
        // 提示用户可点"恢复默认"按钮填充该提供商的推荐配置
    }

    /// <summary>用当前所选提供商的默认配置填充表单</summary>
    [RelayCommand]
    private void LoadProviderDefault()
    {
        var d = AiSettings.DefaultFor(SelectedProvider);
        Endpoint = d.Endpoint;
        Model = d.Model;
        Temperature = d.Temperature;
        MaxTokens = d.MaxTokens;
        // ApiKey 不覆盖(用户需自行填)
    }

    /// <summary>保存配置</summary>
    [RelayCommand]
    private void Save()
    {
        var s = new AiSettings
        {
            Provider = SelectedProvider,
            Endpoint = Endpoint.Trim(),
            ApiKey = ApiKey.Trim(),
            Model = Model.Trim(),
            Temperature = Temperature,
            MaxTokens = MaxTokens,
            SystemPrompt = SystemPrompt,
            TimeoutSeconds = TimeoutSeconds,
            Enabled = Enabled
        };
        _store.Save(s);
        SetStatus($"AI 配置已保存({_store.Current.Provider}) — " +
                   (_store.Current.Enabled ? "已启用" : "未启用"));
    }

    /// <summary>测试连接(用当前表单值,不一定要先保存)</summary>
    [RelayCommand]
    private async Task TestConnectionAsync()
    {
        if (string.IsNullOrWhiteSpace(Endpoint) || string.IsNullOrWhiteSpace(ApiKey) || string.IsNullOrWhiteSpace(Model))
        {
            TestOk = false;
            TestResult = "请先填写 Endpoint / ApiKey / Model";
            return;
        }

        try
        {
            IsTesting = true;
            TestResult = "正在测试连接…";
            var s = new AiSettings
            {
                Provider = SelectedProvider,
                Endpoint = Endpoint.Trim(),
                ApiKey = ApiKey.Trim(),
                Model = Model.Trim(),
                Temperature = Temperature,
                MaxTokens = MaxTokens,
                TimeoutSeconds = TimeoutSeconds
            };
            var (ok, msg, ms) = await _ai.TestConnectionAsync(s);
            TestOk = ok;
            TestResult = msg;
        }
        catch (Exception ex)
        {
            TestOk = false;
            TestResult = "测试失败: " + ex.Message;
        }
        finally
        {
            IsTesting = false;
        }
    }

    /// <summary>返回 IDE</summary>
    [RelayCommand]
    private void Back()
    {
        Save();
        NavigateTo(null!);
    }
}
