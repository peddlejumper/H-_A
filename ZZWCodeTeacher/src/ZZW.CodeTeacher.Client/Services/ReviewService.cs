using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// SM-2 错题复习 API(后端扩展端点)。
/// GET /api/v1/reviews/due、POST /api/v1/reviews/{problemId}(body: { quality: 0-5 })。
/// 后端未就绪时所有方法 try/catch 返回空/默认,绝不抛出导致 UI 崩溃。
/// </summary>
public sealed class ReviewService
{
    private readonly ApiClient _api;
    public ReviewService(ApiClient api) => _api = api;

    /// <summary>今日待复习项列表。端点未就绪返回空集合。</summary>
    public async Task<IReadOnlyList<ReviewItemDto>> GetDueAsync(CancellationToken ct = default)
    {
        try
        {
            var page = await _api.GetAsync<PagedResult<ReviewItemDto>>("/api/v1/reviews/due?page=1&pageSize=100", ct);
            return page?.Items ?? Array.Empty<ReviewItemDto>();
        }
        catch (ApiException)
        {
            return Array.Empty<ReviewItemDto>();
        }
    }

    /// <summary>提交复习评分(quality 0~5),更新 SM-2 调度。端点未就绪静默忽略。</summary>
    public async Task ScheduleAsync(Guid problemId, int quality, CancellationToken ct = default)
    {
        try
        {
            await _api.PostAsync<ScheduleReviewDto, object>($"/api/v1/reviews/{problemId}", new ScheduleReviewDto(quality), ct);
        }
        catch (ApiException)
        {
            // 端点未就绪:静默忽略,不阻塞 UI
        }
    }
}
