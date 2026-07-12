using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// 知识点图谱 API(后端扩展端点)。
/// GET /api/v1/knowledge-points(树)、POST /api/v1/knowledge-points、
/// POST /api/v1/knowledge-points/link、GET /api/v1/knowledge-points/{id}/problems。
/// 后端未就绪时所有方法 try/catch 返回空/默认,绝不抛出导致 UI 崩溃。
/// </summary>
public sealed class KnowledgePointService
{
    private readonly ApiClient _api;
    public KnowledgePointService(ApiClient api) => _api = api;

    /// <summary>知识点树(顶层节点列表,Children 递归)。端点未就绪返回空集合。</summary>
    public async Task<IReadOnlyList<KnowledgePointDto>> GetTreeAsync(CancellationToken ct = default)
    {
        try
        {
            var list = await _api.GetAsync<IReadOnlyList<KnowledgePointDto>>("/api/v1/knowledge-points", ct);
            return list ?? Array.Empty<KnowledgePointDto>();
        }
        catch (ApiException)
        {
            return Array.Empty<KnowledgePointDto>();
        }
    }

    /// <summary>创建知识点。端点未就绪静默忽略。</summary>
    public async Task<KnowledgePointDto?> CreateAsync(CreateKnowledgePointDto dto, CancellationToken ct = default)
    {
        try
        {
            return await _api.PostAsync<CreateKnowledgePointDto, KnowledgePointDto>("/api/v1/knowledge-points", dto, ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>关联题目与知识点。端点未就绪静默忽略。</summary>
    public async Task LinkAsync(Guid problemId, Guid kpId, CancellationToken ct = default)
    {
        try
        {
            await _api.PostAsync<LinkProblemKnowledgePointDto, object>("/api/v1/knowledge-points/link",
                new LinkProblemKnowledgePointDto(problemId, kpId), ct);
        }
        catch (ApiException)
        {
            // 端点未就绪:静默忽略
        }
    }

    /// <summary>某知识点下的题目列表。端点未就绪返回空集合。</summary>
    public async Task<IReadOnlyList<ProblemListItemDto>> GetProblemsAsync(Guid kpId, CancellationToken ct = default)
    {
        try
        {
            var list = await _api.GetAsync<IReadOnlyList<ProblemListItemDto>>($"/api/v1/knowledge-points/{kpId}/problems", ct);
            return list ?? Array.Empty<ProblemListItemDto>();
        }
        catch (ApiException)
        {
            return Array.Empty<ProblemListItemDto>();
        }
    }
}
