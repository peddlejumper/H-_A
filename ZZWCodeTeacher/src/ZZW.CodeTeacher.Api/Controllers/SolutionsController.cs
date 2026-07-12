namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// 题解 API —— 题目下的解答分享,支持点赞与采纳。
/// 路由分两段:题目下的题解列表 /api/v1/problems/{problemId}/solutions;
/// 题解详情/点赞/采纳 /api/v1/solutions/{id}。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}")]
[Authorize]
[Produces("application/json")]
public class SolutionsController(IMediator mediator) : ControllerBase
{
    /// <summary>分页查询某题目的题解列表(sort=hot|new|accepted)</summary>
    [HttpGet("problems/{problemId:guid}/solutions")]
    [ProducesResponseType(typeof(PagedResult<SolutionListItemDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<SolutionListItemDto>>> ListByProblem(
        Guid problemId, [FromQuery] int page = 1, [FromQuery] int pageSize = 20,
        [FromQuery] string sort = "hot", CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListSolutionsQuery(problemId, page, pageSize, sort), ct);
        return Ok(result);
    }

    /// <summary>创建题解</summary>
    [HttpPost("problems/{problemId:guid}/solutions")]
    [ProducesResponseType(typeof(SolutionDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<SolutionDto>> Create(
        Guid problemId, [FromBody] CreateSolutionDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(
            new CreateSolutionCommand(problemId, dto.Title, dto.Content, dto.Code, dto.Language), ct);
        return Ok(result);
    }

    /// <summary>获取题解详情</summary>
    [HttpGet("solutions/{id:guid}")]
    [ProducesResponseType(typeof(SolutionDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<SolutionDto>> GetById(Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(new GetSolutionQuery(id), ct);
        return result is null ? NotFound() : Ok(result);
    }

    /// <summary>切换题解点赞(已赞则取消,未赞则添加)</summary>
    [HttpPost("solutions/{id:guid}/like")]
    [ProducesResponseType(typeof(ToggleLikeResultDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<ToggleLikeResultDto>> ToggleLike(Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(new ToggleLikeSolutionCommand(id), ct);
        return Ok(result);
    }

    /// <summary>采纳题解(题解作者或教师/管理员可调)</summary>
    [HttpPost("solutions/{id:guid}/accept")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    public async Task<IActionResult> Accept(Guid id, CancellationToken ct)
    {
        await mediator.Send(new AcceptSolutionCommand(id), ct);
        return NoContent();
    }
}
