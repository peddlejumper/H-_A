namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// 收藏 API —— 用户对题目的收藏关系管理。
/// UserId 从登录态(JWT Claims)经 ICurrentUser 获取。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/favorites")]
[Authorize]
[Produces("application/json")]
public class FavoritesController(IMediator mediator) : ControllerBase
{
    /// <summary>切换收藏(已收藏则取消,未收藏则添加),返回当前是否已收藏</summary>
    [HttpPost("{problemId:guid}")]
    [ProducesResponseType(typeof(bool), StatusCodes.Status200OK)]
    public async Task<ActionResult<bool>> Toggle(Guid problemId, CancellationToken ct)
    {
        var result = await mediator.Send(new ToggleFavoriteCommand(problemId), ct);
        return Ok(result);
    }

    /// <summary>列出我的收藏(分页,返回题目列表项)</summary>
    [HttpGet]
    [ProducesResponseType(typeof(PagedResult<ProblemListItemDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<ProblemListItemDto>>> List(
        [FromQuery] int page = 1, [FromQuery] int pageSize = 20, CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListFavoritesQuery(page, pageSize), ct);
        return Ok(result);
    }
}
