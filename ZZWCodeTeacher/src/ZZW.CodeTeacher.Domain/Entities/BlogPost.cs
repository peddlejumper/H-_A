namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 博客/知识分享聚合根 —— 用户发布技术文章(Markdown),支持点赞与浏览计数。
/// </summary>
public sealed class BlogPost
{
    /// <summary>文章唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>作者用户 Id</summary>
    public Guid AuthorId { get; private set; }

    /// <summary>标题</summary>
    public string Title { get; private set; } = string.Empty;

    /// <summary>摘要</summary>
    public string Summary { get; private set; } = string.Empty;

    /// <summary>正文(Markdown)</summary>
    public string Content { get; private set; } = string.Empty;

    /// <summary>标签</summary>
    public IReadOnlyList<string> Tags { get; private set; } = [];

    /// <summary>浏览数</summary>
    public int ViewCount { get; private set; }

    /// <summary>点赞数</summary>
    public int LikeCount { get; private set; }

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    /// <summary>更新时间</summary>
    public DateTime UpdatedAt { get; private set; }

    /// <summary>是否已发布(草稿/已发布)</summary>
    public bool IsPublished { get; private set; }

    // EF Core 构造函数
    private BlogPost() { }

    /// <summary>工厂方法:创建文章</summary>
    public static BlogPost Create(Guid authorId, string title, string summary,
        string content, IEnumerable<string>? tags = null, bool isPublished = true)
    {
        if (authorId == Guid.Empty)
            throw new DomainException("作者 Id 不能为空");
        if (string.IsNullOrWhiteSpace(title))
            throw new DomainException("文章标题不能为空");
        if (title.Length > 200)
            throw new DomainException("文章标题长度不能超过 200");
        if (string.IsNullOrWhiteSpace(content))
            throw new DomainException("文章内容不能为空");

        var now = DateTime.UtcNow;
        return new BlogPost
        {
            Id = Guid.NewGuid(),
            AuthorId = authorId,
            Title = title.Trim(),
            Summary = summary ?? string.Empty,
            Content = content,
            Tags = tags?.ToList().AsReadOnly() ?? [],
            ViewCount = 0,
            LikeCount = 0,
            IsPublished = isPublished,
            CreatedAt = now,
            UpdatedAt = now
        };
    }

    /// <summary>更新文章</summary>
    public void Update(string? title, string? summary, string? content,
        IEnumerable<string>? tags, bool? isPublished)
    {
        if (title is not null)
        {
            if (string.IsNullOrWhiteSpace(title))
                throw new DomainException("文章标题不能为空");
            Title = title.Trim();
        }
        if (summary is not null) Summary = summary;
        if (content is not null)
        {
            if (string.IsNullOrWhiteSpace(content))
                throw new DomainException("文章内容不能为空");
            Content = content;
        }
        if (tags is not null) Tags = tags.ToList().AsReadOnly();
        if (isPublished is not null) IsPublished = isPublished.Value;
        UpdatedAt = DateTime.UtcNow;
    }

    /// <summary>增加浏览量</summary>
    public void IncrementView() => ViewCount++;

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
}

/// <summary>
/// 博客文章点赞实体 —— 同用户同文章唯一。
/// </summary>
public sealed class BlogLike
{
    /// <summary>点赞唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>文章 Id</summary>
    public Guid BlogPostId { get; private set; }

    /// <summary>点赞用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>点赞时间</summary>
    public DateTime CreatedAt { get; private set; }

    private BlogLike() { }

    public static BlogLike Create(Guid blogPostId, Guid userId)
    {
        if (blogPostId == Guid.Empty)
            throw new DomainException("文章 Id 不能为空");
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");

        return new BlogLike
        {
            Id = Guid.NewGuid(),
            BlogPostId = blogPostId,
            UserId = userId,
            CreatedAt = DateTime.UtcNow
        };
    }
}
