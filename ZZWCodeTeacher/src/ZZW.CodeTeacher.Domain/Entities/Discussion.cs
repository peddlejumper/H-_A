namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 讨论聚合根 —— 题目讨论帖。
/// 聚合根负责维护回复的创建与计数一致性。
/// </summary>
public sealed class Discussion
{
    private readonly List<DiscussionReply> _replies = [];

    /// <summary>讨论唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>所属题目 Id</summary>
    public Guid ProblemId { get; private set; }

    /// <summary>发帖用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>标题</summary>
    public string Title { get; private set; } = string.Empty;

    /// <summary>正文</summary>
    public string Content { get; private set; } = string.Empty;

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    /// <summary>回复数(冗余计数,便于列表展示)</summary>
    public int ReplyCount { get; private set; }

    /// <summary>回复集合(聚合内实体)</summary>
    public IReadOnlyList<DiscussionReply> Replies => _replies.AsReadOnly();

    // EF Core 构造函数
    private Discussion() { }

    /// <summary>工厂方法:创建讨论帖</summary>
    public static Discussion Create(Guid problemId, Guid userId, string title, string content)
    {
        if (problemId == Guid.Empty)
            throw new DomainException("题目 Id 不能为空");
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");
        ValidateTitle(title);
        ValidateContent(content);

        return new Discussion
        {
            Id = Guid.NewGuid(),
            ProblemId = problemId,
            UserId = userId,
            Title = title.Trim(),
            Content = content,
            CreatedAt = DateTime.UtcNow
        };
    }

    /// <summary>添加回复,返回创建的 DiscussionReply(供仓储显式 Add)</summary>
    public DiscussionReply AddReply(Guid userId, string content)
    {
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");
        ValidateContent(content);

        var reply = DiscussionReply.Create(Id, userId, content);
        _replies.Add(reply);
        ReplyCount++;
        return reply;
    }

    #region 校验
    private static void ValidateTitle(string title)
    {
        if (string.IsNullOrWhiteSpace(title))
            throw new DomainException("讨论标题不能为空");
        if (title.Length > 200)
            throw new DomainException("讨论标题长度不能超过 200");
    }

    private static void ValidateContent(string content)
    {
        if (string.IsNullOrWhiteSpace(content))
            throw new DomainException("内容不能为空");
    }
    #endregion
}

/// <summary>
/// 讨论回复(聚合内实体,通过 Discussion 聚合根管理)。
/// </summary>
public sealed class DiscussionReply
{
    /// <summary>回复唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>所属讨论 Id</summary>
    public Guid DiscussionId { get; private set; }

    /// <summary>回复用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>回复正文</summary>
    public string Content { get; private set; } = string.Empty;

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    private DiscussionReply() { }

    internal static DiscussionReply Create(Guid discussionId, Guid userId, string content)
    {
        return new DiscussionReply
        {
            Id = Guid.NewGuid(),
            DiscussionId = discussionId,
            UserId = userId,
            Content = content,
            CreatedAt = DateTime.UtcNow
        };
    }
}
