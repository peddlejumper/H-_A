namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;
using ZZW.CodeTeacher.Domain.Enums;

/// <summary>
/// 提交与评测 API。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/submissions")]
[Produces("application/json")]
public class SubmissionsController(IMediator mediator) : ControllerBase
{
    /// <summary>提交代码</summary>
    [HttpPost]
    [Authorize]
    [ProducesResponseType(typeof(SubmissionDto), StatusCodes.Status201Created)]
    public async Task<ActionResult<SubmissionDto>> Submit([FromBody] SubmitCodeDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(new SubmitCodeCommand(dto.ProblemId, dto.Code, dto.Language), ct);
        return CreatedAtAction(nameof(GetById), new { id = result.Id }, result);
    }

    /// <summary>获取提交详情</summary>
    [HttpGet("{id:guid}")]
    [Authorize]
    [ProducesResponseType(typeof(SubmissionDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<SubmissionDto>> GetById(Guid id, CancellationToken ct)
    {
        var sub = await mediator.Send(new GetSubmissionByIdQuery(id), ct);
        return sub is null ? NotFound() : Ok(sub);
    }

    /// <summary>查询某用户的提交记录</summary>
    [HttpGet("user/{userId:guid}")]
    [Authorize]
    [ProducesResponseType(typeof(PagedResult<SubmissionDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<SubmissionDto>>> ListByUser(
        Guid userId, [FromQuery] int page = 1, [FromQuery] int pageSize = 20, CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListSubmissionsByUserQuery(userId, page, pageSize), ct);
        return Ok(result);
    }

    /// <summary>查询某用户的错题本(未通过的提交,按题目去重)</summary>
    [HttpGet("user/{userId:guid}/wrong")]
    [Authorize]
    [ProducesResponseType(typeof(PagedResult<SubmissionDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<SubmissionDto>>> ListWrong(
        Guid userId, [FromQuery] int page = 1, [FromQuery] int pageSize = 50, CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListWrongSubmissionsQuery(userId, page, pageSize), ct);
        return Ok(result);
    }

    /// <summary>查询全部提交（教师/管理员）</summary>
    [HttpGet]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(typeof(PagedResult<SubmissionDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<SubmissionDto>>> ListAll(
        [FromQuery] int page = 1, [FromQuery] int pageSize = 20,
        [FromQuery] SubmissionStatus? status = null, CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListAllSubmissionsQuery(page, pageSize, status), ct);
        return Ok(result);
    }

    /// <summary>重新评测（教师/管理员）</summary>
    [HttpPost("{id:guid}/rejudge")]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(typeof(SubmissionDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<SubmissionDto>> Rejudge(Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(new RejudgeCommand(id), ct);
        return Ok(result);
    }
}
