using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// AI 题目推荐 ViewModel:展示 5 道 AI 推荐题目(题号/标题/难度/推荐理由)。
/// 点击推荐项 → 由 MainIdeViewModel 加载该题到编辑器。
/// 后端端点未就绪时优雅降级(空列表/"暂无推荐"),绝不崩溃。
/// </summary>
public partial class RecommendationViewModel : ViewModelBase
{
    private readonly RecommendationService _service;

    /// <summary>推荐题目列表</summary>
    public ObservableCollection<RecommendedProblemDto> Recommendations { get; } = new();

    [ObservableProperty]
    private bool _isLoading;

    public RecommendationViewModel(RecommendationService service)
    {
        _service = service;
    }

    /// <summary>拉取 AI 推荐题目(默认 5 道)。</summary>
    [RelayCommand]
    public async Task RefreshAsync()
    {
        try
        {
            IsLoading = true;
            var list = await _service.GetRecommendedAsync(5);
            Recommendations.Clear();
            foreach (var r in list) Recommendations.Add(r);
            SetStatus(Recommendations.Count > 0 ? $"已加载 {Recommendations.Count} 道推荐题" : "暂无推荐");
        }
        catch (Exception ex)
        {
            SetStatus("推荐加载失败: " + ex.Message);
        }
        finally
        {
            IsLoading = false;
        }
    }
}
