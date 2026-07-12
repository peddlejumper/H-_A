using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 博客/知识分享 ViewModel:文章列表 + 查看正文 + 发布 + 点赞。
/// 作为独立页面路由展示( MainWindow 顶部 ⋯ 菜单 / MainIdeView ⋯ 菜单「知识广场」入口)。
/// 后端端点未就绪时所有操作优雅降级(空列表/"暂无文章"),绝不崩溃。
/// </summary>
public partial class BlogViewModel : ViewModelBase
{
    private readonly BlogService _service;

    /// <summary>文章列表</summary>
    public ObservableCollection<BlogPostListItemDto> Posts { get; } = new();

    /// <summary>选中文章的详情(含正文)</summary>
    [ObservableProperty]
    private BlogPostDto? _detail;

    [ObservableProperty]
    private BlogPostListItemDto? _selectedPost;

    [ObservableProperty]
    private bool _isLoading;

    [ObservableProperty]
    private bool _isPosting;

    /// <summary>是否展开发布文章表单</summary>
    [ObservableProperty]
    private bool _isCreating;

    /// <summary>列表区状态提示</summary>
    [ObservableProperty]
    private string? _statusHint;

    // ── 发布表单字段 ──
    [ObservableProperty] private string _newTitle = "";
    [ObservableProperty] private string _newSummary = "";
    [ObservableProperty] private string _newContent = "";
    [ObservableProperty] private string _newTags = "";

    public BlogViewModel(BlogService service)
    {
        _service = service;
        _ = RefreshAsync();
    }

    /// <summary>拉取文章列表。</summary>
    [RelayCommand]
    public async Task RefreshAsync()
    {
        try
        {
            IsLoading = true;
            StatusHint = "加载文章…";
            var result = await _service.ListAsync(1, 30);
            Posts.Clear();
            if (result?.Items is { } items)
                foreach (var p in items) Posts.Add(p);
            StatusHint = Posts.Count > 0 ? $"共 {Posts.Count} 篇文章" : "暂无文章,来写第一篇吧";
            SetStatus($"文章列表已加载({Posts.Count} 篇)");
        }
        catch (Exception ex)
        {
            StatusHint = "加载文章失败: " + ex.Message;
            SetStatus("文章列表加载失败");
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>选中某篇文章 → 加载正文详情。</summary>
    [RelayCommand]
    private async Task SelectPostAsync(BlogPostListItemDto? post)
    {
        if (post is null) { Detail = null; return; }
        SelectedPost = post;
        Detail = null;
        try
        {
            Detail = await _service.GetAsync(post.Id);
        }
        catch
        {
            Detail = null;
        }
    }

    /// <summary>展开/收起发布文章表单</summary>
    [RelayCommand]
    private void ToggleCreateForm() => IsCreating = !IsCreating;

    /// <summary>发布文章(标题/摘要/正文/标签)。</summary>
    [RelayCommand]
    private async Task CreatePostAsync()
    {
        if (string.IsNullOrWhiteSpace(NewTitle) || string.IsNullOrWhiteSpace(NewContent))
        {
            StatusHint = "标题和正文均不能为空"; return;
        }
        try
        {
            IsPosting = true;
            var tags = NewTags.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            var dto = new CreateBlogPostDto(NewTitle.Trim(),
                string.IsNullOrWhiteSpace(NewSummary) ? "" : NewSummary.Trim(),
                NewContent.Trim(), tags);
            var created = await _service.CreateAsync(dto);
            NewTitle = "";
            NewSummary = "";
            NewContent = "";
            NewTags = "";
            IsCreating = false;
            if (created is not null)
            {
                SetStatus("文章已发布");
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

    /// <summary>点赞文章(幂等),本地 +1。</summary>
    [RelayCommand]
    private async Task LikeAsync(BlogPostListItemDto? post)
    {
        if (post is null) return;
        try
        {
            var ok = await _service.LikeAsync(post.Id);
            if (ok)
            {
                var idx = Posts.IndexOf(post);
                if (idx >= 0)
                    Posts[idx] = post with { LikeCount = post.LikeCount + 1 };
                if (Detail?.Id == post.Id)
                    Detail = Detail with { LikeCount = Detail.LikeCount + 1 };
                SetStatus("已点赞");
            }
        }
        catch (Exception ex)
        {
            SetStatus("点赞失败: " + ex.Message);
        }
    }

    /// <summary>返回 IDE。</summary>
    [RelayCommand]
    private void BackToIde() => NavigateTo(null!);
}
