using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// SM-2 错题复习 ViewModel:今日待复习列表 + 5 档评分(0~5)+ 去做题。
/// 作为 ProfileView 的子区展示;评分后从待复习列表移除该项并刷新。
/// 后端端点未就绪时优雅降级(空列表/"暂无待复习"),绝不崩溃。
/// </summary>
public partial class ReviewViewModel : ViewModelBase
{
    private readonly ReviewService _service;

    /// <summary>今日待复习项列表</summary>
    public ObservableCollection<ReviewItemDto> DueItems { get; } = new();

    [ObservableProperty]
    private ReviewItemDto? _selectedReview;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string? _statusHint;

    public ReviewViewModel(ReviewService service)
    {
        _service = service;
    }

    /// <summary>拉取今日待复习列表。</summary>
    [RelayCommand]
    public async Task RefreshAsync()
    {
        try
        {
            IsLoading = true;
            StatusHint = "加载复习项…";
            var items = await _service.GetDueAsync();
            DueItems.Clear();
            foreach (var r in items) DueItems.Add(r);
            StatusHint = DueItems.Count > 0 ? $"今日待复习 {DueItems.Count} 题" : "今日无待复习,保持节奏!";
            SetStatus($"复习列表已加载({DueItems.Count} 题)");
        }
        catch (Exception ex)
        {
            StatusHint = "加载复习项失败: " + ex.Message;
            SetStatus("复习列表加载失败");
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>提交复习评分(quality 0~5:0 再学/2 困难/3 一般/4 容易/5 完美),更新 SM-2 调度。
    /// 评分对象为当前 SelectedReview;评分后从待复习列表移除该项(SM-2 会按评分安排下次复习)。</summary>
    private async Task RateAsync(int quality)
    {
        if (SelectedReview is null) return;
        var item = SelectedReview;
        try
        {
            await _service.ScheduleAsync(item.ProblemId, quality);
            DueItems.Remove(item);
            SelectedReview = null;
            StatusHint = DueItems.Count > 0 ? $"已评分,剩余 {DueItems.Count} 题" : "今日复习已完成 🎉";
            SetStatus($"已提交评分({quality}/5)");
        }
        catch (Exception ex)
        {
            StatusHint = "评分提交失败: " + ex.Message;
        }
    }

    /// <summary>5 档评分命令(对当前选中复习项评分)。XAML 友好:无参数,各命令绑定固定评分等级。
    /// ReviewRatePayload record 保留供程序化调用;UI 通过下方 5 个命令触发,避免 XAML 构造 record 的限制。</summary>
    [RelayCommand] private Task RateAgainAsync() => RateAsync(0);    // 再学
    [RelayCommand] private Task RateHardAsync() => RateAsync(2);     // 困难
    [RelayCommand] private Task RateGoodAsync() => RateAsync(3);     // 一般
    [RelayCommand] private Task RateEasyAsync() => RateAsync(4);     // 容易
    [RelayCommand] private Task RatePerfectAsync() => RateAsync(5);  // 完美

    /// <summary>去做题:返回 IDE(由 ProfileViewModel 转发导航)。</summary>
    [RelayCommand]
    private void GoToProblem() => NavigateTo(null!);
}

/// <summary>评分命令参数(复习项 + 评分等级)。</summary>
public sealed record ReviewRatePayload(ReviewItemDto? Item, int Quality);
