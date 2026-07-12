using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// 博客/知识分享 API(后端扩展端点)。
/// GET /api/v1/blog、GET /api/v1/blog/{id}、POST /api/v1/blog、POST /api/v1/blog/{id}/like。
/// 后端未就绪时所有方法 try/catch 返回空/默认,绝不抛出导致 UI 崩溃。
/// </summary>
public sealed class BlogService
{
    private readonly ApiClient _api;
    public BlogService(ApiClient api) => _api = api;

    /// <summary>博客文章列表(分页)。端点未就绪返回 null。</summary>
    public async Task<PagedResult<BlogPostListItemDto>?> ListAsync(int page = 1, int pageSize = 20, CancellationToken ct = default)
    {
        try
        {
            return await _api.GetAsync<PagedResult<BlogPostListItemDto>>($"/api/v1/blog?page={page}&pageSize={pageSize}", ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>文章详情(含正文)。端点未就绪返回 null。</summary>
    public async Task<BlogPostDto?> GetAsync(Guid id, CancellationToken ct = default)
    {
        try
        {
            return await _api.GetAsync<BlogPostDto>($"/api/v1/blog/{id}", ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>发布文章。返回创建后的 DTO;端点未就绪返回 null。</summary>
    public async Task<BlogPostDto?> CreateAsync(CreateBlogPostDto dto, CancellationToken ct = default)
    {
        try
        {
            return await _api.PostAsync<CreateBlogPostDto, BlogPostDto>("/api/v1/blog", dto, ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>点赞文章(幂等)。返回是否请求成功;端点未就绪返回 false。</summary>
    public async Task<bool> LikeAsync(Guid id, CancellationToken ct = default)
    {
        try
        {
            await _api.PostAsync<object, object>($"/api/v1/blog/{id}/like", new { }, ct);
            return true;
        }
        catch (ApiException)
        {
            return false;
        }
    }
}
