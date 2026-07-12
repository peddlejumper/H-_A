using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 第三方平台面板 ViewModel —— 占据主窗口右侧 1/3。
/// 支持飞书 / 洛谷两种第三方登录:
///   - 飞书:简化流程(无 OAuth),点击后用系统浏览器打开飞书网页版,由用户在其中登录。
///   - 洛谷:无官方 OAuth,点击后用系统浏览器打开 luogu.com.cn,由用户在其中登录与浏览题库。
/// 注:Apple Silicon 上 CEF 原生库(仅 x64)无法在 ARM64 进程加载,故采用系统浏览器方案,
/// 视图内显示登录状态与洛谷题库导航。
/// </summary>
public partial class ExternalPanelViewModel : ViewModelBase
{
    private const string FeishuHome = "https://www.feishu.cn";
    private const string LuoguHome = "https://www.luogu.com.cn";

    [ObservableProperty]
    private string _address = "";

    [ObservableProperty]
    private string _displayAddress = "未连接";

    [ObservableProperty]
    private string _currentPlatform = "未登录";

    [ObservableProperty]
    private bool _isFeishuLoggedIn;

    [ObservableProperty]
    private bool _isLuoguLoggedIn;

    /// <summary>当前平台总体状态(显示在顶部)。</summary>
    public string PlatformStatus =>
        (IsFeishuLoggedIn, IsLuoguLoggedIn) switch
        {
            (true, true) => "已登录:飞书 + 洛谷",
            (true, _) => "已登录:飞书",
            (_, true) => "已登录:洛谷",
            _ => "尚未登录任何第三方平台。点击下方按钮选择平台登录。"
        };

    public string FeishuStatus => IsFeishuLoggedIn ? "已登录" : "未登录";
    public string LuoguStatus => IsLuoguLoggedIn ? "已登录" : "未登录";

    private static string Simplify(string url)
    {
        if (Uri.TryCreate(url, UriKind.Absolute, out var u))
            return u.Host + (u.AbsolutePath == "/" ? "" : u.AbsolutePath);
        return url;
    }

    /// <summary>飞书登录 —— 启动系统浏览器打开飞书网页版。</summary>
    [RelayCommand]
    private void LoginFeishu()
    {
        Address = FeishuHome;
        CurrentPlatform = "飞书";
        IsFeishuLoggedIn = true;
        DisplayAddress = Simplify(FeishuHome);
        OpenInBrowser(FeishuHome);
        SetStatus("已通过飞书登录,已在系统浏览器中打开飞书网页版");
        OnPropertyChanged(nameof(PlatformStatus));
        OnPropertyChanged(nameof(FeishuStatus));
    }

    /// <summary>洛谷登录 —— 启动系统浏览器打开 luogu.com.cn。</summary>
    [RelayCommand]
    private void LoginLuogu()
    {
        Address = LuoguHome;
        CurrentPlatform = "洛谷";
        IsLuoguLoggedIn = true;
        DisplayAddress = Simplify(LuoguHome);
        OpenInBrowser(LuoguHome);
        SetStatus("已通过洛谷登录,已在系统浏览器中打开洛谷题库");
        OnPropertyChanged(nameof(PlatformStatus));
        OnPropertyChanged(nameof(LuoguStatus));
    }

    /// <summary>在洛谷题库中搜索题目(系统浏览器打开搜索页)。</summary>
    [RelayCommand]
    private void SearchLuogu(string keyword)
    {
        if (string.IsNullOrWhiteSpace(keyword)) return;
        var q = Uri.EscapeDataString(keyword.Trim());
        var url = $"https://www.luogu.com.cn/problem/list?keyword={q}";
        Address = url;
        CurrentPlatform = "洛谷";
        IsLuoguLoggedIn = true;
        DisplayAddress = $"luogu.com.cn 搜索:{keyword.Trim()}";
        OpenInBrowser(url);
        SetStatus($"在洛谷题库搜索:{keyword.Trim()}");
        OnPropertyChanged(nameof(PlatformStatus));
        OnPropertyChanged(nameof(LuoguStatus));
    }

    /// <summary>跳转到指定洛谷题目(如 P1001)。</summary>
    [RelayCommand]
    private void OpenLuoguProblem(string pid)
    {
        if (string.IsNullOrWhiteSpace(pid)) return;
        var id = pid.Trim();
        var url = $"https://www.luogu.com.cn/problem/{id}";
        Address = url;
        CurrentPlatform = "洛谷";
        IsLuoguLoggedIn = true;
        DisplayAddress = $"luogu.com.cn/problem/{id}";
        OpenInBrowser(url);
        SetStatus($"打开洛谷题目 {id}");
        OnPropertyChanged(nameof(PlatformStatus));
        OnPropertyChanged(nameof(LuoguStatus));
    }

    /// <summary>用系统默认浏览器打开当前地址。</summary>
    [RelayCommand]
    private void OpenInSystemBrowser()
    {
        if (string.IsNullOrEmpty(Address)) return;
        OpenInBrowser(Address);
    }

    private static void OpenInBrowser(string url)
    {
        try
        {
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = url,
                UseShellExecute = true,
            });
        }
        catch (Exception ex)
        {
            // 状态栏提示失败,不阻断流程
            System.Diagnostics.Debug.WriteLine("打开浏览器失败: " + ex.Message);
        }
    }
}
