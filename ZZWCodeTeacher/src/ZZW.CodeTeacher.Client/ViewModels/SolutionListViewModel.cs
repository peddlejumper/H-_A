using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 题解列表 ViewModel:某题的题解列表 + 排序 + 查看详情 + 发布 + 点赞 + 采纳。
/// 当前题目 Id 由 MainIdeViewModel 在切题时通过 <see cref="SetProblem"/> 传入。
/// 后端端点未就绪时所有操作优雅降级(空列表/"暂无题解"),绝不崩溃。
/// </summary>
public partial class SolutionListViewModel : ViewModelBase
{
    private readonly SolutionService _service;
    private readonly AuthState _auth;
    private Guid _currentProblemId;

    /// <summary>当前题目的题解列表</summary>
    public ObservableCollection<SolutionListItemDto> Solutions { get; } = new();

    /// <summary>选中题解的详情(含正文/代码)</summary>
    [ObservableProperty]
    private SolutionDto? _detail;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(SelectSolutionCommand))]
    private SolutionListItemDto? _selectedSolution;

    /// <summary>排序模式:hot(热度)/ new(最新)/ accepted(已采纳优先)</summary>
    [ObservableProperty]
    private string _sortMode = "hot";

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private bool _isPosting;

    /// <summary>是否展开发布题解表单</summary>
    [ObservableProperty]
    private bool _isCreating;

    /// <summary>列表区状态提示</summary>
    [ObservableProperty]
    private string? _statusHint;

    // ── 发布表单字段 ──
    [ObservableProperty] private string _newTitle = "";
    [ObservableProperty] private string _newContent = "";
    [ObservableProperty] private string _newCode = "";
    [ObservableProperty] private SupportedLanguage _newLanguage = SupportedLanguage.Python;

    /// <summary>当前用户是否为教师/管理员(控制"采纳"可见性)</summary>
    [ObservableProperty]
    private bool _isTeacher;

    /// <summary>支持语言选项(供发布表单下拉)</summary>
    public IReadOnlyList<SupportedLanguage> LanguageOptions { get; } = Enum.GetValues<SupportedLanguage>();

    public SolutionListViewModel(SolutionService service, AuthState auth)
    {
        _service = service;
        _auth = auth;
        _auth.Changed += (_, _) => SyncRole();
        SyncRole();
    }

    private void SyncRole()
        => IsTeacher = _auth.CurrentUser?.Role == UserRole.Teacher
                    || _auth.CurrentUser?.Role == UserRole.Admin;

    /// <summary>切题时调用:记录当前题目并刷新题解列表,清空详情。</summary>
    public void SetProblem(Guid problemId)
    {
        _currentProblemId = problemId;
        SelectedSolution = null;
        Detail = null;
        _ = RefreshAsync();
    }

    /// <summary>排序模式变更 → 重新拉取列表。</summary>
    partial void OnSortModeChanged(string value) => _ = RefreshAsync();

    /// <summary>拉取当前题目的题解列表(按 SortMode 排序)。</summary>
    [RelayCommand]
    public async Task RefreshAsync()
    {
        if (_currentProblemId == Guid.Empty) return;
        try
        {
            IsLoading = true;
            StatusHint = "加载题解…";
            Solutions.Clear();
            var result = await _service.ListAsync(_currentProblemId, 1, SortMode);
            if (result?.Items is { } items)
                foreach (var s in items) Solutions.Add(s);
            StatusHint = Solutions.Count > 0 ? $"共 {Solutions.Count} 条题解" : "暂无题解,来写第一篇吧";
            SetStatus($"题解已加载({Solutions.Count} 条)");
        }
        catch (Exception ex)
        {
            StatusHint = "加载题解失败: " + ex.Message;
            SetStatus("题解加载失败");
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>选中某条题解 → 加载详情(正文/代码)。</summary>
    [RelayCommand(CanExecute = nameof(CanSelectSolution))]
    private async Task SelectSolutionAsync(SolutionListItemDto? item)
    {
        if (item is null) { Detail = null; return; }
        SelectedSolution = item;
        Detail = null;
        try
        {
            Detail = await _service.GetAsync(item.Id);
        }
        catch
        {
            Detail = null;
        }
    }

    private static bool CanSelectSolution(SolutionListItemDto? item) => item is not null;

    /// <summary>切换点赞(幂等),本地更新点赞数。</summary>
    [RelayCommand]
    private async Task ToggleLikeAsync(SolutionListItemDto? item)
    {
        if (item is null) return;
        try
        {
            var r = await _service.ToggleLikeAsync(item.Id);
            if (r is not null)
            {
                var idx = Solutions.IndexOf(item);
                if (idx >= 0)
                    Solutions[idx] = item with { LikeCount = r.LikeCount };
                if (Detail?.Id == item.Id)
                    Detail = Detail with { LikeCount = r.LikeCount };
                SetStatus(r.Liked ? "已点赞" : "已取消点赞");
            }
        }
        catch (Exception ex)
        {
            SetStatus("点赞失败: " + ex.Message);
        }
    }

    /// <summary>采纳题解(教师/作者)。成功后本地标记。</summary>
    [RelayCommand]
    private async Task AcceptAsync(SolutionListItemDto? item)
    {
        if (item is null) return;
        try
        {
            await _service.AcceptAsync(item.Id);
            var idx = Solutions.IndexOf(item);
            if (idx >= 0)
                Solutions[idx] = item with { IsAccepted = true };
            if (Detail?.Id == item.Id)
                Detail = Detail with { IsAccepted = true };
            SetStatus("已采纳该题解");
        }
        catch (Exception ex)
        {
            SetStatus("采纳失败: " + ex.Message);
        }
    }

    /// <summary>当前用户是否可采纳指定题解(教师 或 题解作者)。</summary>
    public bool CanAccept(SolutionListItemDto item)
        => IsTeacher || _auth.CurrentUser?.Id == item.UserId;

    /// <summary>展开/收起发布题解表单</summary>
    [RelayCommand]
    private void ToggleCreateForm() => IsCreating = !IsCreating;

    /// <summary>发布题解(标题+正文+可选代码)。</summary>
    [RelayCommand]
    private async Task CreateSolutionAsync()
    {
        if (_currentProblemId == Guid.Empty)
        {
            StatusHint = "请先选择一道题目"; return;
        }
        if (string.IsNullOrWhiteSpace(NewTitle) || string.IsNullOrWhiteSpace(NewContent))
        {
            StatusHint = "标题和正文均不能为空"; return;
        }
        try
        {
            IsPosting = true;
            var lang = string.IsNullOrWhiteSpace(NewCode) ? (SupportedLanguage?)null : NewLanguage;
            var dto = new CreateSolutionDto(NewTitle.Trim(), NewContent.Trim(),
                string.IsNullOrWhiteSpace(NewCode) ? null : NewCode, lang);
            var created = await _service.CreateAsync(_currentProblemId, dto);
            NewTitle = "";
            NewContent = "";
            NewCode = "";
            IsCreating = false;
            if (created is not null)
            {
                SetStatus("题解已发布");
                await RefreshAsync();
            }
            else
            {
                StatusHint = "发布失败(后端可能未就绪)";
            }
        }
        catch (Exception ex)
        {
            StatusHint = "发布失败: " + ex.Message;
        }
        finally
        {
            IsPosting = false;
        }
    }
}
