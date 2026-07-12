namespace ZZW.CodeTeacher.Infrastructure.Logging;

using System.Globalization;
using Serilog;
using Serilog.Configuration;
using Serilog.Events;

/// <summary>
/// Serilog 日志配置扩展。
/// </summary>
public static class LoggingConfiguration
{
    public static LoggerConfiguration ConfigureLogging(this LoggerConfiguration cfg, string appName)
    {
        return cfg
            .MinimumLevel.Information()
            .Enrich.FromLogContext()
            .Enrich.WithProperty("Application", appName)
            .WriteTo.Console(
                outputTemplate: "[{Timestamp:HH:mm:ss} {Level:u3}] {Message:lj} {Properties:j}{NewLine}{Exception}",
                formatProvider: CultureInfo.InvariantCulture)
            .WriteTo.File(
                path: $"logs/{appName}-.log",
                rollingInterval: RollingInterval.Day,
                retainedFileCountLimit: 14,
                restrictedToMinimumLevel: LogEventLevel.Warning,
                formatProvider: CultureInfo.InvariantCulture);
    }
}
