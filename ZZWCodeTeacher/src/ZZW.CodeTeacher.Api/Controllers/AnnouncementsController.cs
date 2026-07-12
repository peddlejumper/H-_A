namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// 教师公告 API —— 教师发布、学员接收通知。
/// 学员仅看 active 公告,教师/管理员可看全部;创建/删除需教师角色。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/announcements")]
[Authorize]
[Produces("application/json")]
public class AnnouncementsController(IMediator mediator) : ControllerBase
{
    /// <summary>分页查询公告列表(学员看 active,教师看全部;支持 activeOnly 查询参数)</summary>
    [HttpGet]
    [ProducesResponseType(typeof(PagedResult<AnnouncementListItemDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<AnnouncementListItemDto>>> List(
        [FromQuery] bool activeOnly = false, [FromQuery] int page = 1, [FromQuery] int pageSize = 20,
        CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListAnnouncementsQuery(activeOnly, page, pageSize), ct);
        return Ok(result);
    }

    /// <summary>创建公告(仅教师/管理员)</summary>
    [HttpPost]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(typeof(AnnouncementDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<AnnouncementDto>> Create([FromBody] CreateAnnouncementDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(new CreateAnnouncementCommand(dto.Title, dto.Content, dto.Pinned), ct);
        return Ok(result);
    }

    /// <summary>标记公告已读(幂等)</summary>
    [HttpPost("{id:guid}/read")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> MarkRead(Guid id, CancellationToken ct)
    {
        await mediator.Send(new MarkAnnouncementReadCommand(id), ct);
        return NoContent();
    }

    /// <summary>删除公告(仅教师/管理员)</summary>
    [HttpDelete("{id:guid}")]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> Delete(Guid id, CancellationToken ct)
    {
        await mediator.Send(new DeleteAnnouncementCommand(id), ct);
        return NoContent();
    }
}
