using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

public enum SettingsSection
{
    Network,
    Runtime,
    Editor,
    Appearance,
    Ai
}

/// <summary>独立设置窗口 ViewModel:侧边栏 + 多设置页。</summary>
public partial class SettingsViewModel : ViewModelBase
{
    private readonly AppSettingsService _appSettings;
    private readonly BackgroundSettingsService _backgroundSettings;
    private readonly ThemeService _themeService;
    private readonly OpacityService _opacityService;
    private readonly string _appSettingsPath = AppSettingsService.GetSettingsPath();
    private readonly string _backgroundSettingsPath = BackgroundSettingsService.GetSettingsPath();
    private readonly string _themeSettingsPath = ThemeService.GetSettingsPath();
    private readonly string _opacitySettingsPath = OpacityService.GetSettingsPath();

    public AiSettingsViewModel AiSettings { get; }

    public ObservableCollection<RuntimePathItemViewModel> RuntimePaths { get; } = new();

    /// <summary>全部 15 种语言(供默认语言下拉绑定)</summary>
    public static IReadOnlyList<SupportedLanguage> AllLanguages { get; } = Enum.GetValues<SupportedLanguage>();

    [ObservableProperty] private SettingsSection _selectedSection = SettingsSection.Network;
    [ObservableProperty] private string _apiBaseUrl = "";
    [ObservableProperty] private bool _useHttps;
    [ObservableProperty] private string? _backgroundImagePath;
    [ObservableProperty] private double _backgroundOpacity = 0.24;
    [ObservableProperty] private string _status = "设置会自动保存到本地。";
    [ObservableProperty] private bool _isDetecting;

    // 主题设置
    [ObservableProperty] private bool _isDarkTheme;

    // 编辑器设置
    [ObservableProperty] private int _editorFontSize = 13;
    [ObservableProperty] private int _editorTabWidth = 4;
    [ObservableProperty] private SupportedLanguage _selectedDefaultLanguage = SupportedLanguage.Python;
    [ObservableProperty] private bool _autoAiExplain = true;

    // 控件透明度设置(0.0~1.0)
    [ObservableProperty] private double _surfaceOpacity = 0.87;
    [ObservableProperty] private double _toolbarOpacity = 0.92;
    [ObservableProperty] private double _insetOpacity = 0.75;
    [ObservableProperty] private double _editorOpacity = 0.75;
    [ObservableProperty] private double _borderOpacity = 0.6;

    public bool IsNetworkSelected => SelectedSection == SettingsSection.Network;
    public bool IsRuntimeSelected => SelectedSection == SettingsSection.Runtime;
    public bool IsEditorSelected => SelectedSection == SettingsSection.Editor;
    public bool IsAppearanceSelected => SelectedSection == SettingsSection.Appearance;
    public bool IsAiSelected => SelectedSection == SettingsSection.Ai;

    public string AppSettingsPath => _appSettingsPath;
    public string BackgroundSettingsPath => _backgroundSettingsPath;
    public string ThemeSettingsPath => _themeSettingsPath;
    public string OpacitySettingsPath => _opacitySettingsPath;

    public SettingsViewModel(AppSettingsService appSettings,
        BackgroundSettingsService backgroundSettings,
        ThemeService themeService,
        OpacityService opacityService,
        AiSettingsViewModel aiSettings)
    {
        _appSettings = appSettings;
        _backgroundSettings = backgroundSettings;
        _themeService = themeService;
        _opacityService = opacityService;
        AiSettings = aiSettings;

        LoadFromServices();
        _backgroundSettings.Changed += (_, path) => BackgroundImagePath = path;
        _backgroundSettings.OpacityChanged += (_, opacity) => BackgroundOpacity = opacity;
        _themeService.ThemeChanged += (_, theme) => IsDarkTheme = theme == AppTheme.Dark;
    }

    partial void OnSelectedSectionChanged(SettingsSection value)
    {
        OnPropertyChanged(nameof(IsNetworkSelected));
        OnPropertyChanged(nameof(IsRuntimeSelected));
        OnPropertyChanged(nameof(IsEditorSelected));
        OnPropertyChanged(nameof(IsAppearanceSelected));
        OnPropertyChanged(nameof(IsAiSelected));
    }

