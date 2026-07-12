namespace ZZW.CodeTeacher.Domain.ValueObjects;

/// <summary>
/// 测评结果值对象 —— 单个测试点的执行结果。
/// </summary>
public readonly record struct TestCaseResult(
    int Index,
    bool Passed,
    long ElapsedMs,
    long MemoryKb,
    string? Expected,
    string? Actual,
    string? Error)
{
    /// <summary>创建通过的结果</summary>
    public static TestCaseResult Pass(int index, long elapsedMs, long memoryKb) =>
        new(index, true, elapsedMs, memoryKb, null, null, null);

    /// <summary>创建失败的结果</summary>
    public static TestCaseResult Fail(int index, long elapsedMs, long memoryKb,
        string expected, string actual, string? error = null) =>
        new(index, false, elapsedMs, memoryKb, expected, actual, error);
}

/// <summary>
/// 评测报告值对象 —— 一次提交的完整测评汇总。
/// </summary>
public readonly record struct JudgeReport(
    int TotalCases,
    int PassedCases,
    long TotalElapsedMs,
    long MaxMemoryKb,
    IReadOnlyList<TestCaseResult> Cases)
{
    /// <summary>通过率（0.0 ~ 1.0）</summary>
    public double PassRate => TotalCases == 0 ? 0 : (double)PassedCases / TotalCases;

    /// <summary>是否全部通过</summary>
    public bool AllPassed => PassedCases == TotalCases && TotalCases > 0;
}
