using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>题目列表行视图模型:包装 ProblemListItemDto + 我对该题的最近提交状态。</summary>
public sealed class ProblemRowVm : ObservableObject
{
    public ProblemListItemDto Source { get; }

    /// <summary>我对该题的最近提交状态;null=未做过</summary>
    public SubmissionStatus? MyStatus { get; set; }

    public ProblemRowVm(ProblemListItemDto source, SubmissionStatus? myStatus = null)
    {
        Source = source;
        MyStatus = myStatus;
    }

    // 代理属性(供 XAML 绑定)
    public Guid Id => Source.Id;

    private bool _isFavorite;

    /// <summary>当前用户是否收藏了该题(变更会同步刷新 FavoriteMark)。</summary>
    public bool IsFavorite
    {
        get => _isFavorite;
        set
        {
            if (SetProperty(ref _isFavorite, value))
                OnPropertyChanged(nameof(FavoriteMark));
        }
    }

    /// <summary>收藏星标(★实心/☆空心),金黄色显示由 XAML 控制。</summary>
    public string FavoriteMark => IsFavorite ? "★" : "☆";
    public string Code => Source.Code;
    public string Title => Source.Title;
    public DifficultyLevel Difficulty => Source.Difficulty;
    public int TestCaseCount => Source.TestCaseCount;
    public int SubmitCount => Source.SubmitCount;
    public int PassCount => Source.PassCount;
    public IReadOnlyList<SupportedLanguage> SupportedLanguages => Source.SupportedLanguages;
    public bool IsActive => Source.IsActive;

    /// <summary>状态标记文本(用于列表项前的圆点)</summary>
    public string StatusMark => MyStatus switch
    {
        SubmissionStatus.Accepted => "✓",
        SubmissionStatus.WrongAnswer or SubmissionStatus.TimeLimitExceeded
            or SubmissionStatus.RuntimeError or SubmissionStatus.CompileError => "✗",
        _ => "·"
    };

    /// <summary>状态标记颜色</summary>
    public string StatusColor => MyStatus switch
    {
        SubmissionStatus.Accepted => "#16A34A",
        SubmissionStatus.WrongAnswer or SubmissionStatus.TimeLimitExceeded
            or SubmissionStatus.RuntimeError or SubmissionStatus.CompileError => "#DC2626",
        _ => "#9CA3AF"
    };

    public void RefreshDisplay()
    {
        OnPropertyChanged(nameof(StatusMark));
        OnPropertyChanged(nameof(StatusColor));
    }
}

/// <summary>左侧题目浏览器:列表 + 搜索 + 难度筛选 + 标签筛选 + 状态标记。</summary>
public partial class ProblemBrowserViewModel : ViewModelBase
{
    private readonly ProblemService _problemService;
    private readonly SubmissionService _submissionService;
    private readonly CommunityService _community;
    private readonly AuthState _auth;

    [ObservableProperty]
    private string _searchText = "";

    [ObservableProperty]
    private DifficultyLevel? _difficultyFilter;

    [ObservableProperty]
    private string? _selectedTag;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string? _errorMessage;

    /// <summary>当前选中行(双向绑定到 ListBox.SelectedItem)。</summary>
    [ObservableProperty]
    private ProblemRowVm? _selectedRow;

    /// <summary>当前选中题目(由 SelectedRow 同步;对外暴露供 MainIdeViewModel 订阅)。</summary>
    [ObservableProperty]
    private ProblemListItemDto? _selectedProblem;

    /// <summary>SelectedRow 变更 → 同步 SelectedProblem → 触发事件加载详情。</summary>
    partial void OnSelectedRowChanged(ProblemRowVm? value)
    {
        SelectedProblem = value?.Source;
        ProblemSelected?.Invoke(this, SelectedProblem);
    }

    /// <summary>全部题目行(含状态标记)。XAML 绑定此集合。</summary>
    public ObservableCollection<ProblemRowVm> Rows { get; } = new();

    /// <summary>从全部题目中提取的标签集合(供标签筛选下拉)</summary>
    public ObservableCollection<string> AllTags { get; } = new();

    /// <summary>难度选项(供下拉)</summary>
    public IReadOnlyList<DifficultyLevel?> DifficultyOptions { get; } =
        new List<DifficultyLevel?> { null, DifficultyLevel.Easy, DifficultyLevel.Medium, DifficultyLevel.Hard };

    /// <summary>我对每题的最近提交状态(ProblemId → Status)</summary>
    private readonly Dictionary<Guid, SubmissionStatus> _myStatus = new();

    /// <summary>当前用户收藏的题目 Id 集合(用于列表星标标记)</summary>
    private readonly HashSet<Guid> _favoriteIds = new();

    /// <summary>原始后端题目列表(用于标签筛选的本地过滤)</summary>
    private List<ProblemListItemDto> _rawProblems = new();

    public event EventHandler<ProblemListItemDto?>? ProblemSelected;

    public ProblemBrowserViewModel(ProblemService problemService, SubmissionService submissionService, CommunityService communityService, AuthState auth)
    {
        _problemService = problemService;
        _submissionService = submissionService;
        _community = communityService;
        _auth = auth;
    }

    /// <summary>SelectedProblem 变更(外部设置)→ 触发事件加载详情。</summary>
    partial void OnSelectedProblemChanged(ProblemListItemDto? value)
        => ProblemSelected?.Invoke(this, value);

