namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// 每日打卡 API —— 学习打卡与连续天数统计。
/// UserId 从登录态(JWT Claims)经 ICurrentUser 获取。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/checkins")]
[Authorize]
[Produces("application/json")]
public class CheckInsController(IMediator mediator) : ControllerBase
{
    /// <summary>每日打卡(同日幂等,不重复加)</summary>
    [HttpPost]
    [ProducesResponseType(typeof(CheckInResultDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<CheckInResultDto>> CheckIn(CancellationToken ct)
    {
        var result = await mediator.Send(new CheckInCommand(), ct);
        return Ok(result);
    }

    /// <summary>获取当前用户打卡状态(连续天数、今日是否已打卡、累计打卡数)</summary>
    [HttpGet("status")]
    [ProducesResponseType(typeof(CheckInResultDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<CheckInResultDto>> GetStatus(CancellationToken ct)
    {
        var result = await mediator.Send(new GetCheckInStatusQuery(), ct);
        return Ok(result);
    }
}
