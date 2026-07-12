using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Extensions.DependencyInjection;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 学员主 IDE 三栏布局 ViewModel。
/// 包含:题目浏览器(左)、代码编辑器+运行面板(中)、AI 教练(右)。
/// </summary>
public partial class MainIdeViewModel : ViewModelBase
{
    private readonly AuthState _auth;
    private readonly IServiceProvider _sp;
    private readonly ThemeService _themeService;
    private readonly CommunityService _community;
    private readonly RecentProblemsStore _recentProblems;
    private readonly SubmissionService _submissions;
    private readonly ReviewService _reviews;
    private readonly GroupService _groups;
    private readonly BackgroundSettingsService _backgroundSettings;
    private readonly SettingsWindowService _settingsWindow;
    private readonly AppSettingsService _appSettings;

    [ObservableProperty]
    private ProblemBrowserViewModel _browser = null!;

    [ObservableProperty]
    private CodeEditorViewModel _editor = null!;

    [ObservableProperty]
    private RunnerPanelViewModel _runner = null!;

    [ObservableProperty]
    private AiChatPanelViewModel _aiChat = null!;

    [ObservableProperty]
    private ExternalPanelViewModel _external = null!;

    [ObservableProperty]
    private DiscussionViewModel _discussionVm = null!;

    [ObservableProperty]
    private AnnouncementsViewModel _announcements = null!;

    /// <summary>题解列表(右栏第 3 个 Tab)</summary>
    [ObservableProperty]
    private SolutionListViewModel _solutions = null!;

    /// <summary>知识点树(左栏 Expander,选中知识点筛选题目)</summary>
    [ObservableProperty]
    private KnowledgePointTreeViewModel _knowledgeTree = null!;

    /// <summary>AI 题目推荐(左栏 Expander)</summary>
    [ObservableProperty]
    private RecommendationViewModel _recommendations = null!;

    /// <summary>代码片段库(本地持久化的可复用片段)</summary>
    [ObservableProperty]
    private SnippetLibraryViewModel _snippetLibrary = null!;

    /// <summary>代码片段库浮层是否展开</summary>
    [ObservableProperty]
    private bool _isSnippetLibraryOpen;

    /// <summary>最近浏览的题目(本地持久化,最新在前;UI 取前若干条展示)</summary>
    public ObservableCollection<RecentProblemItem> RecentProblems { get; } = new();

    [ObservableProperty]
    private bool _isBusy;

    /// <summary>每日打卡按钮文案(如"打卡"或"已打卡 3 天 🔥")</summary>
    [ObservableProperty]
    private string _checkInLabel = "打卡";

    /// <summary>今日是否还可打卡(TodayCheckedIn=true 则禁用)</summary>
    [ObservableProperty]
    private bool _canCheckIn = true;

    /// <summary>题目描述区是否展开(可折叠让出空间给编辑器)</summary>
    [ObservableProperty]
    private bool _isDescriptionExpanded = true;

    /// <summary>评测结果区是否展开(折叠后让出空间给编辑器)</summary>
    [ObservableProperty]
    private bool _isRunnerExpanded = true;

    /// <summary>当前用户是否为教师/管理员(控制「教师后台」入口可见性)</summary>
    [ObservableProperty]
    private bool _isTeacher;

    /// <summary>当前主题名(浅色/深色),供工具栏按钮显示</summary>
    [ObservableProperty]
    private string _themeLabel = "浅色";

    /// <summary>提交未通过时是否自动让 AI 解释错误(默认开,可在 ⋯ 菜单切换)</summary>
    [ObservableProperty]
    private bool _autoAiExplain = true;

    /// <summary>今日待复习题目数(⋯ 菜单「今日复习」Badge;后端未就绪为 0)</summary>
    [ObservableProperty]
    private int _reviewDueCount;

    /// <summary>「加入班级」弹窗是否展开(⋯ 菜单 → 加入班级)</summary>
    [ObservableProperty]
    private bool _isJoinGroupOpen;

    /// <summary>加入班级邀请码输入</summary>
    [ObservableProperty]
    private string _joinInviteCode = "";

    /// <summary>加入班级请求中(禁用按钮)</summary>
    [ObservableProperty]
    private bool _isJoining;

    /// <summary>当前题目的"我的提交历史"(切题后后台拉取最近 10 条;后端端点未就绪时为空)</summary>
    public ObservableCollection<SubmissionDto> ProblemSubmissions { get; } = new();

