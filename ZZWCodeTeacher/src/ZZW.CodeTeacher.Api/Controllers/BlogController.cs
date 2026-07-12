namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// 博客/知识分享区 API —— 用户发布技术文章(Markdown),支持点赞与浏览计数。
/// 列表/详情匿名可读;创建/点赞需登录。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/blog")]
[Produces("application/json")]
public class BlogController(IMediator mediator) : ControllerBase
{
    /// <summary>分页查询博客列表(默认仅已发布,支持搜索)</summary>
    [HttpGet]
    [AllowAnonymous]
    [ProducesResponseType(typeof(PagedResult<BlogPostListItemDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<BlogPostListItemDto>>> List(
        [FromQuery] int page = 1, [FromQuery] int pageSize = 20,
        [FromQuery] string? search = null, CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListBlogPostsQuery(page, pageSize, search), ct);
        return Ok(result);
    }

    /// <summary>获取博客文章详情(同时增加浏览量)</summary>
    [HttpGet("{id:guid}")]
    [AllowAnonymous]
    [ProducesResponseType(typeof(BlogPostDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<BlogPostDto>> GetById(Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(new GetBlogPostQuery(id), ct);
        return result is null ? NotFound() : Ok(result);
    }

    /// <summary>创建博客文章(需登录)</summary>
    [HttpPost]
    [Authorize]
    [ProducesResponseType(typeof(BlogPostDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<BlogPostDto>> Create([FromBody] CreateBlogPostDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(
            new CreateBlogPostCommand(dto.Title, dto.Summary, dto.Content, dto.Tags, dto.IsPublished), ct);
        return Ok(result);
    }

    /// <summary>切换博客点赞(需登录,已赞则取消)</summary>
    [HttpPost("{id:guid}/like")]
    [Authorize]
    [ProducesResponseType(typeof(ToggleLikeResultDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<ToggleLikeResultDto>> ToggleLike(Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(new ToggleBlogLikeCommand(id), ct);
        return Ok(result);
    }
}
