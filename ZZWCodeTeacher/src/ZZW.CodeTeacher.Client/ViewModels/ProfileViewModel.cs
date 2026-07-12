using System.Collections.ObjectModel;
using System.Globalization;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using LiveChartsCore;
using LiveChartsCore.SkiaSharpView;
using LiveChartsCore.SkiaSharpView.Painting;
using SkiaSharp;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>学习画像窗口:个人统计 + 错题本 + 排行榜 + 提交历史(含用例级明细)。</summary>
public partial class ProfileViewModel : ViewModelBase
{
    private readonly UserStatsService _stats;
    private readonly SubmissionService _submissions;
    private readonly AuthState _auth;

    /// <summary>SM-2 错题复习子区 VM(今日待复习 + 5 档评分)</summary>
    public ReviewViewModel Review { get; }

    /// <summary>最近一次 dashboard 拉取的 TopUsers(all),用作扩展排行榜端点不可用时的回落数据。</summary>
    private IReadOnlyList<TopUserDto> _lastTopUsers = Array.Empty<TopUserDto>();

    [ObservableProperty]
    private string _displayName = "";

    [ObservableProperty]
    private string _role = "";

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string? _errorMessage;

    [ObservableProperty]
    private int _totalProblems;

    [ObservableProperty]
    private int _totalSubmissions;

    [ObservableProperty]
    private int _acceptedSubmissions;

    [ObservableProperty]
    private double _acceptanceRate;

    /// <summary>难度分布(题目维度):Easy/Medium/Hard 数量</summary>
    public ObservableCollection<DifficultyDistributionDto> DifficultyDist { get; } = new();

    /// <summary>近 X 天提交趋势(日期/提交数/通过数)</summary>
    public ObservableCollection<DailySubmissionDto> RecentTrend { get; } = new();

    /// <summary>难度分布环形图系列(Easy/Medium/Hard 三块)</summary>
    [ObservableProperty]
    private ISeries[] _difficultySeries = Array.Empty<ISeries>();

    /// <summary>近 X 天趋势折线图系列(提交数/通过数 两条线)</summary>
    [ObservableProperty]
    private ISeries[] _trendSeries = Array.Empty<ISeries>();

    /// <summary>趋势图 X 轴(日期标签)</summary>
    [ObservableProperty]
    private Axis[] _trendXAxes = Array.Empty<Axis>();

    /// <summary>趋势时间窗:7d/30d/90d。变更自动刷新。</summary>
    [ObservableProperty]
    private string _trendRange = "7d";

    /// <summary>趋势时间窗显示文案(如"近 7 天趋势"),供标题绑定</summary>
    [ObservableProperty]
    private string _trendRangeLabel = "近 7 天趋势";

    /// <summary>按语言维度的提交统计(后端扩展;未就绪时为空,UI 显示"暂无数据")</summary>
    public ObservableCollection<LanguageStatDto> LanguageStats { get; } = new();

    /// <summary>按标签维度的提交统计(Top 10;后端扩展;未就绪时为空)</summary>
    public ObservableCollection<TagStatDto> TagStats { get; } = new();

    /// <summary>语言环形图系列</summary>
    [ObservableProperty]
    private ISeries[] _languageSeries = Array.Empty<ISeries>();

    /// <summary>标签条形图的最大计数(用于 ProgressBar 归一化)</summary>
    [ObservableProperty]
    private int _maxTagCount;

    public ObservableCollection<LeaderboardRow> Leaderboard { get; } = new();
    public ObservableCollection<SubmissionDto> MySubmissions { get; } = new();
    public ObservableCollection<SubmissionDto> WrongBook { get; } = new();

    /// <summary>排行榜范围:all/week/month。变更自动刷新排行榜。</summary>
    [ObservableProperty]
    private string _leaderboardScope = "all";

    /// <summary>排行榜语言筛选:null=全部</summary>
    [ObservableProperty]
    private string? _leaderboardLanguage;

    /// <summary>排行榜语言筛选可选项(null=全部 + 常见语言)</summary>
    public IReadOnlyList<string?> LeaderboardLanguages { get; } = new List<string?>
    {
        null, "Python", "CSharp", "Java", "Cpp", "JavaScript", "Go", "Rust", "C"
    };

    /// <summary>当前选中的提交(用于下钻查看用例明细);null 时关闭详情面板</summary>
    [ObservableProperty]
    private SubmissionDto? _selectedSubmission;

    public ProfileViewModel(UserStatsService stats, SubmissionService submissions, AuthState auth, ReviewViewModel review)
    {
        _stats = stats;
        _submissions = submissions;
        _auth = auth;
        Review = review;
        _ = RefreshAsync();
    }