    /// <summary>历史提交列表是否展开(评测结果区下方可折叠)</summary>
    [ObservableProperty]
    private bool _isHistoryExpanded;

    public MainIdeViewModel(AuthState auth, IServiceProvider sp,
        ProblemBrowserViewModel browser, CodeEditorViewModel editor,
        RunnerPanelViewModel runner, AiChatPanelViewModel aiChat,
        ExternalPanelViewModel external, ThemeService themeService,
        CommunityService community, DiscussionViewModel discussion,
        AnnouncementsViewModel announcements, SubmissionService submissions,
        SnippetLibraryViewModel snippetLibrary, RecentProblemsStore recentProblems,
        SolutionListViewModel solutions, KnowledgePointTreeViewModel knowledgeTree,
        RecommendationViewModel recommendations, ReviewService reviews,
        GroupService groups, BackgroundSettingsService backgroundSettings,
        SettingsWindowService settingsWindow, AppSettingsService appSettings)
    {
        _auth = auth;
        _sp = sp;
        _themeService = themeService;
        _community = community;
        _submissions = submissions;
        _recentProblems = recentProblems;
        _reviews = reviews;
        _groups = groups;
        _backgroundSettings = backgroundSettings;
        _settingsWindow = settingsWindow;
        _appSettings = appSettings;

        // 从本地设置读取"提交失败自动 AI 解释"初值(默认 true)
        AutoAiExplain = appSettings.GetAutoAiExplain();
        Browser = browser;
        Editor = editor;
        Runner = runner;
        AiChat = aiChat;
        External = external;
        DiscussionVm = discussion;
        Announcements = announcements;
        SnippetLibrary = snippetLibrary;
        Solutions = solutions;
        KnowledgeTree = knowledgeTree;
        Recommendations = recommendations;

        // 片段库"插入"请求 → 追加内容到编辑器并关闭浮层
        SnippetLibrary.InsertRequested += (_, content) => InsertSnippet(content);

        // 初始化最近浏览列表(从本地存储加载前 8 条)
        RefreshRecentProblems();

        // 主题按钮文案跟随 ThemeService 状态
        ThemeLabel = _themeService.CurrentThemeName;
        _themeService.ThemeChanged += (_, t) => ThemeLabel = t == AppTheme.Light ? "浅色" : "深色";

        // 选中题目 → 加载详情到编辑器
        Browser.ProblemSelected += OnProblemSelected;

        // 知识点树筛选结果 → 替换题目列表展示(null = 清除筛选,恢复完整列表)
        KnowledgeTree.ProblemsLoaded += OnKnowledgeProblemsLoaded;

        // 监听编辑器语言切换 → 同步到运行面板与 AI 教练
        Editor.PropertyChanged += (_, e) =>
        {
            if (e.PropertyName == nameof(CodeEditorViewModel.Language))
            {
                Runner.Language = Editor.Language;
                AiChat.SetLanguage(Editor.Language);
            }
            if (e.PropertyName == nameof(CodeEditorViewModel.Code))
            {
                AiChat.SetContext(AiChat.CurrentProblemId, Editor.Code);
            }
        };

        // 进入 IDE 时自动加载题目列表(后台触发,不阻塞 UI)
        _ = LoadBrowserAsync();

        // 初始化每日打卡状态(后台拉取,失败不阻塞)
        _ = InitCheckInStatusAsync();

        // 进入 IDE 时后台拉取公告(更新铃铛未读数;失败不阻塞)
        _ = Announcements.RefreshAsync();

        // 后台拉取 AI 推荐 + 知识点树 + 今日复习数(均优雅降级,失败不阻塞)
        _ = Recommendations.RefreshAsync();
        _ = KnowledgeTree.RefreshAsync();
        _ = InitReviewDueCountAsync();

        // 教师/管理员入口可见性(登录后 CurrentUser 非空;此处 null 安全判断)
        IsTeacher = _auth.CurrentUser?.Role == UserRole.Teacher
                 || _auth.CurrentUser?.Role == UserRole.Admin;
    }

    private async Task LoadBrowserAsync()
    {
        try { await Browser.RefreshAsync(); }
        catch { /* 题目加载失败不阻塞 IDE 进入,用户可用刷新按钮重试 */ }
    }