    [RelayCommand]
    public async Task RefreshAsync()
    {
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            SetStatus("加载题目列表…");

            // 并发:题目列表 + 我的最近提交(用于状态标记)+ 我的收藏(用于星标)
            var listTask = _problemService.ListAsync(1, 100, SearchText, DifficultyFilter);
            var myTask = _auth.IsLoggedIn
                ? _submissionService.ListByUserAsync(_auth.CurrentUser!.Id, 1, 100)
                : Task.FromResult<PagedResult<SubmissionDto>?>(null);
            var favTask = _auth.IsLoggedIn
                ? _community.ListFavoritesAsync(1, 100)
                : Task.FromResult<PagedResult<ProblemListItemDto>?>(null);
            await Task.WhenAll(listTask, myTask, favTask);

            var result = listTask.Result;
            _rawProblems = result?.Items?.ToList() ?? new List<ProblemListItemDto>();

            // 计算每题最近提交状态(按 SubmittedAt 取最新一条)
            _myStatus.Clear();
            if (myTask.Result?.Items is { } subs)
            {
                foreach (var s in subs.OrderByDescending(x => x.SubmittedAt))
                {
                    if (_myStatus.TryAdd(s.ProblemId, s.Status) && _myStatus.Count >= 200) break;
                }
            }

            // 标记收藏(收藏列表拉取失败不阻塞,星标保持空心)
            _favoriteIds.Clear();
            if (favTask.Result?.Items is { } favs)
            {
                foreach (var f in favs) _favoriteIds.Add(f.Id);
            }

            // 刷新标签集合
            RefreshTags();

            // 渲染(应用标签筛选)
            ApplyTagFilter();

            SetStatus($"已加载 {Rows.Count} 道题目");
        }
        catch (Exception ex)
        {
            ErrorMessage = "加载题目失败: " + ex.Message;
            SetStatus("题目加载失败");
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>搜索框回车 / 难度变更 → 重新拉取列表。</summary>
    [RelayCommand]
    private async Task ApplyFilterAsync() => await RefreshAsync();

    /// <summary>切换难度下拉 → 重新拉取。</summary>
    partial void OnDifficultyFilterChanged(DifficultyLevel? value) => _ = RefreshAsync();

    /// <summary>切换标签筛选 → 本地过滤(不调后端)。</summary>
    partial void OnSelectedTagChanged(string? value) => ApplyTagFilter();

    private void RefreshTags()
    {
        var tags = _rawProblems
            .SelectMany(p => GetAllTags(p))   // ProblemListItemDto 没有 Tags 字段,这里需后端支持;暂用 Title 关键字
            .Distinct()
            .OrderBy(x => x)
            .ToList();
        AllTags.Clear();
        AllTags.Add("(全部)");
        foreach (var t in tags) AllTags.Add(t);
    }

    private static IEnumerable<string> GetAllTags(ProblemListItemDto p)
    {
        // ProblemListItemDto 没暴露 Tags,这里返回空(标签筛选依赖 ProblemDto.Tags,列表项拿不到)
        // 保留钩子,后端如扩展 ProblemListItemDto.Tags 可立即生效
        return Enumerable.Empty<string>();
    }

    private void ApplyTagFilter()
    {
        var tag = SelectedTag is null or "(全部)" ? null : SelectedTag;
        Rows.Clear();
        foreach (var p in _rawProblems)
        {
            _myStatus.TryGetValue(p.Id, out var status);
            Rows.Add(new ProblemRowVm(p, status) { IsFavorite = _favoriteIds.Contains(p.Id) });
        }
    }

    /// <summary>用外部传入的题目列表替换当前展示(用于知识点树筛选)。
    /// 复用最近一次 RefreshAsync 拉取的 _myStatus / _favoriteIds 标记状态与收藏;若无历史数据则标记为空,不影响展示。</summary>
    public void DisplayProblems(IReadOnlyList<ProblemListItemDto> problems, string hint)
    {
        Rows.Clear();
        foreach (var p in problems)
        {
            _myStatus.TryGetValue(p.Id, out var status);
            Rows.Add(new ProblemRowVm(p, status) { IsFavorite = _favoriteIds.Contains(p.Id) });
        }
        SetStatus(string.IsNullOrEmpty(hint) ? $"已筛选 {Rows.Count} 道题目" : hint);
    }

    /// <summary>切换某题收藏状态(星标点击),更新行 IsFavorite 并提示。</summary>
    [RelayCommand]
    private async Task ToggleFavoriteAsync(ProblemRowVm? row)
    {
        if (row is null) return;
        try
        {
            var now = await _community.ToggleFavoriteAsync(row.Id);
            row.IsFavorite = now;
            if (now) _favoriteIds.Add(row.Id); else _favoriteIds.Remove(row.Id);
            SetStatus(now ? $"已收藏「{row.Title}」" : $"已取消收藏「{row.Title}」");
        }
        catch (Exception ex)
        {
            SetStatus("收藏操作失败: " + ex.Message);
        }
    }

    [RelayCommand]
    public void SelectProblem(ProblemListItemDto? problem)
        => ProblemSelected?.Invoke(this, problem);

    /// <summary>从选中项拉取题目详情(含描述、样例、模板)。</summary>
    public async Task<ProblemDto?> LoadDetailAsync(Guid id)
        => await _problemService.GetAsync(id);
}
