using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// 单学员进度 API(后端扩展端点)。
/// GET /api/v1/users/{userId}/progress → UserProgressDto。
/// 后端未就绪时 try/catch 返回 null,绝不抛出导致 UI 崩溃。
/// </summary>
public sealed class ProgressService
{
    private readonly ApiClient _api;
    public ProgressService(ApiClient api) => _api = api;

    /// <summary>查询某学员的学习进度详情。端点未就绪返回 null。</summary>
    public async Task<UserProgressDto?> GetAsync(Guid userId, CancellationToken ct = default)
    {
        try
        {
            return await _api.GetAsync<UserProgressDto>($"/api/v1/users/{userId}/progress", ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }
}