    /// <summary>知识点树筛选结果回调:null → 清除筛选(恢复完整列表);非 null → 仅展示这些题目。</summary>
    private async void OnKnowledgeProblemsLoaded(object? sender, IReadOnlyList<ProblemListItemDto>? problems)
    {
        try
        {
            if (problems is null)
                await Browser.RefreshAsync();
            else
                Browser.DisplayProblems(problems, $"已按知识点筛选({problems.Count} 题)");
        }
        catch { /* 筛选失败不阻塞 */ }
    }

    /// <summary>后台拉取今日待复习数(供 ⋯ 菜单「今日复习」Badge;失败保持 0)。</summary>
    private async Task InitReviewDueCountAsync()
    {
        if (!_auth.IsLoggedIn) return;
        try
        {
            var items = await _reviews.GetDueAsync();
            ReviewDueCount = items.Count;
        }
        catch { ReviewDueCount = 0; }
    }

    /// <summary>点击 AI 推荐题 → 加载该题到编辑器(复用题目详情拉取逻辑)。</summary>
    [RelayCommand]
    private async Task OpenRecommendedProblemAsync(Guid problemId)
    {
        if (problemId == Guid.Empty) return;
        try
        {
            IsBusy = true;
            SetStatus("加载推荐题目…");
            var detail = await Browser.LoadDetailAsync(problemId);
            if (detail is not null)
            {
                Editor.SetProblem(detail);
                Runner.SetProblem(detail);
                Runner.Language = Editor.Language;
                AiChat.SetContext(detail.Id.ToString(), Editor.Code);
                AiChat.SetLanguage(Editor.Language);
                DiscussionVm.SetProblem(detail.Id);
                Solutions.SetProblem(detail.Id);
                _ = LoadProblemHistoryAsync(detail.Id);
                _recentProblems.Record(detail.Id, detail.Title, detail.Code);
                RefreshRecentProblems();
                SetStatus($"推荐题 {detail.Code} — {detail.Title}");
            }
        }
        catch (Exception ex)
        {
            ShowError("加载推荐题失败: " + ex.Message);
        }
        finally
        {
            IsBusy = false;
        }
    }

    /// <summary>打开博客/知识广场(独立页面)。</summary>
    [RelayCommand]
    private void OpenBlog()
    {
        var blog = _sp.GetRequiredService<BlogViewModel>();
        NavigateTo(blog);
    }

    /// <summary>打开学习画像(含「错题复习」子区)。</summary>
    [RelayCommand]
    private void OpenReviewProfile()
    {
        var profile = _sp.GetRequiredService<ProfileViewModel>();
        NavigateTo(profile);
    }

    /// <summary>展开/关闭「加入班级」弹窗。</summary>
    [RelayCommand]
    private void OpenJoinGroup() => IsJoinGroupOpen = !IsJoinGroupOpen;

    /// <summary>提交邀请码加入班级(学员;成功后关闭弹窗并提示)。</summary>
    [RelayCommand]
    private async Task SubmitJoinGroupAsync()
    {
        if (string.IsNullOrWhiteSpace(JoinInviteCode))
        {
            SetStatus("请输入邀请码");
            return;
        }
        try
        {
            IsJoining = true;
            var g = await _groups.JoinAsync(JoinInviteCode.Trim());
            JoinInviteCode = "";
            if (g is not null)
            {
                IsJoinGroupOpen = false;
                SetStatus($"已加入班级「{g.Name}」");
            }
            else
            {
                SetStatus("加入失败:邀请码无效或后端未就绪");
            }
        }
        catch (Exception ex)
        {
            SetStatus("加入班级失败: " + ex.Message);
        }
        finally
        {
            IsJoining = false;
        }
    }

    private async void OnProblemSelected(object? sender, ProblemListItemDto? problem)
    {
        if (problem is null) return;
        try
        {
            IsBusy = true;
            SetStatus($"加载题目 {problem.Code}…");
            // 通过子 VM 的 service 拉取详情
            var detail = await Browser.LoadDetailAsync(problem.Id);
            if (detail is not null)
            {
                Editor.SetProblem(detail);
                Runner.SetProblem(detail);
                Runner.Language = Editor.Language;
                AiChat.SetContext(detail.Id.ToString(), Editor.Code);
                AiChat.SetLanguage(Editor.Language);
                // 切题 → 刷新该题讨论列表
                DiscussionVm.SetProblem(detail.Id);
                // 切题 → 刷新该题题解列表(右栏「题解」Tab)
                Solutions.SetProblem(detail.Id);
                // 切题 → 后台拉取该题我的提交历史(最近 10 条;端点未就绪时空,不报错)
                _ = LoadProblemHistoryAsync(detail.Id);
                // 切题 → 记录到最近浏览(本地持久化,最新置顶)
                _recentProblems.Record(detail.Id, detail.Title, detail.Code);
                RefreshRecentProblems();
                SetStatus($"题目 {problem.Code} — {problem.Title}");
            }
        }
        catch (Exception ex)
        {
            ShowError("加载题目失败: " + ex.Message);
        }
        finally
        {
            IsBusy = false;
        }
    }

