using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// 题解 API(后端扩展端点)。
/// GET /api/v1/problems/{problemId}/solutions、POST .../solutions、
/// GET /api/v1/solutions/{id}、POST .../like、POST .../accept。
/// 后端未就绪时所有方法 try/catch 返回空/默认,绝不抛出导致 UI 崩溃。
/// </summary>
public sealed class SolutionService
{
    private readonly ApiClient _api;
    public SolutionService(ApiClient api) => _api = api;

    /// <summary>某题的题解列表(分页 + 排序 hot/new/accepted)。端点未就绪返回 null。</summary>
    public async Task<PagedResult<SolutionListItemDto>?> ListAsync(Guid problemId, int page = 1, string sort = "hot", CancellationToken ct = default)
    {
        try
        {
            return await _api.GetAsync<PagedResult<SolutionListItemDto>>(
                $"/api/v1/problems/{problemId}/solutions?page={page}&pageSize=50&sort={Uri.EscapeDataString(sort)}", ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>题解详情(含正文/代码)。端点未就绪返回 null。</summary>
    public async Task<SolutionDto?> GetAsync(Guid id, CancellationToken ct = default)
    {
        try
        {
            return await _api.GetAsync<SolutionDto>($"/api/v1/solutions/{id}", ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>在某题下发布题解。返回创建后的 DTO;端点未就绪返回 null。</summary>
    public async Task<SolutionDto?> CreateAsync(Guid problemId, CreateSolutionDto dto, CancellationToken ct = default)
    {
        try
        {
            return await _api.PostAsync<CreateSolutionDto, SolutionDto>($"/api/v1/problems/{problemId}/solutions", dto, ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>切换点赞(幂等 toggle)。返回 {Liked, LikeCount};端点未就绪返回 null。</summary>
    public async Task<ToggleLikeResultDto?> ToggleLikeAsync(Guid id, CancellationToken ct = default)
    {
        try
        {
            return await _api.PostAsync<object, ToggleLikeResultDto>($"/api/v1/solutions/{id}/like", new { }, ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>采纳题解(教师/作者)。端点未就绪静默忽略。</summary>
    public async Task AcceptAsync(Guid id, CancellationToken ct = default)
    {
        try
        {
            await _api.PostAsync<object, object>($"/api/v1/solutions/{id}/accept", new { }, ct);
        }
        catch (ApiException)
        {
            // 端点未就绪:静默忽略,不阻塞 UI
        }
    }
}