    [RelayCommand]
    private void SelectSection(string section)
    {
        if (Enum.TryParse<SettingsSection>(section, out var parsed))
            SelectedSection = parsed;
    }

    [RelayCommand]
    private void SaveNetwork()
    {
        var current = _appSettings.Current;
        _appSettings.Save(current with
        {
            UseHttps = UseHttps,
            ApiBaseUrl = ApiBaseUrl
        });
        ApiBaseUrl = _appSettings.Current.ApiBaseUrl;
        Status = "网络设置已保存，API 地址变更将在重启客户端后完全生效。";
    }

    [RelayCommand]
    private void SaveRuntime()
    {
        var current = _appSettings.Current;
        _appSettings.Save(current with
        {
            RuntimePaths = RuntimePaths.ToDictionary(x => x.Language.ToString(), x => x.ExecutablePath.Trim())
        });
        Status = "运行环境设置已保存。服务端评测语言仍以服务端运行环境为准。";
    }

    /// <summary>保存主题设置:立即切换浅色/深色并持久化到 theme.json。</summary>
    [RelayCommand]
    private async Task SaveThemeAsync()
    {
        var target = IsDarkTheme ? AppTheme.Dark : AppTheme.Light;
        await _themeService.SetAsync(target);
        Status = $"主题已切换为 {_themeService.CurrentThemeName},立即生效。";
    }

    /// <summary>保存编辑器与行为设置:字号 / Tab 宽 / 默认语言 / 失败自动 AI 解释。重启后生效。</summary>
    [RelayCommand]
    private void SaveEditor()
    {
        var current = _appSettings.Current;
        _appSettings.Save(current with
        {
            EditorFontSize = Math.Clamp(EditorFontSize, 10, 22),
            EditorTabWidth = Math.Clamp(EditorTabWidth, 2, 8),
            DefaultLanguage = (int)SelectedDefaultLanguage,
            AutoAiExplain = AutoAiExplain
        });
        // 同步回显(范围钳制后的值)
        EditorFontSize = _appSettings.Current.EditorFontSize;
        EditorTabWidth = _appSettings.Current.EditorTabWidth;
        Status = "编辑器与行为设置已保存。字号/Tab 宽将在下次打开编辑器时生效;默认语言与自动 AI 解释立即生效。";
    }

    /// <summary>
    /// 自动检测全部 15 种语言的运行环境:从系统 PATH 查找默认命令名,
    /// 找到则填入绝对路径,未找到则保留用户已配置的值(避免覆盖手动配置)。
    /// </summary>
    [RelayCommand(CanExecute = nameof(CanDetectAll))]
    private async Task DetectAllAsync()
    {
        IsDetecting = true;
        Status = "正在自动检测系统 PATH 中的语言运行环境...";
        try
        {
            var detected = await AppSettingsService.DetectAllRuntimeAsync();
            var hit = 0;
            foreach (var item in RuntimePaths)
            {
                if (detected.TryGetValue(item.Language, out var path) && !string.IsNullOrWhiteSpace(path))
                {
                    item.ExecutablePath = path;
                    hit++;
                }
                // 未找到则保留原值(用户可能已配置非默认路径或不想配置)
            }
            Status = $"自动检测完成:在 PATH 中找到 {hit}/{RuntimePaths.Count} 种语言。点击「保存运行环境」以持久化。";
        }
        catch (OperationCanceledException)
        {
            Status = "自动检测已取消。";
        }
        catch (Exception ex)
        {
            Status = $"自动检测失败: {ex.Message}";
        }
        finally
        {
            IsDetecting = false;
        }
    }

    private bool CanDetectAll => !IsDetecting;

    partial void OnIsDetectingChanged(bool value)
    {
        DetectAllCommand.NotifyCanExecuteChanged();
    }

    /// <summary>
    /// 由 View 层文件对话框调用:为指定语言填入用户选择的可执行文件绝对路径。
    /// 不直接持久化,需用户点击「保存运行环境」。
    /// </summary>
    public void SetRuntimePath(SupportedLanguage language, string path)
    {
        var item = RuntimePaths.FirstOrDefault(x => x.Language == language);
        if (item is null) return;
        item.ExecutablePath = path;
        Status = $"{language.DisplayName()} 路径已更新。点击「保存运行环境」以持久化。";
    }

