using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// 班级/小组 API(后端扩展端点)。
/// POST /api/v1/groups、GET /api/v1/groups、POST /api/v1/groups/join、
/// GET /api/v1/groups/{id}/members、DELETE /api/v1/groups/{id}/members/{userId}。
/// 后端未就绪时所有方法 try/catch 返回空/默认,绝不抛出导致 UI 崩溃。
/// </summary>
public sealed class GroupService
{
    private readonly ApiClient _api;
    public GroupService(ApiClient api) => _api = api;

    /// <summary>创建班级。返回创建后的 DTO;端点未就绪返回 null。</summary>
    public async Task<GroupDto?> CreateAsync(CreateGroupDto dto, CancellationToken ct = default)
    {
        try
        {
            return await _api.PostAsync<CreateGroupDto, GroupDto>("/api/v1/groups", dto, ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>我加入/创建的班级列表。端点未就绪返回空集合。</summary>
    public async Task<IReadOnlyList<GroupDto>> ListMyAsync(CancellationToken ct = default)
    {
        try
        {
            var page = await _api.GetAsync<PagedResult<GroupDto>>("/api/v1/groups?page=1&pageSize=100", ct);
            return page?.Items ?? Array.Empty<GroupDto>();
        }
        catch (ApiException)
        {
            return Array.Empty<GroupDto>();
        }
    }

    /// <summary>通过邀请码加入班级。返回该班级 DTO;端点未就绪/码无效返回 null。</summary>
    public async Task<GroupDto?> JoinAsync(string inviteCode, CancellationToken ct = default)
    {
        try
        {
            return await _api.PostAsync<JoinGroupDto, GroupDto>("/api/v1/groups/join", new JoinGroupDto(inviteCode), ct);
        }
        catch (ApiException)
        {
            return null;
        }
    }

    /// <summary>班级成员列表。端点未就绪返回空集合。</summary>
    public async Task<IReadOnlyList<GroupMemberDto>> GetMembersAsync(Guid groupId, CancellationToken ct = default)
    {
        try
        {
            var page = await _api.GetAsync<PagedResult<GroupMemberDto>>($"/api/v1/groups/{groupId}/members?page=1&pageSize=200", ct);
            return page?.Items ?? Array.Empty<GroupMemberDto>();
        }
        catch (ApiException)
        {
            return Array.Empty<GroupMemberDto>();
        }
    }

    /// <summary>移除班级成员。端点未就绪静默忽略。</summary>
    public async Task RemoveMemberAsync(Guid groupId, Guid userId, CancellationToken ct = default)
    {
        try
        {
            await _api.DeleteAsync($"/api/v1/groups/{groupId}/members/{userId}", ct);
        }
        catch (ApiException)
        {
            // 端点未就绪:静默忽略
        }
    }
}
