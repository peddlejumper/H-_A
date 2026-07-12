namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// 讨论区 API —— 题目讨论帖与回复。
/// 路由分两段:题目下的讨论列表 /api/v1/problems/{problemId}/discussions;
/// 讨论下的回复 /api/v1/discussions/{id}/replies。
/// UserId 从登录态(JWT Claims)经 ICurrentUser 获取。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}")]
[Authorize]
[Produces("application/json")]
public class DiscussionsController(IMediator mediator) : ControllerBase
{
    /// <summary>分页查询某题目的讨论列表</summary>
    [HttpGet("problems/{problemId:guid}/discussions")]
    [ProducesResponseType(typeof(PagedResult<DiscussionListItemDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<DiscussionListItemDto>>> ListByProblem(
        Guid problemId, [FromQuery] int page = 1, [FromQuery] int pageSize = 20,
        CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListDiscussionsQuery(problemId, page, pageSize), ct);
        return Ok(result);
    }

    /// <summary>创建讨论</summary>
    [HttpPost("problems/{problemId:guid}/discussions")]
    [ProducesResponseType(typeof(DiscussionDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<DiscussionDto>> Create(
        Guid problemId, [FromBody] CreateDiscussionDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(
            new CreateDiscussionCommand(problemId, dto.Title, dto.Content), ct);
        return Ok(result);
    }

    /// <summary>查询某讨论的回复列表(按时间正序)</summary>
    [HttpGet("discussions/{id:guid}/replies")]
    [ProducesResponseType(typeof(IReadOnlyList<DiscussionReplyDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<DiscussionReplyDto>>> ListReplies(
        Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(new ListRepliesQuery(id), ct);
        return Ok(result);
    }

    /// <summary>创建回复</summary>
    [HttpPost("discussions/{id:guid}/replies")]
    [ProducesResponseType(typeof(DiscussionReplyDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<DiscussionReplyDto>> CreateReply(
        Guid id, [FromBody] CreateReplyDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(new CreateReplyCommand(id, dto.Content), ct);
        return Ok(result);
    }
}
