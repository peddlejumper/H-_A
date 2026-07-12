namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 题解聚合根 —— 学员对某道题目的解答分享,支持点赞与采纳。
/// </summary>
public sealed class Solution
{
    /// <summary>题解唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>所属题目 Id</summary>
    public Guid ProblemId { get; private set; }

    /// <summary>作者用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>标题</summary>
    public string Title { get; private set; } = string.Empty;

    /// <summary>正文(Markdown)</summary>
    public string Content { get; private set; } = string.Empty;

    /// <summary>可选:附带的代码</summary>
    public string? Code { get; private set; }

    /// <summary>可选:代码语言</summary>
    public SupportedLanguage? Language { get; private set; }

    /// <summary>点赞数(冗余计数)</summary>
    public int LikeCount { get; private set; }

    /// <summary>是否被采纳(题目作者或教师可置)</summary>
    public bool IsAccepted { get; private set; }

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    /// <summary>更新时间</summary>
    public DateTime UpdatedAt { get; private set; }

    // EF Core 构造函数
    private Solution() { }

    /// <summary>工厂方法:创建题解</summary>
    public static Solution Create(Guid problemId, Guid userId, string title, string content,
        string? code = null, SupportedLanguage? language = null)
    {
        if (problemId == Guid.Empty)
            throw new DomainException("题目 Id 不能为空");
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");
        if (string.IsNullOrWhiteSpace(title))
            throw new DomainException("题解标题不能为空");
        if (title.Length > 200)
            throw new DomainException("题解标题长度不能超过 200");
        if (string.IsNullOrWhiteSpace(content))
            throw new DomainException("题解内容不能为空");

        var now = DateTime.UtcNow;
        return new Solution
        {
            Id = Guid.NewGuid(),
            ProblemId = problemId,
            UserId = userId,
            Title = title.Trim(),
            Content = content,
            Code = code,
            Language = language,
            LikeCount = 0,
            IsAccepted = false,
            CreatedAt = now,
            UpdatedAt = now
        };
    }

    /// <summary>点赞(计数 +1)</summary>
    public void IncrementLike()
    {
        LikeCount++;
        UpdatedAt = DateTime.UtcNow;
    }

    /// <summary>取消点赞(计数 -1,不低于 0)</summary>
    public void DecrementLike()
    {
        if (LikeCount > 0) LikeCount--;
        UpdatedAt = DateTime.UtcNow;
    }

    /// <summary>采纳该题解</summary>
    public void Accept()
    {
        IsAccepted = true;
        UpdatedAt = DateTime.UtcNow;
    }
}

/// <summary>
/// 题解点赞实体 —— 同用户同题解唯一。
/// </summary>
public sealed class SolutionLike
{
    /// <summary>点赞唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>题解 Id</summary>
    public Guid SolutionId { get; private set; }

    /// <summary>点赞用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>点赞时间</summary>
    public DateTime CreatedAt { get; private set; }

    private SolutionLike() { }

    public static SolutionLike Create(Guid solutionId, Guid userId)
    {
        if (solutionId == Guid.Empty)
            throw new DomainException("题解 Id 不能为空");
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");

        return new SolutionLike
        {
            Id = Guid.NewGuid(),
            SolutionId = solutionId,
            UserId = userId,
            CreatedAt = DateTime.UtcNow
        };
    }
}
