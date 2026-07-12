namespace ZZW.CodeTeacher.Domain.Services;

using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Exceptions;
using ZZW.CodeTeacher.Domain.ValueObjects;

/// <summary>
/// 评测领域服务 —— 封装对提交代码执行测评的核心业务逻辑。
/// 领域服务处理跨聚合或无状态的业务操作。
/// </summary>
public sealed class JudgingService
{
    /// <summary>
    /// 对提交代码执行测评。
    /// 实际执行由基础设施层（沙箱/进程）完成，这里只做结果聚合。
    /// </summary>
    public static JudgeReport Judge(IReadOnlyList<(string Input, string Expected)> testCases,
        Func<string, string> execute, int timeLimitMs, int memoryLimitKb)
    {
        var results = new List<TestCaseResult>(testCases.Count);
        long totalMs = 0;
        long maxMem = 0;

        for (var i = 0; i < testCases.Count; i++)
        {
            var (input, expected) = testCases[i];
            var sw = System.Diagnostics.Stopwatch.StartNew();
            string actual;
            try
            {
                actual = execute(input);
            }
            catch (Exception ex)
            {
                results.Add(TestCaseResult.Fail(i, sw.ElapsedMilliseconds, 0,
                    expected, "", ex.Message));
                return new JudgeReport(testCases.Count, results.Count(r => r.Passed),
                    totalMs, maxMem, results);
            }
            sw.Stop();

            var elapsed = sw.ElapsedMilliseconds;
            totalMs += elapsed;

            var passed = string.Equals(actual?.Trim(), expected?.Trim(), StringComparison.Ordinal);
            results.Add(passed
                ? TestCaseResult.Pass(i, elapsed, 0)
                : TestCaseResult.Fail(i, elapsed, 0, expected ?? "", actual ?? "", null));

            if (elapsed > timeLimitMs)
                throw new DomainException($"测试用例 {i + 1} 超时（{elapsed}ms > {timeLimitMs}ms）");
        }

        return new JudgeReport(testCases.Count, results.Count(r => r.Passed),
            totalMs, maxMem, results);
    }
}

/// <summary>
/// 权限领域服务 —— 检查用户是否有权执行某操作。
/// </summary>
public sealed class AuthorizationService
{
    public static bool CanManageProblems(UserRole role) =>
        role is UserRole.Teacher or UserRole.Admin;

    public static bool CanReviewSubmissions(UserRole role) =>
        role is UserRole.Teacher or UserRole.Admin;

    public static bool CanViewAllUsers(UserRole role) =>
        role is UserRole.Admin;

    public static void EnsureCanManageProblems(UserRole role)
    {
        if (!CanManageProblems(role))
            throw new ForbiddenException($"角色 {role} 无权管理题目");
    }
}
