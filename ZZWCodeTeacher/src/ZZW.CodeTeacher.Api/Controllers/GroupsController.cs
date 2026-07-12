namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// 班级/小组 API —— 教师创建班级,学员凭邀请码加入。
/// 班长(Owner)可查看成员、移除成员,并复用单学员进度接口查看组内进度。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/groups")]
[Authorize]
[Produces("application/json")]
public class GroupsController(IMediator mediator) : ControllerBase
{
    /// <summary>创建班级(创建者自动成为 Owner)</summary>
    [HttpPost]
    [ProducesResponseType(typeof(GroupDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<GroupDto>> Create([FromBody] CreateGroupDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(new CreateGroupCommand(dto.Name, dto.Description), ct);
        return Ok(result);
    }

    /// <summary>列出我的班级</summary>
    [HttpGet]
    [ProducesResponseType(typeof(IReadOnlyList<GroupDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<GroupDto>>> ListMine(CancellationToken ct)
    {
        var result = await mediator.Send(new ListMyGroupsQuery(), ct);
        return Ok(result);
    }

    /// <summary>凭邀请码加入班级(成为 Member)</summary>
    [HttpPost("join")]
    [ProducesResponseType(typeof(GroupDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<GroupDto>> Join([FromBody] JoinGroupDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(new JoinGroupCommand(dto.InviteCode), ct);
        return Ok(result);
    }

    /// <summary>列出班级成员</summary>
    [HttpGet("{id:guid}/members")]
    [ProducesResponseType(typeof(IReadOnlyList<GroupMemberDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<GroupMemberDto>>> ListMembers(Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(new ListGroupMembersQuery(id), ct);
        return Ok(result);
    }

    /// <summary>移除班级成员(仅 Owner 可调)</summary>
    [HttpDelete("{id:guid}/members/{userId:guid}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    public async Task<IActionResult> RemoveMember(Guid id, Guid userId, CancellationToken ct)
    {
        await mediator.Send(new RemoveGroupMemberCommand(id, userId), ct);
        return NoContent();
    }
}
