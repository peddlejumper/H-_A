using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Avalonia.Media.Imaging;
using Microsoft.Extensions.DependencyInjection;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Client.Views;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>主窗口 ViewModel —— 持有当前显示的子视图(Login 或 MainIDE),
/// 并提供全局快捷键导航、命令面板(Ctrl+K)、主题切换、退出登录等能力。</summary>
public partial class MainWindowViewModel : ViewModelBase
{
    private readonly AuthState _auth;
    private readonly IServiceProvider _sp;
    private readonly ThemeService _themeService;
    private readonly BackgroundSettingsService _backgroundSettings;
    private readonly SettingsWindowService _settingsWindow;
    private MainIdeViewModel? _ide;
    private LoginViewModel? _login;

    [ObservableProperty]
    private ViewModelBase? _activeView;

    [ObservableProperty]
    private string _statusBar = "就绪";

    [ObservableProperty]
    private string _userName = "未登录";

    [ObservableProperty]
    private Bitmap? _backgroundImage;

    [ObservableProperty]
    private bool _hasCustomBackground;

    [ObservableProperty]
    private double _backgroundImageOpacity = 0.24;

    /// <summary>命令面板 ViewModel(Ctrl+K 弹出)</summary>
    public CommandPaletteViewModel CommandPalette { get; }

    /// <summary>命令面板是否展开</summary>
    [ObservableProperty]
    private bool _isCommandPaletteOpen;

    public MainWindowViewModel(AuthState auth, IServiceProvider sp,
        ThemeService themeService, BackgroundSettingsService backgroundSettings,
        SettingsWindowService settingsWindow, CommandPaletteViewModel commandPalette)
    {
        _auth = auth;
        _sp = sp;
        _themeService = themeService;
        _backgroundSettings = backgroundSettings;
        _settingsWindow = settingsWindow;
        CommandPalette = commandPalette;

        _auth.Changed += (_, _) => SyncFromAuth();
        CommandPalette.RequestExecute += OnPaletteExecute;
        _backgroundSettings.Changed += (_, path) => LoadBackgroundImage(path);
        _backgroundSettings.OpacityChanged += (_, opacity) => BackgroundImageOpacity = opacity;

        SyncFromAuth();
        BackgroundImageOpacity = _backgroundSettings.Opacity;
        LoadBackgroundImage(_backgroundSettings.ImagePath);
    }

    private void SyncFromAuth()
    {
        if (_auth.IsLoggedIn)
        {
            UserName = $"{_auth.CurrentUser!.DisplayName} ({_auth.CurrentUser.Role})";
            _ide ??= _sp.GetRequiredService<MainIdeViewModel>();
            WireNavigation(_ide);
            ActiveView = _ide;
            StatusBar = $"已登录 — {UserName}";
        }
        else
        {
            UserName = "未登录";
            _ide = null; // 退出登录后丢弃旧 IDE 状态
            _login ??= _sp.GetRequiredService<LoginViewModel>();
            WireNavigation(_login);
            ActiveView = _login;
            StatusBar = "未登录";
        }
    }

    private void WireNavigation(ViewModelBase vm)
    {
        vm.RequestViewChange -= HandleViewChange;
        vm.RequestStatus -= HandleStatusChange;
        vm.RequestError -= HandleErrorChange;
        vm.RequestViewChange += HandleViewChange;
        vm.RequestStatus += HandleStatusChange;
        vm.RequestError += HandleErrorChange;
    }

    /// <summary>处理子视图的导航请求。next 为 null 表示"返回根视图"(IDE 或登录)。</summary>
    private void HandleViewChange(object? sender, ViewModelBase? next)
    {
        if (next is null)
        {
            SyncFromAuth(); // 返回登录态对应的根视图
        }
        else
        {
            WireNavigation(next);
            ActiveView = next;
        }
    }

    private void HandleStatusChange(object? sender, string text) => StatusBar = text;
    private void HandleErrorChange(object? sender, string text) => StatusBar = "⚠ " + text;

    // ── 全局导航(供 MainWindow 快捷键 Alt+1/2/3/4 与 Ctrl+, 调用)──

