using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 班级/小组管理 ViewModel:我的班级列表 + 创建班级 + 加入班级 + 成员列表 + 移除成员 + 查看成员进度。
/// 作为教师后台第 4 个 Tab 的内容;学员加入班级由 MainIdeView ⋯ 菜单弹窗处理(直接调 GroupService)。
/// 后端端点未就绪时所有操作优雅降级(空列表/"暂无班级"),绝不崩溃。
/// </summary>
public partial class GroupManagementViewModel : ViewModelBase
{
    private readonly GroupService _service;
    private readonly AuthState _auth;

    /// <summary>我的班级列表</summary>
    public ObservableCollection<GroupDto> Groups { get; } = new();

    /// <summary>选中班级的成员列表</summary>
    public ObservableCollection<GroupMemberDto> Members { get; } = new();

    [ObservableProperty]
    private GroupDto? _selectedGroup;

    /// <summary>当前选中的成员(用于显示进度详情)</summary>
    [ObservableProperty]
    private GroupMemberDto? _selectedMember;

    /// <summary>成员进度详情 VM(选中成员后加载)</summary>
    [ObservableProperty]
    private UserProgressViewModel? _memberProgress;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private string? _statusHint;

    // ── 创建班级表单 ──
    [ObservableProperty] private string _newGroupName = "";
    [ObservableProperty] private string _newGroupDesc = "";

    /// <summary>当前用户是否为教师/管理员(控制"创建班级"入口可见性)</summary>
    [ObservableProperty]
    private bool _isTeacher;

    public GroupManagementViewModel(GroupService service, AuthState auth, UserProgressViewModel memberProgress)
    {
        _service = service;
        _auth = auth;
        MemberProgress = memberProgress;
        _auth.Changed += (_, _) => SyncRole();
        SyncRole();
    }

    private void SyncRole()
        => IsTeacher = _auth.CurrentUser?.Role == UserRole.Teacher
                    || _auth.CurrentUser?.Role == UserRole.Admin;

    /// <summary>拉取我的班级列表。</summary>
    [RelayCommand]
    public async Task RefreshAsync()
    {
        try
        {
            IsLoading = true;
            StatusHint = "加载班级…";
            var list = await _service.ListMyAsync();
            Groups.Clear();
            foreach (var g in list) Groups.Add(g);
            StatusHint = Groups.Count > 0 ? $"共 {Groups.Count} 个班级" : "暂无班级,创建或加入一个吧";
            SetStatus($"班级列表已加载({Groups.Count} 个)");
        }
        catch (Exception ex)
        {
            StatusHint = "加载班级失败: " + ex.Message;
            SetStatus("班级列表加载失败");
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>选中某班级 → 加载成员列表。</summary>
    [RelayCommand]
    private async Task SelectGroupAsync(GroupDto? group)
    {
        if (group is null) return;
        SelectedGroup = group;
        Members.Clear();
        SelectedMember = null;
        try
        {
            var members = await _service.GetMembersAsync(group.Id);
            foreach (var m in members) Members.Add(m);
            SetStatus($"「{group.Name}」成员 {Members.Count} 人");
        }
        catch (Exception ex)
        {
            StatusHint = "成员加载失败: " + ex.Message;
        }
    }

    /// <summary>选中某成员 → 加载其进度详情(显示在右侧面板)。</summary>
    partial void OnSelectedMemberChanged(GroupMemberDto? value)
    {
        if (value is not null && MemberProgress is not null)
            _ = MemberProgress.LoadAsync(value.UserId);
    }

    /// <summary>创建班级(教师/管理员)。</summary>
    [RelayCommand]
    private async Task CreateAsync()
    {
        if (string.IsNullOrWhiteSpace(NewGroupName))
        {
            StatusHint = "班级名称不能为空"; return;
        }
        try
        {
            IsLoading = true;
            var dto = new CreateGroupDto(NewGroupName.Trim(), NewGroupDesc.Trim());
            var created = await _service.CreateAsync(dto);
            NewGroupName = "";
            NewGroupDesc = "";
            if (created is not null)
            {
                SetStatus($"班级「{created.Name}」已创建,邀请码: {created.InviteCode}");
                await RefreshAsync();
            }
            else
            {
                StatusHint = "创建失败(后端可能未就绪)";
            }
        }
        catch (Exception ex)
        {
            StatusHint = "创建班级失败: " + ex.Message;
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>移除班级成员(教师/创建者)。</summary>
    [RelayCommand]
    private async Task RemoveMemberAsync(GroupMemberDto? member)
    {
        if (member is null || SelectedGroup is null) return;
        try
        {
            await _service.RemoveMemberAsync(SelectedGroup.Id, member.UserId);
            Members.Remove(member);
            if (SelectedMember == member) SelectedMember = null;
            SetStatus($"已移除成员 {member.Username}");
        }
        catch (Exception ex)
        {
            StatusHint = "移除成员失败: " + ex.Message;
        }
    }
}
