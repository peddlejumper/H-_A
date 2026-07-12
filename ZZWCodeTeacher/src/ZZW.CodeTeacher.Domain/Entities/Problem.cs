namespace ZZW.CodeTeacher.Domain.Entities;

using System.Collections.ObjectModel;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Events;
using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 题目聚合根。
/// 聚合根负责维护自身一致性边界：测试用例的增删、难度变更等都通过聚合根方法进行。
/// </summary>
public sealed class Problem
{
    private readonly List<TestCase> _testCases = [];

    /// <summary>题目唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>题号（如 P001）</summary>
    public string Code { get; private set; } = string.Empty;

    /// <summary>标题</summary>
    public string Title { get; private set; } = string.Empty;

    /// <summary>描述</summary>
    public string Description { get; private set; } = string.Empty;

    /// <summary>难度</summary>
    public DifficultyLevel Difficulty { get; private set; }

    /// <summary>时间限制（毫秒）</summary>
    public int TimeLimitMs { get; private set; }

    /// <summary>内存限制（KB）</summary>
    public int MemoryLimitKb { get; private set; }

    /// <summary>输出比对器类型(默认 Exact 精确匹配;可选 FloatTolerance 浮点容差 / SpecialJudge 特判)</summary>
    public CheckerType CheckerType { get; private set; } = CheckerType.Exact;

    /// <summary>代码模板</summary>
    public string Template { get; private set; } = string.Empty;

    /// <summary>标签</summary>
    public IReadOnlyList<string> Tags { get; private set; } = [];

    /// <summary>该题目支持的编程语言(至少 1 种,默认 [Python])</summary>
    public IReadOnlyList<SupportedLanguage> SupportedLanguages { get; private set; } = [];

    /// <summary>是否启用</summary>
    public bool IsActive { get; private set; }

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    /// <summary>更新时间</summary>
    public DateTime UpdatedAt { get; private set; }

    /// <summary>测试用例（聚合内实体）</summary>
    public IReadOnlyList<TestCase> TestCases => _testCases.AsReadOnly();

    // 领域事件集合
    private readonly List<IDomainEvent> _domainEvents = [];
    public IReadOnlyList<IDomainEvent> DomainEvents => _domainEvents.AsReadOnly();

    // EF Core 构造函数
    private Problem() { }

    /// <summary>工厂方法:创建新题目</summary>
    public static Problem Create(string code, string title, string description,
        DifficultyLevel difficulty, int timeLimitMs = 1000, int memoryLimitKb = 65536,
        string template = "", IEnumerable<string>? tags = null,
        IEnumerable<SupportedLanguage>? supportedLanguages = null,
        CheckerType checkerType = CheckerType.Exact)
    {
        ValidateCode(code);
        ValidateTitle(title);
        ValidateTimeLimit(timeLimitMs);
        ValidateMemoryLimit(memoryLimitKb);

        var now = DateTime.UtcNow;
        var langs = NormalizeLanguages(supportedLanguages);
        var problem = new Problem
        {
            Id = Guid.NewGuid(),
            Code = code.Trim(),
            Title = title.Trim(),
            Description = description ?? string.Empty,
            Difficulty = difficulty,
            TimeLimitMs = timeLimitMs,
            MemoryLimitKb = memoryLimitKb,
            CheckerType = checkerType,
            Template = template ?? string.Empty,
            Tags = tags?.ToList().AsReadOnly() ?? [],
            SupportedLanguages = langs,
            IsActive = true,
            CreatedAt = now,
            UpdatedAt = now
        };

        problem._domainEvents.Add(new ProblemCreatedEvent(problem.Id, problem.Code));
        return problem;
    }

