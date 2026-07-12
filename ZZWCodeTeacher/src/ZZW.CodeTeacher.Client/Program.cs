using Avalonia;
using System;
using System.Globalization;
using System.IO;
using Serilog;

namespace ZZW.CodeTeacher.Client;

internal static class Program
{
    [STAThread]
    public static void Main(string[] args)
    {
        ConfigureLogging();
        try
        {
            BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
        }
        catch (Exception ex)
        {
            Log.Fatal(ex, "客户端启动失败");
            throw;
        }
        finally
        {
            Log.CloseAndFlush();
        }
    }

    /// <summary>
    /// Serilog FileSink 配置:写到 %AppData%/ZZWCodeTeacher/logs/client-YYYYMMDD.log,
    /// 滚动 daily,保留 7 天。客户端异常/VM 错误均落盘,便于排查。
    /// </summary>
    private static void ConfigureLogging()
    {
        var dir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "ZZWCodeTeacher", "logs");
        try { Directory.CreateDirectory(dir); }
        catch { /* 目录创建失败不阻塞,FileSink 内部会再次尝试 */ }

        Log.Logger = new LoggerConfiguration()
            .MinimumLevel.Information()
            .WriteTo.File(
                path: Path.Combine(dir, "client-.log"),
                rollingInterval: RollingInterval.Day,
                retainedFileCountLimit: 7,
                formatProvider: CultureInfo.InvariantCulture,
                outputTemplate: "{Timestamp:yyyy-MM-dd HH:mm:ss.fff} [{Level:u3}] {Message:lj}{NewLine}{Exception}")
            .CreateLogger();
        Log.Information("=== 客户端启动 ===");
    }

    public static AppBuilder BuildAvaloniaApp()
        => AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .WithInterFont()
            .LogToTrace();
}
