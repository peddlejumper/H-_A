namespace ZZW.CodeTeacher.Application.Behaviors;

using System.Diagnostics;
using MediatR;
using Microsoft.Extensions.Logging;

/// <summary>
/// 日志行为（Pipeline Behavior）—— 记录每个请求的执行时间。
/// 使用 .NET 10 的 Stopwatch.GetTimestamp() 高精度计时。
/// </summary>
public sealed class LoggingBehavior<TRequest, TResponse>(ILogger<LoggingBehavior<TRequest, TResponse>> logger)
    : IPipelineBehavior<TRequest, TResponse> where TRequest : notnull
{
    private static readonly Action<ILogger, string, Exception?> _logRequestStart =
        LoggerMessage.Define<string>(LogLevel.Information, new EventId(1), "→ {RequestName} 开始");
    private static readonly Action<ILogger, string, double, Exception?> _logRequestComplete =
        LoggerMessage.Define<string, double>(LogLevel.Information, new EventId(2), "← {RequestName} 完成，耗时 {ElapsedMs}ms");
    private static readonly Action<ILogger, string, double, Exception?> _logRequestFailed =
        LoggerMessage.Define<string, double>(LogLevel.Error, new EventId(3), "✕ {RequestName} 失败，耗时 {ElapsedMs}ms");

    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next,
        CancellationToken cancellationToken)
    {
        var requestName = typeof(TRequest).Name;
        _logRequestStart(logger, requestName, null);

        var start = Stopwatch.GetTimestamp();
        try
        {
            var response = await next();
            var elapsed = Stopwatch.GetElapsedTime(start);
            _logRequestComplete(logger, requestName, elapsed.TotalMilliseconds, null);
            return response;
        }
        catch (Exception ex)
        {
            var elapsed = Stopwatch.GetElapsedTime(start);
            _logRequestFailed(logger, requestName, elapsed.TotalMilliseconds, ex);
            throw;
        }
    }
}

/// <summary>
/// 验证行为 —— 在请求处理前自动执行 FluentValidation 验证。
/// </summary>
public sealed class ValidationBehavior<TRequest, TResponse>(
    IEnumerable<FluentValidation.IValidator<TRequest>> validators)
    : IPipelineBehavior<TRequest, TResponse> where TRequest : notnull
{
    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next,
        CancellationToken cancellationToken)
    {
        if (!validators.Any()) return await next();

        var context = new FluentValidation.ValidationContext<TRequest>(request);
        var results = await Task.WhenAll(
            validators.Select(v => v.ValidateAsync(context, cancellationToken)));
        var failures = results.SelectMany(r => r.Errors).Where(f => f is not null).ToList();

        if (failures.Count != 0)
            throw new FluentValidation.ValidationException(failures);

        return await next();
    }
}

/// <summary>
/// 异常处理行为 —— 统一捕获领域异常并包装。
/// </summary>
public sealed class ExceptionBehavior<TRequest, TResponse>
    : IPipelineBehavior<TRequest, TResponse> where TRequest : notnull
{
    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next,
        CancellationToken cancellationToken)
    {
        try
        {
            return await next();
        }
        catch (Domain.Exceptions.DomainException)
        {
            throw; // 领域异常直接抛出，由中间件统一处理
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException($"处理 {typeof(TRequest).Name} 时发生错误", ex);
        }
    }
}
