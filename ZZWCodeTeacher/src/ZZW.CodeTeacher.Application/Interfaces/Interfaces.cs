namespace ZZW.CodeTeacher.Application.Interfaces;

using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.ValueObjects;

/// <summary>密码哈希服务接口</summary>
public interface IPasswordHasher
{
    string Hash(string password);
    bool Verify(string password, string hash);
}

/// <summary>JWT 令牌服务接口</summary>
public interface ITokenService
{
    (string token, int expiresIn) GenerateToken(User user);
}

/// <summary>当前用户上下文接口</summary>
public interface ICurrentUser
{
    Guid? UserId { get; }
    string Username { get; }
    Domain.Enums.UserRole Role { get; }
    bool IsAuthenticated { get; }
}

/// <summary>H# 脚本执行器接口 —— 用于在 .NET 中调用 H# 控制面板脚本</summary>
public interface IHSharpScriptRunner
{
    /// <summary>执行指定脚本,返回标准输出</summary>
    Task<string> RunAsync(string scriptPath, IReadOnlyDictionary<string, string>? args = null,
        CancellationToken ct = default);

    /// <summary>执行脚本并获取 JSON 结果</summary>
    Task<T?> RunJsonAsync<T>(string scriptPath, IReadOnlyDictionary<string, string>? args = null,
        CancellationToken ct = default);
}

/// <summary>
/// 通用代码评测器接口 —— 多语言教学的核心。
/// 实现方负责进程隔离/资源限制,针对每种 SupportedLanguage 分发到对应运行时。
/// </summary>
public interface ICodeJudgeRunner
{
    /// <summary>检测指定语言的运行时是否可用(如 python3/node/javac 是否在 PATH)</summary>
    bool IsLanguageAvailable(SupportedLanguage language);

    /// <summary>返回当前环境可用的所有语言</summary>
    IReadOnlyList<SupportedLanguage> GetAvailableLanguages();

    /// <summary>
    /// 对一份代码运行所有测试用例并产出评测报告。
    /// 实现需保证:
    ///  - 单次运行严格受 TimeLimitMs / MemoryLimitKb 约束
    ///  - 子进程与文件系统隔离(临时目录 + 受限权限)
    ///  - 失败时返回结构化错误(CompileError/RuntimeError/TLE/MLE/WrongAnswer)
    ///  - 输出比对按 checkerType 决定(精确 / 浮点容差 / 特判)
    /// </summary>
    Task<JudgeReport> JudgeAsync(
        SupportedLanguage language,
        string code,
        IReadOnlyList<TestCase> testCases,
        int timeLimitMs,
        int memoryLimitKb,
        CheckerType checkerType = CheckerType.Exact,
        CancellationToken ct = default);

    /// <summary>
    /// 仅编译(编译型语言)。返回 (success, errorMessage)。
    /// 解释型语言直接返回 (true, null)。
    /// </summary>
    Task<(bool Success, string? Error)> CompileAsync(
        SupportedLanguage language, string code, CancellationToken ct = default);
}

/// <summary>缓存服务接口</summary>
public interface ICacheService
{
    Task<T?> GetAsync<T>(string key, CancellationToken ct = default);
    Task SetAsync<T>(string key, T value, TimeSpan? expiry = null, CancellationToken ct = default);
    Task RemoveAsync(string key, CancellationToken ct = default);
}