    /// <summary>后台拉取当前题目的"我的提交历史"(最近 10 条),用于评测结果区下方的可折叠列表。
    /// 后端端点未就绪(404/异常)时清空集合并保持"暂无数据"占位,绝不崩溃。</summary>
    private async Task LoadProblemHistoryAsync(Guid problemId)
    {
        if (!_auth.IsLoggedIn) { ProblemSubmissions.Clear(); return; }
        try
        {
            var page = await _submissions.ListByProblemAsync(problemId, 1, 10);
            ProblemSubmissions.Clear();
            if (page?.Items is { } items)
                foreach (var s in items) ProblemSubmissions.Add(s);
        }
        catch
        {
            // 优雅降级:历史拉取失败不影响做题
            ProblemSubmissions.Clear();
        }
    }

    /// <summary>加载某条历史提交的代码到编辑器(便于从上次尝试继续/复盘)。覆盖当前草稿,请慎用。</summary>
    [RelayCommand]
    private void LoadHistoryCode(SubmissionDto? sub)
    {
        if (sub is null) return;
        Editor.Code = sub.Code;
        Editor.Language = sub.Language;
        SetStatus($"已加载历史提交 #{sub.Id} 代码(分数 {sub.Score}/{sub.TotalCases}),可直接修改重试");
    }

    [RelayCommand]
    private async Task RunSampleAsync()
    {
        await Runner.RunSampleAsync(Editor.Code);
    }

    /// <summary>切换题目描述区的展开/折叠</summary>
    [RelayCommand]
    private void ToggleDescription() => IsDescriptionExpanded = !IsDescriptionExpanded;

    /// <summary>切换评测结果区的展开/折叠</summary>
    [RelayCommand]
    private void ToggleRunner() => IsRunnerExpanded = !IsRunnerExpanded;

    [RelayCommand]
    private async Task SubmitAsync()
    {
        SubmissionDto? submission = null;
        try
        {
            IsBusy = true;
            submission = await Runner.SubmitAsync(Editor.Code);
            if (submission is not null)
            {
                SetStatus($"提交 #{submission.Id} 状态: {submission.Status}  分数: {submission.Score}/{submission.TotalCases}");
                AiChat.SetLastError(submission.ErrorMessage);
                // 切题后历史列表本地追加一条(无需重新拉取)
                ProblemSubmissions.Insert(0, submission);
            }
        }
        catch (Exception ex)
        {
            ShowError("提交失败: " + ex.Message);
            return;
        }
        finally
        {
            IsBusy = false;
        }

        // ── AI 评测结果联动:未通过则自动让 AI 解释错误 ──
        // 防循环:此处仅触发 AI 分析,不触发提交;AI 分析失败不阻塞。
        if (submission is not null
            && AutoAiExplain
            && submission.Status != SubmissionStatus.Accepted)
        {
            SetStatus("评测未通过,正在让 AI 分析...");
            try
            {
                await AiChat.ExplainErrorCommand.ExecuteAsync(null);
            }
            catch
            {
                // AI 分析失败:不影响做题,状态保持原评测结果
                SetStatus($"AI 分析失败,评测状态: {submission.Status}");
            }
        }
    }

    public void SetCustomBackground(string path)
    {
        _backgroundSettings.SetImage(path);
        SetStatus("已设置自定义背景图片");
    }

    public void ClearCustomBackground()
    {
        _backgroundSettings.Clear();
        SetStatus("已清除自定义背景图片");
    }

    [RelayCommand]
    private void OpenProfile()
    {
        var profile = _sp.GetRequiredService<ProfileViewModel>();
        NavigateTo(profile);
    }

    /// <summary>打开教师/管理员后台(题目/提交/用户管理)</summary>
    [RelayCommand]
    private void OpenTeacherDashboard()
    {
        var dash = _sp.GetRequiredService<TeacherDashboardViewModel>();
        NavigateTo(dash);
    }

