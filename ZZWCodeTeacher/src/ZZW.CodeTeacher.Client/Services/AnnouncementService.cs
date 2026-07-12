using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// 教师公告 API(后端扩展端点)。
/// 端点假设:GET /api/v1/announcements、POST /api/v1/announcements、POST /api/v1/announcements/{id}/read。
/// 后端未就绪时所有方法 try/catch 返回空/默认,绝不抛出导致 UI 崩溃。
/// </summary>
public sealed class AnnouncementService
{
    private readonly ApiClient _api;
    public AnnouncementService(ApiClient api) => _api = api;

    /// <summary>公告列表(activeOnly=true 仅返回生效中)。端点未就绪返回空列表。</summary>
    public async Task<IReadOnlyList<AnnouncementDto>> ListAsync(bool activeOnly = true, CancellationToken ct = default)
    {
        try
        {
            var page = await _api.GetAsync<PagedResult<AnnouncementDto>>(
                $"/api/v1/announcements?activeOnly={activeOnly.ToString().ToLowerInvariant()}&pageSize=50", ct);
            return page?.Items ?? Array.Empty<AnnouncementDto>();
        }
        catch (ApiException)
        {
            // 端点未就绪(404/401 等):优雅降级,返回空集合
            return Array.Empty<AnnouncementDto>();
        }
    }

    /// <summary>教师发布公告。返回创建后的 DTO;端点未就绪返回 null。</summary>
    public async Task<AnnouncementDto?> CreateAsync(CreateAnnouncementDto dto, CancellationToken ct = default)
    {
        try
        {
            return await _api.PostAsync<CreateAnnouncementDto, AnnouncementDto>("/api/v1/announcements", dto, ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>标记公告为已读(幂等)。端点未就绪静默忽略。</summary>
    public async Task MarkReadAsync(Guid id, CancellationToken ct = default)
    {
        try
        {
            await _api.PostAsync<object, object>($"/api/v1/announcements/{id}/read", new { }, ct);
        }
        catch (ApiException)
        {
            // 端点未就绪:静默忽略,不阻塞 UI
        }
    }
}
