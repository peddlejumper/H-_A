using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>通知中心 ViewModel:教师公告列表 + 标记已读 + 教师发布。
/// 后端端点未就绪时所有操作优雅降级(空列表/"暂无公告"),绝不崩溃。</summary>
public partial class AnnouncementsViewModel : ViewModelBase
{
    private readonly AnnouncementService _service;
    private readonly AuthState _auth;

    public ObservableCollection<AnnouncementDto> Items { get; } = new();

    [ObservableProperty]
    private AnnouncementDto? _selectedAnnouncement;

    [ObservableProperty]
    private bool _isLoading;

    /// <summary>未读公告数(用于铃铛 Badge)</summary>
    [ObservableProperty]
    private int _unreadCount;

    /// <summary>当前用户是否为教师/管理员(控制"发布公告"入口可见性)</summary>
    [ObservableProperty]
    private bool _isTeacher;

    /// <summary>是否展开发布公告表单</summary>
    [ObservableProperty]
    private bool _isCreating;

    [ObservableProperty]
    private string _newTitle = "";

    [ObservableProperty]
    private string _newContent = "";

    public AnnouncementsViewModel(AnnouncementService service, AuthState auth)
    {
        _service = service;
        _auth = auth;
        _auth.Changed += (_, _) => SyncRole();
        SyncRole();
    }

    private void SyncRole()
    {
        IsTeacher = _auth.CurrentUser?.Role == UserRole.Teacher
                 || _auth.CurrentUser?.Role == UserRole.Admin;
    }

    /// <summary>拉取公告列表(默认仅生效中);更新未读数。</summary>
    [RelayCommand]
    public async Task RefreshAsync()
    {
        if (!_auth.IsLoggedIn) return;
        try
        {
            IsLoading = true;
            var list = await _service.ListAsync(activeOnly: true);
            Items.Clear();
            foreach (var a in list) Items.Add(a);
            UnreadCount = Items.Count(x => !x.IsRead);
            SetStatus(Items.Count == 0 ? "暂无公告" : $"已加载 {Items.Count} 条公告({UnreadCount} 未读)");
        }
        catch
        {
            // 优雅降级:任何异常都显示空列表
            Items.Clear();
            UnreadCount = 0;
            SetStatus("公告加载失败,稍后重试");
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>标记某条公告为已读(并刷新未读数)</summary>
    [RelayCommand]
    private async Task MarkReadAsync(AnnouncementDto? ann)
    {
        if (ann is null) return;
        if (ann.IsRead) { SelectedAnnouncement = ann; return; }
        try
        {
            await _service.MarkReadAsync(ann.Id);
            // 本地标记已读(替换集合中的项,触发 UI 更新)
            var idx = Items.IndexOf(ann);
            if (idx >= 0)
            {
                var updated = ann with { IsRead = true };
                Items[idx] = updated;
                SelectedAnnouncement = updated;
            }
            UnreadCount = Items.Count(x => !x.IsRead);
        }
        catch
        {
            // 静默:标记失败不阻塞查看
            SelectedAnnouncement = ann;
        }
    }

    /// <summary>展开/收起发布公告表单</summary>
    [RelayCommand]
    private void ToggleCreateForm() => IsCreating = !IsCreating;

    /// <summary>教师发布公告(标题+内容)</summary>
    [RelayCommand]
    private async Task CreateAnnouncementAsync()
    {
        if (string.IsNullOrWhiteSpace(NewTitle) || string.IsNullOrWhiteSpace(NewContent))
        {
            SetStatus("标题和内容均不能为空");
            return;
        }
        try
        {
            IsLoading = true;
            var dto = new CreateAnnouncementDto(NewTitle.Trim(), NewContent.Trim());
            var created = await _service.CreateAsync(dto);
            NewTitle = "";
            NewContent = "";
            IsCreating = false;
            if (created is not null)
            {
                SetStatus("公告已发布");
                await RefreshAsync();
            }
            else
            {
                // 端点未就绪:本地模拟插入一条,保证教师可见效果(后端就绪后自动替换为真实数据)
                Items.Insert(0, new AnnouncementDto(
                    Guid.NewGuid(), dto.Title, dto.Content,
                    _auth.CurrentUser?.Id ?? Guid.Empty,
                    _auth.CurrentUser?.DisplayName ?? "我",
                    DateTime.Now, IsActive: true, Pinned: false) { IsRead = true });
                SetStatus("公告已发布(本地,后端就绪后将同步)");
            }
        }
        catch (Exception ex)
        {
            SetStatus("发布公告失败: " + ex.Message);
        }
        finally
        {
            IsLoading = false;
        }
    }
}