    /// <summary>打开 AI 接入设置面板(用户自行配置飞书/豆包/OpenAI)</summary>
    [RelayCommand]
    private void OpenAiSettings()
    {
        _settingsWindow.OpenAiSettings();
    }

    /// <summary>切换深色/浅色主题(持久化到本地 theme.json)</summary>
    [RelayCommand]
    private async Task ToggleTheme()
    {
        await _themeService.ToggleAsync();
        SetStatus($"已切换为{_themeService.CurrentThemeName}主题");
    }

    [RelayCommand]
    private void Logout()
    {
        _auth.Clear();
        SetStatus("已退出登录");
    }

    // ── 代码片段库 ──

    /// <summary>打开/关闭代码片段库浮层;打开时刷新列表。</summary>
    [RelayCommand]
    private void OpenSnippetLibrary()
    {
        if (!IsSnippetLibraryOpen) SnippetLibrary.Reload();
        IsSnippetLibraryOpen = !IsSnippetLibraryOpen;
    }

    /// <summary>把指定片段内容追加到编辑器并关闭浮层(由 SnippetLibrary.InsertRequested 事件或 UI 调用)。</summary>
    [RelayCommand]
    private void InsertSnippet(string content)
    {
        Editor.AppendCode(content);
        IsSnippetLibraryOpen = false;
        SetStatus("已插入代码片段");
    }

    // ── 最近浏览 ──

    /// <summary>从本地存储刷新最近浏览集合(UI 展示用,取前 8 条)。</summary>
    private void RefreshRecentProblems()
    {
        RecentProblems.Clear();
        foreach (var item in _recentProblems.GetAll().Take(8))
            RecentProblems.Add(item);
    }

    /// <summary>点击最近浏览项 → 重新加载该题目到编辑器。</summary>
    [RelayCommand]
    private async Task OpenRecentAsync(RecentProblemItem? item)
    {
        if (item is null) return;
        try
        {
            IsBusy = true;
            SetStatus($"加载最近 {item.Code}…");
            var detail = await Browser.LoadDetailAsync(item.ProblemId);
            if (detail is not null)
            {
                Editor.SetProblem(detail);
                Runner.SetProblem(detail);
                Runner.Language = Editor.Language;
                AiChat.SetContext(detail.Id.ToString(), Editor.Code);
                AiChat.SetLanguage(Editor.Language);
                DiscussionVm.SetProblem(detail.Id);
                _ = LoadProblemHistoryAsync(detail.Id);
                _recentProblems.Record(detail.Id, detail.Title, detail.Code);
                RefreshRecentProblems();
                SetStatus($"题目 {detail.Code} — {detail.Title}");
            }
        }
        catch (Exception ex)
        {
            ShowError("加载最近题目失败: " + ex.Message);
        }
        finally
        {
            IsBusy = false;
        }
    }

    // ── 每日打卡 ──

    /// <summary>进入 IDE 时后台拉取打卡状态,设置按钮文案/可用性。</summary>
    private async Task InitCheckInStatusAsync()
    {
        if (!_auth.IsLoggedIn) return;
        try
        {
            var st = await _community.GetCheckInStatusAsync();
            if (st is not null) ApplyCheckInStatus(st);
        }
        catch { /* 状态查询失败不阻塞,按钮保持默认可点击 */ }
    }

    private void ApplyCheckInStatus(CheckInResultDto st)
    {
        CanCheckIn = !st.TodayCheckedIn;
        CheckInLabel = st.TodayCheckedIn
            ? $"已打卡 {st.StreakDays} 天 🔥"
            : $"打卡(已连 {st.StreakDays} 天)";
    }

    /// <summary>每日打卡(幂等),成功后更新按钮文案并提示连续天数。</summary>
    [RelayCommand]
    private async Task CheckInAsync()
    {
        try
        {
            IsBusy = true;
            var st = await _community.CheckInAsync();
            if (st is not null)
            {
                ApplyCheckInStatus(st);
                SetStatus(st.TodayCheckedIn
                    ? $"打卡成功!连续 {st.StreakDays} 天 🔥(累计 {st.TotalCheckIns} 次)"
                    : "今日已打卡,明天再来吧");
            }
        }
        catch (Exception ex)
        {
            ShowError("打卡失败: " + ex.Message);
        }
        finally
        {
            IsBusy = false;
        }
    }
}
