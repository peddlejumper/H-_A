namespace ZZW.CodeTeacher.Api.Controllers;

using Asp.Versioning;
using Microsoft.AspNetCore.Mvc;
using MediatR;
using ZZW.CodeTeacher.Application.Interfaces;

/// <summary>
/// H# 控制面板 API —— 暴露 H# 脚本执行能力。
/// 通过此 API 可触发 H# 运维脚本、查看规则执行结果。
/// </summary>
[ApiController]
[ApiVersion(1.0)]
[Route("api/v{version:apiVersion}/panel")]
[Produces("application/json")]
public class HSharpPanelController(IHSharpScriptRunner runner) : ControllerBase
{
    /// <summary>执行指定 H# 脚本</summary>
    [HttpPost("run/{scriptName}")]
    public async Task<IActionResult> RunScript(string scriptName, CancellationToken ct)
    {
        var scriptPath = $"scripts/{scriptName}.hto";
        var output = await runner.RunAsync(scriptPath, null, ct);
        return Ok(new { script = scriptName, output });
    }

    /// <summary>获取控制面板可用脚本列表</summary>
    [HttpGet("scripts")]
    public IActionResult ListScripts()
    {
        var scriptsDir = Path.Combine(AppContext.BaseDirectory, "scripts");
        if (!Directory.Exists(scriptsDir))
            return Ok(new { scripts = Array.Empty<string>() });

        var scripts = Directory.GetFiles(scriptsDir, "*.hto")
            .Select(Path.GetFileNameWithoutExtension)
            .ToArray();
        return Ok(new { scripts });
    }
}
