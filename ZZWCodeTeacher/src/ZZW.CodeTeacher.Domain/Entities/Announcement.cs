namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 教师公告聚合根 —— 教师发布、学员接收的通知。
/// </summary>
public sealed class Announcement
{
    /// <summary>公告唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>标题</summary>
    public string Title { get; private set; } = string.Empty;

    /// <summary>正文</summary>
    public string Content { get; private set; } = string.Empty;

    /// <summary>作者(教师)用户 Id</summary>
    public Guid AuthorId { get; private set; }

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    /// <summary>是否启用(下架则学员不可见)</summary>
    public bool IsActive { get; private set; }

    /// <summary>是否置顶</summary>
    public bool Pinned { get; private set; }

    // EF Core 构造函数
    private Announcement() { }

    /// <summary>工厂方法:创建公告</summary>
    public static Announcement Create(Guid authorId, string title, string content,
        bool pinned = false)
    {
        if (authorId == Guid.Empty)
            throw new DomainException("作者 Id 不能为空");
        if (string.IsNullOrWhiteSpace(title))
            throw new DomainException("公告标题不能为空");
        if (title.Length > 200)
            throw new DomainException("公告标题长度不能超过 200");
        if (string.IsNullOrWhiteSpace(content))
            throw new DomainException("公告内容不能为空");

        return new Announcement
        {
            Id = Guid.NewGuid(),
            AuthorId = authorId,
            Title = title.Trim(),
            Content = content,
            IsActive = true,
            Pinned = pinned,
            CreatedAt = DateTime.UtcNow
        };
    }

    /// <summary>启用/下架</summary>
    public void SetActive(bool active)
    {
        IsActive = active;
    }

    /// <summary>置顶/取消置顶</summary>
    public void SetPinned(bool pinned)
    {
        Pinned = pinned;
    }
}

/// <summary>
/// 公告已读记录 —— 同用户同公告唯一。
/// </summary>
public sealed class AnnouncementRead
{
    /// <summary>记录唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>公告 Id</summary>
    public Guid AnnouncementId { get; private set; }

    /// <summary>用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>已读时间</summary>
    public DateTime ReadAt { get; private set; }

    private AnnouncementRead() { }

    public static AnnouncementRead Create(Guid announcementId, Guid userId)
    {
        if (announcementId == Guid.Empty)
            throw new DomainException("公告 Id 不能为空");
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");

        return new AnnouncementRead
        {
            Id = Guid.NewGuid(),
            AnnouncementId = announcementId,
            UserId = userId,
            ReadAt = DateTime.UtcNow
        };
    }
}