    public void SetBackgroundImage(string path)
    {
        _backgroundSettings.SetImage(path);
        BackgroundImagePath = path;
        Status = "背景图片已更新。";
    }

    [RelayCommand]
    private void ClearBackground()
    {
        _backgroundSettings.Clear();
        BackgroundImagePath = null;
        Status = "背景图片已清除。";
    }

    [RelayCommand]
    private void SaveAppearance()
    {
        _backgroundSettings.SetOpacity(BackgroundOpacity);
        Status = "外观设置已保存。";
    }

    /// <summary>保存控件透明度设置:立即应用到界面(修改 Glass Brush.Color alpha)。</summary>
    [RelayCommand]
    private void SaveOpacity()
    {
        _opacityService.Save(new OpacitySettings(
            Math.Clamp(SurfaceOpacity, 0.0, 1.0),
            Math.Clamp(ToolbarOpacity, 0.0, 1.0),
            Math.Clamp(InsetOpacity, 0.0, 1.0),
            Math.Clamp(EditorOpacity, 0.0, 1.0),
            Math.Clamp(BorderOpacity, 0.0, 1.0)));
        // 同步回显(钳制后的值)
        SurfaceOpacity = _opacityService.Current.Surface;
        ToolbarOpacity = _opacityService.Current.Toolbar;
        InsetOpacity = _opacityService.Current.Inset;
        EditorOpacity = _opacityService.Current.Editor;
        BorderOpacity = _opacityService.Current.Border;
        Status = "控件透明度已保存并立即生效。";
    }

    /// <summary>重置透明度为默认值(Light 主题原始 alpha 比例)。</summary>
    [RelayCommand]
    private void ResetOpacity()
    {
        var d = OpacityService.Defaults;
        SurfaceOpacity = d.Surface;
        ToolbarOpacity = d.Toolbar;
        InsetOpacity = d.Inset;
        EditorOpacity = d.Editor;
        BorderOpacity = d.Border;
        Status = "已重置为默认透明度,点击「保存透明度」生效。";
    }

    [RelayCommand]
    private async Task SaveAllAsync()
    {
        SaveNetwork();
        SaveRuntime();
        SaveEditor();
        SaveAppearance();
        SaveOpacity();
        await SaveThemeAsync();
        AiSettings.SaveCommand.Execute(null);
        Status = "所有设置已保存。";
    }

    private void LoadFromServices()
    {
        ApiBaseUrl = _appSettings.Current.ApiBaseUrl;
        UseHttps = _appSettings.Current.UseHttps;
        BackgroundImagePath = _backgroundSettings.ImagePath;
        BackgroundOpacity = _backgroundSettings.Opacity;

        // 主题
        IsDarkTheme = _themeService.CurrentTheme == AppTheme.Dark;

        // 编辑器与行为
        EditorFontSize = _appSettings.GetEditorFontSize();
        EditorTabWidth = _appSettings.GetEditorTabWidth();
        SelectedDefaultLanguage = _appSettings.GetDefaultLanguage();
        AutoAiExplain = _appSettings.GetAutoAiExplain();

        // 控件透明度
        SurfaceOpacity = _opacityService.Current.Surface;
        ToolbarOpacity = _opacityService.Current.Toolbar;
        InsetOpacity = _opacityService.Current.Inset;
        EditorOpacity = _opacityService.Current.Editor;
        BorderOpacity = _opacityService.Current.Border;

        RuntimePaths.Clear();
        foreach (SupportedLanguage lang in Enum.GetValues<SupportedLanguage>())
            RuntimePaths.Add(new RuntimePathItemViewModel(lang, _appSettings.GetRuntimePath(lang)));
    }
}

public partial class RuntimePathItemViewModel : ObservableObject
{
    public SupportedLanguage Language { get; }
    public string DisplayName => Language.DisplayName();

    [ObservableProperty] private string _executablePath;

    public RuntimePathItemViewModel(SupportedLanguage language, string executablePath)
    {
        Language = language;
        _executablePath = executablePath;
    }
}
