namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// 错题复习 API —— 基于 SM-2 间隔重复算法。
/// GET /reviews/due 查今日待复习;POST /reviews/{problemId} 评分(quality 0~5)触发 SM-2 更新。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/reviews")]
[Authorize]
[Produces("application/json")]
public class ReviewsController(IMediator mediator) : ControllerBase
{
    /// <summary>查询今日待复习项</summary>
    [HttpGet("due")]
    [ProducesResponseType(typeof(IReadOnlyList<ReviewItemDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<ReviewItemDto>>> ListDue(CancellationToken ct)
    {
        var result = await mediator.Send(new GetDueReviewsQuery(), ct);
        return Ok(result);
    }

    /// <summary>复习评分(quality 0~5,触发 SM-2 算法更新复习计划)</summary>
    [HttpPost("{problemId:guid}")]
    [ProducesResponseType(typeof(ReviewItemDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<ReviewItemDto>> ScheduleReview(
        Guid problemId, [FromBody] ScheduleReviewDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(new ScheduleReviewCommand(problemId, dto.Quality), ct);
        return Ok(result);
    }
}
