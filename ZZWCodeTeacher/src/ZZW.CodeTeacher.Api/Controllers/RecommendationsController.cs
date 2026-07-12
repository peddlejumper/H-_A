namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// AI 题目推荐 API —— 错题驱动的规则推荐(不引入 ML)。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/recommendations")]
[Authorize]
[Produces("application/json")]
public class RecommendationsController(IMediator mediator) : ControllerBase
{
    /// <summary>获取推荐题目(错题驱动,limit 默认 5)</summary>
    [HttpGet("problems")]
    [ProducesResponseType(typeof(IReadOnlyList<RecommendedProblemDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<RecommendedProblemDto>>> RecommendProblems(
        [FromQuery] int limit = 5, CancellationToken ct = default)
    {
        var result = await mediator.Send(new GetRecommendedProblemsQuery(limit), ct);
        return Ok(result);
    }
}
