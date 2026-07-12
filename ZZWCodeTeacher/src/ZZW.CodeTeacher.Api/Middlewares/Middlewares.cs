#pragma warning disable CA1848, CA1873
namespace ZZW.CodeTeacher.Api.Middlewares;

using System.Net;
using System.Text.Json;
using FluentValidation;
using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 全局异常处理中间件 —— 统一捕获异常并返回标准化错误响应。
/// </summary>
public sealed class GlobalExceptionMiddleware(RequestDelegate next, ILogger<GlobalExceptionMiddleware> logger)
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await next(context);
        }
        catch (Exception ex)
        {
            await HandleExceptionAsync(context, ex, logger);
        }
    }

    private static async Task HandleExceptionAsync(HttpContext ctx, Exception ex, ILogger logger)
    {
        var (status, code, message) = ex switch
        {
            ValidationException ve => (HttpStatusCode.BadRequest, "VALIDATION_ERROR",
                string.Join("; ", ve.Errors.Select(e => e.ErrorMessage))),
            NotFoundException => (HttpStatusCode.NotFound, "NOT_FOUND", ex.Message),
            ForbiddenException => (HttpStatusCode.Forbidden, "FORBIDDEN", ex.Message),
            DomainException de => (HttpStatusCode.BadRequest, "DOMAIN_ERROR", de.Message),
            UnauthorizedAccessException => (HttpStatusCode.Unauthorized, "UNAUTHORIZED", "未授权"),
            _ => (HttpStatusCode.InternalServerError, "INTERNAL_ERROR", "服务器内部错误")
        };

        if (status == HttpStatusCode.InternalServerError)
            logger.LogError(ex, "未处理异常：{Message}", ex.Message);
        else
            logger.LogWarning("业务异常：{Code} - {Message}", code, message);

        ctx.Response.ContentType = "application/json; charset=utf-8";
        ctx.Response.StatusCode = (int)status;

        var response = new
        {
            success = false,
            errorCode = code,
            message,
            traceId = ctx.TraceIdentifier
        };

        var json = JsonSerializer.Serialize(response, JsonOptions);
        await ctx.Response.WriteAsync(json);
    }
}

/// <summary>
/// 请求日志中间件 —— 记录每个请求的方法、路径、状态码、耗时。
/// </summary>
public sealed class RequestLoggingMiddleware(RequestDelegate next, ILogger<RequestLoggingMiddleware> logger)
{
    public async Task InvokeAsync(HttpContext context)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        try
        {
            await next(context);
        }
        finally
        {
            sw.Stop();
            logger.LogInformation("{Method} {Path} → {StatusCode} ({ElapsedMs}ms)",
                context.Request.Method, context.Request.Path,
                context.Response.StatusCode, sw.ElapsedMilliseconds);
        }
    }
}
