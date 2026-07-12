using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 讨论区 ViewModel:某题的讨论列表 + 查看回复 + 发新帖 + 回复。
/// 当前题目 Id 由 MainIdeViewModel 在切题时通过 <see cref="SetProblem"/> 传入。
/// </summary>
public partial class DiscussionViewModel : ViewModelBase
{
    private readonly CommunityService _community;
    private Guid _currentProblemId;

    /// <summary>当前题目的讨论列表</summary>
    public ObservableCollection<DiscussionListItemDto> Discussions { get; } = new();

    /// <summary>选中讨论的回复列表</summary>
    public ObservableCollection<DiscussionReplyDto> Replies { get; } = new();

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(CreateReplyCommand))]
    private DiscussionListItemDto? _selectedDiscussion;

    /// <summary>新帖标题输入</summary>
    [ObservableProperty]
    private string _newDiscussionTitle = "";

    /// <summary>新帖内容输入</summary>
    [ObservableProperty]
    private string _newDiscussionContent = "";

    /// <summary>回复内容输入</summary>
    [ObservableProperty]
    private string _replyContent = "";

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private bool _isPosting;

    /// <summary>列表区状态提示(如"共 N 条讨论" / 错误信息)</summary>
    [ObservableProperty]
    private string? _statusHint;

    public DiscussionViewModel(CommunityService community)
    {
        _community = community;
    }

    /// <summary>切题时调用:记录当前题目并刷新讨论列表,清空回复。</summary>
    public void SetProblem(Guid problemId)
    {
        _currentProblemId = problemId;
        SelectedDiscussion = null;
        Replies.Clear();
        _ = RefreshDiscussionsCommand.ExecuteAsync(problemId);
    }

    /// <summary>拉取某题的讨论列表。</summary>
    [RelayCommand]
    public async Task RefreshDiscussionsAsync(Guid problemId)
    {
        try
        {
            IsLoading = true;
            StatusHint = "加载讨论…";
            Discussions.Clear();
            var result = await _community.ListDiscussionsAsync(problemId);
            if (result?.Items is { } items)
                foreach (var d in items) Discussions.Add(d);
            StatusHint = Discussions.Count > 0 ? $"共 {Discussions.Count} 条讨论" : "暂无讨论,发第一条吧";
            SetStatus($"讨论区已加载({Discussions.Count} 条)");
        }
        catch (Exception ex)
        {
            StatusHint = "加载讨论失败: " + ex.Message;
            SetStatus("讨论加载失败");
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>刷新当前题目的讨论列表(供刷新按钮调用,无参)。</summary>
    [RelayCommand]
    private async Task RefreshCurrentAsync()
    {
        if (_currentProblemId != Guid.Empty)
            await RefreshDiscussionsAsync(_currentProblemId);
    }

    /// <summary>在某题下发起新讨论。</summary>
    [RelayCommand]
    private async Task CreateDiscussionAsync()
    {
        if (_currentProblemId == Guid.Empty)
        {
            StatusHint = "请先选择一道题目"; return;
        }
        if (string.IsNullOrWhiteSpace(NewDiscussionTitle))
        {
            StatusHint = "请填写标题"; return;
        }
        try
        {
            IsPosting = true;
            var dto = new CreateDiscussionDto(NewDiscussionTitle.Trim(), NewDiscussionContent.Trim());
            var created = await _community.CreateDiscussionAsync(_currentProblemId, dto);
            if (created is not null)
            {
                NewDiscussionTitle = "";
                NewDiscussionContent = "";
                await RefreshDiscussionsAsync(_currentProblemId);
                SetStatus("讨论发布成功");
            }
        }
        catch (Exception ex)
        {
            StatusHint = "发布失败: " + ex.Message;
            SetStatus("讨论发布失败");
        }
        finally
        {
            IsPosting = false;
        }
    }

    /// <summary>选中某条讨论并加载其回复。</summary>
    [RelayCommand]
    private async Task SelectDiscussionAsync(DiscussionListItemDto? discussion)
    {
        if (discussion is null) return;
        SelectedDiscussion = discussion;
        Replies.Clear();
        try
        {
            var result = await _community.ListRepliesAsync(discussion.Id);
            if (result?.Items is { } items)
                foreach (var r in items) Replies.Add(r);
            SetStatus($"已加载「{discussion.Title}」的 {Replies.Count} 条回复");
        }
        catch (Exception ex)
        {
            SetStatus("加载回复失败: " + ex.Message);
        }
    }

    /// <summary>在选中讨论下发表回复(需先选中讨论)。</summary>
    [RelayCommand(CanExecute = nameof(CanCreateReply))]
    private async Task CreateReplyAsync()
    {
        if (SelectedDiscussion is null) return;
        if (string.IsNullOrWhiteSpace(ReplyContent))
        {
            StatusHint = "请输入回复内容"; return;
        }
        try
        {
            IsPosting = true;
            var created = await _community.CreateReplyAsync(SelectedDiscussion.Id, new CreateReplyDto(ReplyContent.Trim()));
            if (created is not null)
            {
                ReplyContent = "";
                // 刷新回复列表与讨论列表(更新回复数)
                await SelectDiscussionAsync(SelectedDiscussion);
                await RefreshDiscussionsAsync(_currentProblemId);
                SetStatus("回复成功");
            }
        }
        catch (Exception ex)
        {
            StatusHint = "回复失败: " + ex.Message;
            SetStatus("回复失败");
        }
        finally
        {
            IsPosting = false;
        }
    }

    private bool CanCreateReply() => SelectedDiscussion is not null;
}
