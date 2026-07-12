namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;
using ZZW.CodeTeacher.Domain.Enums;

/// <summary>
/// 仪表盘统计 API —— 为 TREA 风格前端提供数据可视化端点。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/dashboard")]
[Produces("application/json")]
[Authorize]
public class DashboardController(IMediator mediator) : ControllerBase
{
    /// <summary>获取仪表盘统计数据</summary>
    [HttpGet("stats")]
    [ProducesResponseType(typeof(DashboardStatsDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<DashboardStatsDto>> GetStats(CancellationToken ct)
    {
        var stats = await mediator.Send(new GetDashboardStatsQuery(), ct);
        return Ok(stats);
    }

    /// <summary>多维排行榜(scope=week|month|all,可选 language 过滤)</summary>
    [HttpGet("leaderboard")]
    [ProducesResponseType(typeof(IReadOnlyList<TopUserDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<TopUserDto>>> Leaderboard(
        [FromQuery] LeaderboardScope scope = LeaderboardScope.All,
        [FromQuery] SupportedLanguage? language = null,
        CancellationToken ct = default)
    {
        var result = await mediator.Send(new LeaderboardQuery(scope, language), ct);
        return Ok(result);
    }
}