    /// <summary>更新题目信息</summary>
    public void Update(string? title, string? description, DifficultyLevel? difficulty,
        int? timeLimitMs, int? memoryLimitKb, string? template,
        IEnumerable<string>? tags, IEnumerable<SupportedLanguage>? supportedLanguages = null,
        CheckerType? checkerType = null)
    {
        if (title is not null) { ValidateTitle(title); Title = title.Trim(); }
        if (description is not null) Description = description;
        if (difficulty is not null) Difficulty = difficulty.Value;
        if (timeLimitMs is not null) { ValidateTimeLimit(timeLimitMs.Value); TimeLimitMs = timeLimitMs.Value; }
        if (memoryLimitKb is not null) { ValidateMemoryLimit(memoryLimitKb.Value); MemoryLimitKb = memoryLimitKb.Value; }
        if (template is not null) Template = template;
        if (tags is not null) Tags = tags.ToList().AsReadOnly();
        if (supportedLanguages is not null) SupportedLanguages = NormalizeLanguages(supportedLanguages);
        if (checkerType is not null) CheckerType = checkerType.Value;
        UpdatedAt = DateTime.UtcNow;
    }

    /// <summary>题目是否支持指定语言</summary>
    public bool Supports(SupportedLanguage language) => SupportedLanguages.Contains(language);

    /// <summary>规范化语言集合:去重、非空校验;空则默认 Python</summary>
    private static ReadOnlyCollection<SupportedLanguage> NormalizeLanguages(
        IEnumerable<SupportedLanguage>? languages)
    {
        var list = languages?.Distinct().ToList() ?? [];
        if (list.Count == 0) list.Add(SupportedLanguage.Python);
        return list.AsReadOnly();
    }

    /// <summary>添加测试用例,返回创建的 TestCase(供仓储显式 Add)</summary>
    public TestCase AddTestCase(string input, string expectedOutput, bool isSample = false)
    {
        if (_testCases.Count >= 50)
            throw new DomainException("单个题目最多 50 个测试用例");

        var tc = TestCase.Create(Id, input, expectedOutput, isSample, _testCases.Count + 1);
        _testCases.Add(tc);
        UpdatedAt = DateTime.UtcNow;
        return tc;
    }

    /// <summary>启用/禁用题目</summary>
    public void SetActive(bool active)
    {
        if (IsActive == active) return;
        IsActive = active;
        UpdatedAt = DateTime.UtcNow;
        _domainEvents.Add(new ProblemStatusChangedEvent(Id, Code, active));
    }

    /// <summary>清除领域事件</summary>
    public void ClearDomainEvents() => _domainEvents.Clear();

    #region 校验
    private static void ValidateCode(string code)
    {
        if (string.IsNullOrWhiteSpace(code))
            throw new DomainException("题号不能为空");
        if (code.Length > 20)
            throw new DomainException("题号长度不能超过 20");
    }

    private static void ValidateTitle(string title)
    {
        if (string.IsNullOrWhiteSpace(title))
            throw new DomainException("标题不能为空");
        if (title.Length > 200)
            throw new DomainException("标题长度不能超过 200");
    }

    private static void ValidateTimeLimit(int ms)
    {
        if (ms < 100 || ms > 30000)
            throw new DomainException("时间限制必须在 100ms ~ 30000ms 之间");
    }

    private static void ValidateMemoryLimit(int kb)
    {
        if (kb < 1024 || kb > 524288)
            throw new DomainException("内存限制必须在 1MB ~ 512MB 之间");
    }
    #endregion
}

/// <summary>
/// 测试用例（聚合内实体，通过 Problem 聚合根管理）。
/// </summary>
public sealed class TestCase
{
    public Guid Id { get; private set; }
    public Guid ProblemId { get; private set; }
    public int Order { get; private set; }
    public string Input { get; private set; } = string.Empty;
    public string ExpectedOutput { get; private set; } = string.Empty;
    public bool IsSample { get; private set; }

    private TestCase() { }

    internal static TestCase Create(Guid problemId, string input, string expectedOutput,
        bool isSample, int order)
    {
        return new TestCase
        {
            Id = Guid.NewGuid(),
            ProblemId = problemId,
            Order = order,
            Input = input ?? string.Empty,
            ExpectedOutput = expectedOutput ?? string.Empty,
            IsSample = isSample
        };
    }
}
