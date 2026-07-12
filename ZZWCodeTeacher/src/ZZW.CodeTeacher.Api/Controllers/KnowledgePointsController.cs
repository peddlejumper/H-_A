namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Queries;

/// <summary>
/// 知识点/标签图谱 API —— 自关联形成树形结构,支持按知识点查询题目。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/knowledge-points")]
[Produces("application/json")]
public class KnowledgePointsController(IMediator mediator) : ControllerBase
{
    /// <summary>获取知识点树</summary>
    [HttpGet]
    [ProducesResponseType(typeof(IReadOnlyList<KnowledgePointDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<KnowledgePointDto>>> GetTree(CancellationToken ct)
    {
        var result = await mediator.Send(new GetKnowledgeTreeQuery(), ct);
        return Ok(result);
    }

    /// <summary>创建知识点(教师/管理员)</summary>
    [HttpPost]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(typeof(KnowledgePointDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<KnowledgePointDto>> Create(
        [FromBody] CreateKnowledgePointDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(
            new CreateKnowledgePointCommand(dto.Name, dto.Description, dto.ParentId), ct);
        return Ok(result);
    }

    /// <summary>关联题目与知识点(教师/管理员)</summary>
    [HttpPost("link")]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> LinkProblem([FromBody] LinkProblemKnowledgePointDto dto, CancellationToken ct)
    {
        await mediator.Send(new LinkProblemKnowledgePointCommand(dto.ProblemId, dto.KnowledgePointId), ct);
        return NoContent();
    }

    /// <summary>按知识点查询题目</summary>
    [HttpGet("{id:guid}/problems")]
    [ProducesResponseType(typeof(IReadOnlyList<ProblemListItemDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<IReadOnlyList<ProblemListItemDto>>> GetProblems(Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(new GetProblemsByKnowledgePointQuery(id), ct);
        return Ok(result);
    }
}
