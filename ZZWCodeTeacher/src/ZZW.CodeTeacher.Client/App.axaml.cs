using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Microsoft.Extensions.DependencyInjection;
using Serilog;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Client.ViewModels;
using ZZW.CodeTeacher.Client.Views;

namespace ZZW.CodeTeacher.Client;

public partial class App : global::Avalonia.Application
{
    public static ServiceProvider Services { get; private set; } = null!;

    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);

        var sc = new ServiceCollection();
        ConfigureServices(sc);
        Services = sc.BuildServiceProvider();
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            // 提前解析 ThemeService:触发构造函数,把持久化的主题应用到
            // Application.RequestedThemeVariant,确保首屏(含登录窗)即用正确主题。
            _ = Services.GetRequiredService<ThemeService>();
            // 提前解析 OpacityService:在首屏前应用用户自定义透明度到 Glass Brush
            Services.GetRequiredService<OpacityService>().Apply();

            var mainVm = Services.GetRequiredService<MainWindowViewModel>();
            desktop.MainWindow = new MainWindow { DataContext = mainVm };
        }

        // 全局异常兜底:写入本地日志(Serilog FileSink)便于排查客户端崩溃
        AppDomain.CurrentDomain.UnhandledException += (_, e) =>
        {
            if (e.ExceptionObject is Exception ex)
                Log.Error(ex, "AppDomain 未处理异常 IsTerminating={IsTerminating}", e.IsTerminating);
            else
                Log.Error("AppDomain 未处理异常对象: {Obj}", e.ExceptionObject);
        };
        TaskScheduler.UnobservedTaskException += (_, e) =>
        {
            Log.Error(e.Exception, "未观察的 Task 异常");
            e.SetObserved();
        };

        base.OnFrameworkInitializationCompleted();
    }

    private static void ConfigureServices(IServiceCollection services)
    {
        var appSettings = new AppSettingsService();

        // 配置 API 基地址(.NET 主后端:题目/提交/认证)
        var apiBase = Environment.GetEnvironmentVariable("ZZW_API_BASE")
            ?? appSettings.Current.ApiBaseUrl;

        services.AddHttpClient("ZZWApi", c =>
        {
            c.BaseAddress = new Uri(apiBase);
            c.Timeout = TimeSpan.FromSeconds(15);
        });

        // 服务
        services.AddSingleton<AuthState>();
        services.AddSingleton(appSettings);
        services.AddSingleton<ApiClient>();
        services.AddSingleton<AuthService>();
        services.AddSingleton<ProblemService>();
        services.AddSingleton<SubmissionService>();
        services.AddSingleton<UserService>();               // 教师/管理员:用户管理
        services.AddSingleton<SubmissionAdminService>();    // 教师/管理员:全部提交+重新评测
        services.AddSingleton<AiSettingsStore>();   // AI 配置本地持久化(单例)
        services.AddSingleton<AiService>();          // AI 教练(直连用户配置的提供商)
        services.AddSingleton<UserStatsService>();
        services.AddSingleton<CommunityService>();   // 社区功能(收藏 / 每日打卡 / 讨论区)
        services.AddSingleton<DraftStore>();         // 代码草稿本地持久化(单例,进程内缓存)
        services.AddSingleton<ThemeService>();       // 深色/浅色主题切换(单例,持久化到 theme.json)
        services.AddSingleton<BackgroundSettingsService>(); // 自定义背景图片(单例,持久化到 background.json)
        services.AddSingleton<OpacityService>();   // 控件透明度自定义(单例,持久化到 opacity.json)
        services.AddSingleton<SettingsWindowService>(); // 独立设置窗口
        services.AddSingleton<AnnouncementService>(); // 教师公告(后端扩展端点,优雅降级)
        services.AddSingleton<SnippetStore>();        // 代码片段库本地持久化
        services.AddSingleton<RecentProblemsStore>(); // 最近浏览题目本地持久化
        // 后端 10 项扩展对应服务(均优雅降级,后端不可达时返回空集合/null)
        services.AddSingleton<SolutionService>();          // 题解
        services.AddSingleton<GroupService>();             // 班级/小组
        services.AddSingleton<ReviewService>();            // SM-2 错题复习
        services.AddSingleton<BlogService>();              // 博客/知识分享
        services.AddSingleton<KnowledgePointService>();    // 知识点图谱
        services.AddSingleton<RecommendationService>();    // AI 题目推荐
        services.AddSingleton<ProgressService>();          // 单学员进度

        // 视图模型
        services.AddSingleton<MainWindowViewModel>();
        services.AddTransient<LoginViewModel>();
        services.AddTransient<MainIdeViewModel>();
        services.AddTransient<ProblemBrowserViewModel>();
        services.AddTransient<CodeEditorViewModel>();
        services.AddTransient<RunnerPanelViewModel>();
        services.AddTransient<AiChatPanelViewModel>();
        services.AddTransient<ExternalPanelViewModel>();
        services.AddTransient<DiscussionViewModel>();   // 讨论区(右栏 Tab)
        services.AddTransient<ProfileViewModel>();
        services.AddTransient<TeacherDashboardViewModel>();   // 教师/管理员后台
        services.AddTransient<AiSettingsViewModel>();
        services.AddTransient<SettingsViewModel>();
        services.AddTransient<AnnouncementsViewModel>();  // 通知中心(教师公告)
        services.AddSingleton<SnippetLibraryViewModel>();   // 代码片段库 VM(单例,跨会话保留)
        services.AddSingleton<CommandPaletteViewModel>();    // 命令面板 VM(Ctrl+K)
        // 7 项扩展对应的 VM
        services.AddTransient<SolutionListViewModel>();      // 题解列表(右栏 Tab)
        services.AddTransient<ReviewViewModel>();            // SM-2 错题复习(Profile 子区)
        services.AddTransient<RecommendationViewModel>();    // AI 推荐(左栏 Expander)
        services.AddTransient<KnowledgePointTreeViewModel>();// 知识点树(左栏 Expander)
        services.AddTransient<BlogViewModel>();              // 博客(独立页面)
        services.AddTransient<GroupManagementViewModel>();   // 班级管理(教师后台 Tab)
        services.AddTransient<UserProgressViewModel>();      // 单学员进度(教师后台 + 班级成员)
    }
}