    /// <summary>按 key 切换主视图:ide / profile / teacher / aisettings。</summary>
    public void NavigateToView(string key)
    {
        if (!_auth.IsLoggedIn && key != "aisettings") return;
        switch (key)
        {
            case "ide":
                if (_ide is not null) { WireNavigation(_ide); ActiveView = _ide; }
                break;
            case "profile":
                {
                    var p = _sp.GetRequiredService<ProfileViewModel>();
                    WireNavigation(p); ActiveView = p;
                }
                break;
            case "teacher":
                if (IsTeacherRole())
                {
                    var t = _sp.GetRequiredService<TeacherDashboardViewModel>();
                    WireNavigation(t); ActiveView = t;
                }
                break;
            case "aisettings":
                _settingsWindow.OpenAiSettings();
                break;
            case "blog":
                {
                    var b = _sp.GetRequiredService<BlogViewModel>();
                    WireNavigation(b); ActiveView = b;
                }
                break;
        }
    }

    private bool IsTeacherRole()
        => _auth.CurrentUser?.Role == UserRole.Teacher || _auth.CurrentUser?.Role == UserRole.Admin;

    // ── 命令面板(Ctrl+K / Cmd+K)──

    /// <summary>切换命令面板开关;打开时刷新可用命令并清空过滤词。</summary>
    [RelayCommand]
    private void ToggleCommandPalette()
    {
        if (!IsCommandPaletteOpen) RefreshCommands();
        IsCommandPaletteOpen = !IsCommandPaletteOpen;
        if (IsCommandPaletteOpen) CommandPalette.FilterText = "";
    }

    /// <summary>关闭命令面板(供 Esc 调用)。</summary>
    [RelayCommand]
    private void CloseCommandPalette() => IsCommandPaletteOpen = false;

    private void RefreshCommands()
    {
        var list = new List<CommandItem>
        {
            new("切换主题(浅色/深色)", "theme-toggle"),
            new("打开学习画像", "profile"),
            new("打开 AI 设置", "aisettings"),
            new("返回 IDE", "ide"),
            new("退出登录", "logout"),
        };
        if (IsTeacherRole())
            list.Add(new CommandItem("打开教师后台", "teacher"));
        if (_ide is not null)
        {
            list.Add(new CommandItem("运行样例", "run-sample"));
            list.Add(new CommandItem("提交评测", "submit"));
            list.Add(new CommandItem("刷新题目列表", "refresh-problems"));
            list.Add(new CommandItem("打开代码片段库", "open-snippets"));
            list.Add(new CommandItem("切换题目描述显示", "toggle-description"));
            list.Add(new CommandItem("清除自定义背景", "clear-background"));
            list.Add(new CommandItem("今日打卡", "checkin"));
        }
        CommandPalette.SetCommands(list);
    }

    /// <summary>命令面板执行请求的分发。</summary>
    private void OnPaletteExecute(object? sender, string key)
    {
        IsCommandPaletteOpen = false;
        switch (key)
        {
            case "theme-toggle": _ = ToggleThemeAsync(); break;
            case "profile": NavigateToView("profile"); break;
            case "teacher": NavigateToView("teacher"); break;
            case "aisettings": _settingsWindow.OpenAiSettings(); break;
            case "ide": NavigateToView("ide"); break;
            case "logout": _auth.Clear(); break;
            case "run-sample": _ide?.RunSampleCommand.Execute(null); break;
            case "submit": _ide?.SubmitCommand.Execute(null); break;
            case "refresh-problems": _ = _ide?.Browser.RefreshAsync(); break;
            case "open-snippets": _ide?.OpenSnippetLibraryCommand.Execute(null); break;
            case "toggle-description": _ide?.ToggleDescriptionCommand.Execute(null); break;
            case "clear-background": _backgroundSettings.Clear(); break;
            case "checkin": _ide?.CheckInCommand.Execute(null); break;
        }
    }

    /// <summary>切换深色/浅色主题(持久化到本地 theme.json)。</summary>
    [RelayCommand]
    private async Task ToggleThemeAsync()
    {
        await _themeService.ToggleAsync();
        StatusBar = $"已切换为{_themeService.CurrentThemeName}主题";
    }

    private void LoadBackgroundImage(string? path)
    {
        BackgroundImage?.Dispose();
        BackgroundImage = null;
        HasCustomBackground = false;

        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
            return;

        try
        {
            BackgroundImage = new Bitmap(path);
            HasCustomBackground = true;
            StatusBar = "已应用自定义背景";
        }
        catch
        {
            HasCustomBackground = false;
            StatusBar = "背景图片加载失败";
        }
    }
}
