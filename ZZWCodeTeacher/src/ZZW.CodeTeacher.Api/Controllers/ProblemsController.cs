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
/// 题目管理 API。
/// 遵循 RESTful 规范：GET 查询、POST 创建、PUT 更新、DELETE 删除。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/problems")]
[Produces("application/json")]
public class ProblemsController(IMediator mediator) : ControllerBase
{
    /// <summary>分页查询题目列表</summary>
    [HttpGet]
    [ProducesResponseType(typeof(PagedResult<ProblemListItemDto>), StatusCodes.Status200OK)]
    public async Task<ActionResult<PagedResult<ProblemListItemDto>>> List(
        [FromQuery] int page = 1, [FromQuery] int pageSize = 20,
        [FromQuery] DifficultyLevel? difficulty = null,
        [FromQuery] bool? isActive = null,
        [FromQuery] string? search = null,
        CancellationToken ct = default)
    {
        var result = await mediator.Send(new ListProblemsQuery(page, pageSize, difficulty, isActive, search), ct);
        return Ok(result);
    }

    /// <summary>获取题目详情</summary>
    [HttpGet("{id:guid}")]
    [ProducesResponseType(typeof(ProblemDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ProblemDto>> GetById(Guid id, CancellationToken ct)
    {
        var problem = await mediator.Send(new GetProblemByIdQuery(id), ct);
        return problem is null ? NotFound() : Ok(problem);
    }

    /// <summary>创建题目(教师/管理员)</summary>
    [HttpPost]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(typeof(ProblemDto), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<ProblemDto>> Create([FromBody] CreateProblemDto dto, CancellationToken ct)
    {
        var problem = await mediator.Send(new CreateProblemCommand(
            dto.Code, dto.Title, dto.Description, dto.Difficulty,
            dto.TimeLimitMs, dto.MemoryLimitKb, dto.Template, dto.Tags,
            dto.SupportedLanguages), ct);
        return CreatedAtAction(nameof(GetById), new { id = problem.Id }, problem);
    }

    /// <summary>更新题目</summary>
    [HttpPut("{id:guid}")]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(typeof(ProblemDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<ProblemDto>> Update(Guid id, [FromBody] UpdateProblemDto dto, CancellationToken ct)
    {
        var problem = await mediator.Send(new UpdateProblemCommand(
            id, dto.Title, dto.Description, dto.Difficulty, dto.TimeLimitMs,
            dto.MemoryLimitKb, dto.Template, dto.Tags, dto.SupportedLanguages), ct);
        return Ok(problem);
    }

    /// <summary>添加测试用例</summary>
    [HttpPost("{id:guid}/testcases")]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> AddTestCase(Guid id, [FromBody] AddTestCaseDto dto, CancellationToken ct)
    {
        await mediator.Send(new AddTestCaseCommand(id, dto.Input, dto.ExpectedOutput, dto.IsSample), ct);
        return NoContent();
    }

    /// <summary>删除题目</summary>
    [HttpDelete("{id:guid}")]
    [Authorize(Roles = "Admin")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> Delete(Guid id, CancellationToken ct)
    {
        await mediator.Send(new DeleteProblemCommand(id), ct);
        return NoContent();
    }

    /// <summary>启用/禁用题目</summary>
    [HttpPatch("{id:guid}/active")]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    public async Task<IActionResult> Toggle(Guid id, [FromQuery] bool active, CancellationToken ct)
    {
        await mediator.Send(new ToggleProblemCommand(id, active), ct);
        return NoContent();
    }

    /// <summary>批量导入题目(教师/管理员)。逐条创建并返回成功/失败明细</summary>
    [HttpPost("bulk-import")]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(typeof(BulkImportResultDto), StatusCodes.Status200OK)]
    public async Task<ActionResult<BulkImportResultDto>> BulkImport(
        [FromBody] BulkImportProblemsDto dto, CancellationToken ct)
    {
        var result = await mediator.Send(new BulkImportProblemsCommand(dto.Items), ct);
        return Ok(result);
    }

    /// <summary>导出题目(全部或按 ids),返回 JSON 文件下载(application/json,attachment)</summary>
    [HttpGet("export")]
    [Authorize(Roles = "Teacher,Admin")]
    [ProducesResponseType(typeof(IReadOnlyList<ProblemDto>), StatusCodes.Status200OK)]
    public async Task<IActionResult> Export([FromQuery] string? ids, CancellationToken ct)
    {
        IReadOnlyList<Guid>? idList = null;
        if (!string.IsNullOrWhiteSpace(ids))
        {
            idList = ids.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                .Select(s => Guid.TryParse(s, out var g) ? g : Guid.Empty)
                .Where(g => g != Guid.Empty)
                .ToList();
        }
        var problems = await mediator.Send(new ExportProblemsQuery(idList), ct);
        var json = System.Text.Json.JsonSerializer.Serialize(problems, JsonOptions);
        return File(System.Text.Encoding.UTF8.GetBytes(json), "application/json", "problems.json");
    }

    private static readonly System.Text.Json.JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase,
        WriteIndented = true,
        Converters = { new System.Text.Json.Serialization.JsonStringEnumConverter() }
    };
}
