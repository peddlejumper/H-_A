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
/// 用户管理 API。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/users")]
[Produces("application/json")]
public class UsersController(IMediator mediator) : ControllerBase
{
    /// <summary>注册新用户</summary>
    [HttpPost("register")]
    [AllowAnonymous]
    [ProducesResponseType(typeof(AuthResultDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<AuthResultDto>> Register([FromBody] RegisterDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(new RegisterCommand(
            dto.Username, dto.Email, dto.Password, dto.DisplayName), ct);
        return Ok(result);
    }

    /// <summary>用户登录</summary>
    [HttpPost("login")]
    [AllowAnonymous]
    [ProducesResponseType(typeof(AuthResultDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<ActionResult<AuthResultDto>> Login([FromBody] LoginDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(new LoginCommand(dto.Username, dto.Password), ct);
        return Ok(result);
    }

    /// <summary>获取当前登录用户</summary>
    [HttpGet("me")]
    [Authorize]
    [ProducesResponseType(typeof(UserDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<UserDto>> GetCurrentUser(CancellationToken ct)
    {
        var user = await mediator.Send(new GetCurrentUserQuery(), ct);
        return user is null ? Unauthorized() : Ok(user);
    }

    /// <summary>分页查询用户列表（管理员）</summary>
    [HttpGet]
    [Authorize(Roles = "Admin")]
    [ProducesResponseType(typeof(PagedResult<UserDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<UserDto>>> List(
        [FromQuery] int page = 1, [FromQuery] int pageSize = 20,
        [FromQuery] UserRole? role = null, [FromQuery] bool? isActive = null,
        [FromQuery] string? search = null, CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListUsersQuery(page, pageSize, role, isActive, search), ct);
        return Ok(result);
    }

    /// <summary>更新用户角色（管理员）</summary>
    [HttpPatch("{userId:guid}/role")]
    [Authorize(Roles = "Admin")]
    [ProducesResponseType(typeof(UserDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<UserDto>> UpdateRole(Guid userId, [FromQuery] UserRole role, CancellationToken ct)
    {
        var user = await mediator.Send(new UpdateUserRoleCommand(userId, role), ct);
        return Ok(user);
    }

    /// <summary>查询单学员学习进度(总提交/通过率/按语言/按难度/近期错题/已解题目)</summary>
    [HttpGet("{userId:guid}/progress")]
    [Authorize]
    [ProducesResponseType(typeof(UserProgressDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<UserProgressDto>> GetProgress(Guid userId, CancellationToken ct)
    {
        var result = await mediator.Send(new GetUserProgressQuery(userId), ct);
        return Ok(result);
    }
}
