using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 单学员进度 ViewModel:加载某学员的进度详情(提交/通过/通过率 + 按语言 + 按难度 + 最近错题 + 已解题目)。
/// 在教师后台用户 Tab 与班级管理成员进度查看处复用。
/// 后端端点未就绪时优雅降级(空数据/"暂无数据"),绝不崩溃。
/// </summary>
public partial class UserProgressViewModel : ViewModelBase
{
    private readonly ProgressService _service;

    /// <summary>进度详情 DTO;null 表示未加载或加载失败</summary>
    [ObservableProperty]
    private UserProgressDto? _progress;

    [ObservableProperty]
    private bool _isLoading;

    /// <summary>状态提示(如"加载失败"/"暂无数据")</summary>
    [ObservableProperty]
    private string? _statusHint;

    public UserProgressViewModel(ProgressService service)
    {
        _service = service;
    }

    /// <summary>拉取指定学员的进度详情。</summary>
    [RelayCommand]
    public async Task LoadAsync(Guid userId)
    {
        try
        {
            IsLoading = true;
            StatusHint = "加载进度…";
            Progress = await _service.GetAsync(userId);
            StatusHint = Progress is null ? "暂无进度数据(后端端点可能未就绪)" : null;
        }
        catch (Exception ex)
        {
            Progress = null;
            StatusHint = "进度加载失败: " + ex.Message;
        }
        finally
        {
            IsLoading = false;
        }
    }
}