    /// <summary>TrendRange 变更 → 更新标题并刷新趋势数据</summary>
    partial void OnTrendRangeChanged(string value)
    {
        TrendRangeLabel = value switch { "30d" => "近 30 天趋势", "90d" => "近 90 天趋势", _ => "近 7 天趋势" };
        _ = RefreshAsync();
    }

    /// <summary>排行榜范围变更 → 刷新排行榜(不影响主统计)</summary>
    partial void OnLeaderboardScopeChanged(string value) => _ = RefreshLeaderboardAsync();

    /// <summary>排行榜语言筛选变更 → 刷新排行榜</summary>
    partial void OnLeaderboardLanguageChanged(string? value) => _ = RefreshLeaderboardAsync();

    [RelayCommand]
    public async Task RefreshAsync()
    {
        if (!_auth.IsLoggedIn) return;
        var u = _auth.CurrentUser!;
        DisplayName = u.DisplayName;
        Role = u.Role.ToString();

        try
        {
            IsLoading = true;
            ErrorMessage = null;
            SelectedSubmission = null;

            // 仪表盘统计(按时间窗传 days;后端未实现则忽略并回落 7 天)
            var days = TrendRange switch { "30d" => 30, "90d" => 90, _ => 7 };
            var s = await _stats.GetDashboardAsync(days);
            if (s is not null)
            {
                TotalProblems = s.TotalProblems;
                TotalSubmissions = s.TotalSubmissions;
                AcceptedSubmissions = s.AcceptedSubmissions;
                AcceptanceRate = Math.Round(s.AcceptanceRate * 100, 1);

                DifficultyDist.Clear();
                foreach (var d in s.DifficultyDistribution) DifficultyDist.Add(d);

                RecentTrend.Clear();
                foreach (var t in s.RecentSubmissions) RecentTrend.Add(t);

                // 按语言/标签维度统计(后端扩展字段;未就绪时为空集合,UI 优雅降级)
                LanguageStats.Clear();
                if (s.ByLanguage is not null)
                    foreach (var ls in s.ByLanguage) LanguageStats.Add(ls);
                TagStats.Clear();
                if (s.ByTag is not null)
                    foreach (var ts in s.ByTag.Take(10)) TagStats.Add(ts);
                MaxTagCount = TagStats.Count > 0 ? TagStats.Max(x => x.Count) : 0;

                // 同步刷新 LiveChartsCore 图表系列(折线趋势 + 环形难度分布 + 语言环形)
                RebuildCharts();

                // 缓存 TopUsers,供排行榜扩展端点不可用时回落
                _lastTopUsers = s.TopUsers ?? Array.Empty<TopUserDto>();
            }

            // 排行榜:走扩展端点;不可用时按当前 scope/language 回落(_lastTopUsers 或空)
            await RefreshLeaderboardAsync();

            // 我的提交(最近 50 条)
            var mine = await _submissions.ListByUserAsync(u.Id, 1, 50);
            MySubmissions.Clear();
            if (mine is not null)
                foreach (var sub in mine.Items) MySubmissions.Add(sub);

            // 错题本
            var wrong = await _submissions.ListWrongByUserAsync(u.Id, 1, 50);
            WrongBook.Clear();
            if (wrong is not null)
                foreach (var sub in wrong.Items) WrongBook.Add(sub);

            // SM-2 今日待复习(后端扩展;失败不阻塞)
            _ = Review.RefreshAsync();

            SetStatus($"画像已刷新: {MySubmissions.Count} 条提交, {WrongBook.Count} 道错题");
        }
        catch (Exception ex)
        {
            ErrorMessage = "画像加载失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>独立刷新排行榜:调用扩展端点 GET /api/v1/dashboard/leaderboard?scope=...&amp;language=...
    /// 端点未就绪(404/异常)时:all+全部语言 回落到 dashboard 缓存的 TopUsers;其他维度显示空 + 提示。绝不崩溃。</summary>
    [RelayCommand]
    public async Task RefreshLeaderboardAsync()
    {
        try
        {
            PagedResult<TopUserDto>? page = null;
            try
            {
                page = await _stats.GetLeaderboardAsync(LeaderboardScope, LeaderboardLanguage, pageSize: 20);
            }
            catch (ApiException)
            {
                // 端点未就绪:page 保持 null,下方回落处理
            }

            Leaderboard.Clear();
            var rank = 1;
            if (page?.Items is { } items && items.Count > 0)
            {
                foreach (var t in items) Leaderboard.Add(new LeaderboardRow(rank++, t));
            }
            else if (LeaderboardScope == "all" && string.IsNullOrEmpty(LeaderboardLanguage))
            {
                // all+全部语言:扩展端点不可用时,回落到 dashboard 缓存的 TopUsers
                foreach (var t in _lastTopUsers)
                    Leaderboard.Add(new LeaderboardRow(rank++, t));
                if (Leaderboard.Count == 0)
                    SetStatus("排行榜数据暂不可用,点击刷新重试");
            }
            else
            {
                SetStatus("排行榜该维度暂无数据(可能后端端点未就绪)");
            }
        }
        catch (Exception ex)
        {
            // 任何异常都不崩溃
            SetStatus("排行榜加载失败: " + ex.Message);
        }
    }

    /// <summary>选中某条提交,展开用例级评测明细</summary>
    [RelayCommand]
    private void SelectSubmission(SubmissionDto? sub)
    {
        SelectedSubmission = SelectedSubmission?.Id == sub?.Id ? null : sub;
    }

    [RelayCommand]
    private void BackToIde()
    {
        // 主窗口监听,null 表示返回 IDE(由 MainWindowViewModel 解释)
        NavigateTo(null!);
    }

    /// <summary>
    /// 根据 RecentTrend / DifficultyDist / LanguageStats 重建 LiveChartsCore 图表系列。
    /// 折线:提交数(蓝 #3B82F6)、通过数(绿 #16A34A);X 轴为日期(随时间窗稀疏化)。
    /// 环形:Easy(绿)/Medium(黄)/Hard(红);语言环形按语言分块。
    /// </summary>
    private void RebuildCharts()
    {
        // ── 趋势折线图 ──
        TrendSeries = new ISeries[]
        {
            new LineSeries<int>
            {
                Name = "提交数",
                Values = RecentTrend.Select(d => d.Submissions).ToArray(),
                Stroke = new SolidColorPaint(new SKColor(0x3B, 0x82, 0xF6)) { StrokeThickness = 2 },
                Fill = new SolidColorPaint(new SKColor(0x3B, 0x82, 0xF6, 0x33)),
                GeometrySize = 5,
                GeometryStroke = new SolidColorPaint(new SKColor(0x3B, 0x82, 0xF6)) { StrokeThickness = 2 },
                GeometryFill = new SolidColorPaint(new SKColor(0xFF, 0xFF, 0xFF)),
                LineSmoothness = 0.2
            },
            new LineSeries<int>
            {
                Name = "通过数",
                Values = RecentTrend.Select(d => d.Accepted).ToArray(),
                Stroke = new SolidColorPaint(new SKColor(0x16, 0xA3, 0x4A)) { StrokeThickness = 2 },
                Fill = new SolidColorPaint(new SKColor(0x16, 0xA3, 0x4A, 0x33)),
                GeometrySize = 5,
                GeometryStroke = new SolidColorPaint(new SKColor(0x16, 0xA3, 0x4A)) { StrokeThickness = 2 },
                GeometryFill = new SolidColorPaint(new SKColor(0xFF, 0xFF, 0xFF)),
                LineSmoothness = 0.2
            }
        };

        // X 轴日期标签:7d 全显示(MM-dd);30d 每 3 天一个(MM-dd);90d 每 7 天一个(yyyy-MM-dd)
        var labels = BuildSparseLabels(RecentTrend, TrendRange);
        TrendXAxes = new Axis[]
        {
            new()
            {
                Labels = labels!,
                LabelsRotation = 0,
                TextSize = 11,
                SeparatorsPaint = new SolidColorPaint(new SKColor(0xCB, 0xD5, 0xE1)) { StrokeThickness = 1 }
            }
        };

        // ── 难度分布环形图 ──
        var easy = DifficultyDist.FirstOrDefault(d => d.Difficulty == DifficultyLevel.Easy);
        var medium = DifficultyDist.FirstOrDefault(d => d.Difficulty == DifficultyLevel.Medium);
        var hard = DifficultyDist.FirstOrDefault(d => d.Difficulty == DifficultyLevel.Hard);

        DifficultySeries = new ISeries[]
        {
            new PieSeries<double>
            {
                Name = "简单",
                Values = new double[] { easy?.Count ?? 0 },
                Fill = new SolidColorPaint(new SKColor(0x16, 0xA3, 0x4A)),
                DataLabelsPaint = new SolidColorPaint(new SKColor(0x11, 0x18, 0x27)),
                DataLabelsSize = 11,
                InnerRadius = 25
            },
            new PieSeries<double>
            {
                Name = "中等",
                Values = new double[] { medium?.Count ?? 0 },
                Fill = new SolidColorPaint(new SKColor(0xF5, 0x9E, 0x0B)),
                DataLabelsPaint = new SolidColorPaint(new SKColor(0x11, 0x18, 0x27)),
                DataLabelsSize = 11,
                InnerRadius = 25
            },
            new PieSeries<double>
            {
                Name = "困难",
                Values = new double[] { hard?.Count ?? 0 },
                Fill = new SolidColorPaint(new SKColor(0xDC, 0x26, 0x26)),
                DataLabelsPaint = new SolidColorPaint(new SKColor(0xFF, 0xFF, 0xFF)),
                DataLabelsSize = 11,
                InnerRadius = 25
            }
        };

        // ── 语言维度环形图(后端扩展;空时不渲染系列) ──
        RebuildLanguageChart();
    }

    /// <summary>根据时间窗生成稀疏化的 X 轴标签(隐藏部分标签避免拥挤)。
    /// 7d:MM-dd 全显示;30d:MM-dd 每 3 个显示 1 个;90d:yyyy-MM-dd 每 7 个显示 1 个。</summary>
    private static string?[] BuildSparseLabels(ObservableCollection<DailySubmissionDto> trend, string range)
    {
        if (trend.Count == 0) return Array.Empty<string?>();
        var step = range switch { "30d" => 3, "90d" => 7, _ => 1 };
        var labels = new string?[trend.Count];
        for (var i = 0; i < trend.Count; i++)
        {
            if (i % step == 0 || i == trend.Count - 1)
                labels[i] = range == "90d"
                    ? trend[i].Date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)
                    : trend[i].Date.ToString("MM-dd", CultureInfo.InvariantCulture);
            // 其余位置为 null:LiveChartsCore 隐藏 null 标签
        }
        return labels;
    }

    /// <summary>构建语言维度环形图。空数据时系列为空(UI 显示"暂无数据"占位)。</summary>
    private void RebuildLanguageChart()
    {
        if (LanguageStats.Count == 0)
        {
            LanguageSeries = Array.Empty<ISeries>();
            return;
        }

        // 一组协调的色彩(与难度分布风格一致,避免硬编码到主题)
        var palette = new[]
        {
            new SKColor(0x3B, 0x82, 0xF6), // 蓝
            new SKColor(0x16, 0xA3, 0x4A), // 绿
            new SKColor(0xF5, 0x9E, 0x0B), // 黄
            new SKColor(0xDC, 0x26, 0x26), // 红
            new SKColor(0x8B, 0x5C, 0xF6), // 紫
            new SKColor(0xEC, 0x48, 0x99), // 粉
            new SKColor(0x14, 0xB8, 0xA6), // 青
            new SKColor(0xEA, 0x58, 0x0C), // 橙
            new SKColor(0x6B, 0x72, 0x80), // 灰
            new SKColor(0x0E, 0xA5, 0xE9), // 天蓝
        };

        var series = new List<ISeries>();
        for (var i = 0; i < LanguageStats.Count; i++)
        {
            var ls = LanguageStats[i];
            var color = palette[i % palette.Length];
            series.Add(new PieSeries<double>
            {
                Name = ls.Language.DisplayName(),
                Values = new double[] { ls.Submitted },
                Fill = new SolidColorPaint(color),
                DataLabelsPaint = new SolidColorPaint(new SKColor(0x11, 0x18, 0x27)),
                DataLabelsSize = 10,
                InnerRadius = 25
            });
        }
        LanguageSeries = series.ToArray();
    }
}

/// <summary>排行榜行:包装 TopUserDto 并附加名次与奖牌色(前 3 名金银铜)。</summary>
public sealed class LeaderboardRow
{
    public int Rank { get; }
    public TopUserDto Source { get; }
    public string DisplayName => Source.DisplayName;
    public int Accepted => Source.Accepted;
    public double AcceptanceRate => Source.AcceptanceRate;

    /// <summary>名次徽章前景色:1 金 / 2 银 / 3 铜,其余灰</summary>
    public string MedalColor => Rank switch
    {
        1 => "#D97706", // 金(琥珀深)
        2 => "#6B7280", // 银
        3 => "#B45309", // 铜
        _ => "#9CA3AF"
    };

    /// <summary>名次徽章背景色</summary>
    public string MedalBackground => Rank switch
    {
        1 => "#FEF3C7",
        2 => "#F3F4F6",
        3 => "#FED7AA",
        _ => "#F9FAFB"
    };

    public LeaderboardRow(int rank, TopUserDto source)
    {
        Rank = rank;
        Source = source;
    }
}
