using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// AI 题目推荐 API(后端扩展端点)。
/// GET /api/v1/recommendations/problems?limit=5 → RecommendedProblemDto 列表。
/// 后端未就绪时 try/catch 返回空集合,绝不抛出导致 UI 崩溃。
/// </summary>
public sealed class RecommendationService
{
    private readonly ApiClient _api;
    public RecommendationService(ApiClient api) => _api = api;

    /// <summary>获取 AI 推荐题目(默认 5 道,含推荐理由)。端点未就绪返回空集合。</summary>
    public async Task<IReadOnlyList<RecommendedProblemDto>> GetRecommendedAsync(int limit = 5, CancellationToken ct = default)
    {
        try
        {
            var list = await _api.GetAsync<IReadOnlyList<RecommendedProblemDto>>($"/api/v1/recommendations/problems?limit={limit}", ct);
            return list ?? Array.Empty<RecommendedProblemDto>();
        }
        catch (ApiException)
        {
            return Array.Empty<RecommendedProblemDto>();
        }
    }
}
