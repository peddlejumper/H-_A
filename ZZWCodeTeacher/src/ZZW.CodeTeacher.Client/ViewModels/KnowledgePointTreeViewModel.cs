using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 知识点图谱树 ViewModel:展示知识点树 + 选中知识点筛选题目。
/// 选中知识点 → 拉取该知识点下的题目 → 通过 <see cref="ProblemsLoaded"/> 事件通知 MainIdeViewModel 过滤题目列表。
/// "全部题目"按钮 → 通过 <see cref="ProblemsLoaded"/> 传 null 通知清除筛选(恢复完整列表)。
/// 后端端点未就绪时优雅降级(空树/"暂无知识点"),绝不崩溃。
/// </summary>
public partial class KnowledgePointTreeViewModel : ViewModelBase
{
    private readonly KnowledgePointService _service;

    /// <summary>知识点树(顶层节点,Children 递归展开)</summary>
    public ObservableCollection<KnowledgePointDto> Tree { get; } = new();

    [ObservableProperty]
    private KnowledgePointDto? _selectedPoint;

    [ObservableProperty]
    private bool _isLoading;

    /// <summary>当前是否处于知识点筛选态(用于显示"全部题目"复位按钮)</summary>
    [ObservableProperty]
    private bool _isFiltering;

    /// <summary>当前筛选的知识点名(供标题显示)</summary>
    [ObservableProperty]
    private string? _filterLabel;

    public KnowledgePointTreeViewModel(KnowledgePointService service)
    {
        _service = service;
    }

    /// <summary>题目列表就绪事件:null 表示清除筛选(恢复完整列表),非 null 表示仅显示这些题目。</summary>
    public event EventHandler<IReadOnlyList<ProblemListItemDto>?>? ProblemsLoaded;

    /// <summary>拉取知识点树。</summary>
    [RelayCommand]
    public async Task RefreshAsync()
    {
        try
        {
            IsLoading = true;
            var tree = await _service.GetTreeAsync();
            Tree.Clear();
            foreach (var n in tree) Tree.Add(n);
            SetStatus(Tree.Count > 0 ? $"已加载 {Tree.Count} 个知识点" : "知识点暂不可用");
        }
        catch (Exception ex)
        {
            SetStatus("知识点树加载失败: " + ex.Message);
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>选中某知识点 → 拉取其下题目 → 通知主 VM 过滤列表。</summary>
    [RelayCommand]
    private async Task SelectPointAsync(KnowledgePointDto? point)
    {
        if (point is null) return;
        SelectedPoint = point;
        try
        {
            var problems = await _service.GetProblemsAsync(point.Id);
            IsFiltering = true;
            FilterLabel = point.Name;
            ProblemsLoaded?.Invoke(this, problems);
            SetStatus($"已按知识点「{point.Name}」筛选({problems.Count} 题)");
        }
        catch (Exception ex)
        {
            SetStatus("知识点题目加载失败: " + ex.Message);
        }
    }

    /// <summary>清除知识点筛选 → 通知主 VM 恢复完整题目列表。</summary>
    [RelayCommand]
    private void ClearFilter()
    {
        SelectedPoint = null;
        IsFiltering = false;
        FilterLabel = null;
        ProblemsLoaded?.Invoke(this, null);
        SetStatus("已清除知识点筛选");
    }
}
