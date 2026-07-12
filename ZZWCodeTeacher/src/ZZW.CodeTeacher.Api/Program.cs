namespace ZZW.CodeTeacher.Api;

using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Serilog;
using ZZW.CodeTeacher.Api.Extensions;
using ZZW.CodeTeacher.Api.Middlewares;
using ZZW.CodeTeacher.Application.Services;
using ZZW.CodeTeacher.Infrastructure;
using ZZW.CodeTeacher.Infrastructure.Logging;
using ZZW.CodeTeacher.Infrastructure.Persistence;

/// <summary>
/// 应用程序入口 —— .NET 10 Minimal Hosting Model。
/// </summary>
public partial class Program
{
    public static async Task Main(string[] args)
    {
        var builder = WebApplication.CreateBuilder(args);

        // Serilog 日志
        Log.Logger = new LoggerConfiguration()
            .ConfigureLogging("ZZW.CodeTeacher.Api")
            .CreateLogger();
        builder.Host.UseSerilog();

        // 分层注册
        builder.Services.AddApplication();
        builder.Services.AddInfrastructure(builder.Configuration);
        builder.Services.AddApiServices(builder.Configuration);

        builder.Services.AddControllers()
            .AddJsonOptions(opt =>
            {
                opt.JsonSerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase;
                opt.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter());
            });

        var app = builder.Build();

        // 自动建表 + 种子数据（经典 OJ 题目与默认账户）
        using (var scope = app.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<CodeTeacherDbContext>();
            await ZZW.CodeTeacher.Infrastructure.Persistence.DbSeeder.SeedAsync(db);
        }

        // 中间件管道（顺序重要）
        app.UseMiddleware<GlobalExceptionMiddleware>();
        app.UseMiddleware<RequestLoggingMiddleware>();
        app.UseSerilogRequestLogging();

        // 本地开发环境不强制 HTTPS(Safari 对 http://127.0.0.1 的 ATS 会直接 Load failed)
        if (!app.Environment.IsDevelopment())
        {
            app.UseHttpsRedirection();
        }
        app.UseCors();
        app.UseRateLimiter();
        app.UseAuthentication();
        app.UseAuthorization();

        // TREA 前端静态文件（从 Web 项目的 wwwroot 提供）
        var webRoot = Path.Combine(builder.Environment.ContentRootPath, "..", "ZZW.CodeTeacher.Web", "wwwroot");
        if (Directory.Exists(webRoot))
        {
            app.UseStaticFiles(new StaticFileOptions { FileProvider = new Microsoft.Extensions.FileProviders.PhysicalFileProvider(webRoot) });
        }

        app.MapControllers();
        app.MapOpenApi();

        // 根路径 → TREA 前端
        app.MapGet("/", () => Results.File(Path.Combine(webRoot, "index.html"), "text/html")).AllowAnonymous();

        // OpenAPI 文档
        app.MapGet("/docs", () => Results.Redirect("/openapi/v1.json")).AllowAnonymous();

        Log.Information("ZZW Code Teacher API 启动中...");
        app.Run();
    }
}
