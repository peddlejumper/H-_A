namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 收藏实体 —— 记录用户对题目的收藏关系。
/// UserId + ProblemId 唯一(防重复收藏)。
/// </summary>
public sealed class Favorite
{
    /// <summary>收藏唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>题目 Id</summary>
    public Guid ProblemId { get; private set; }

    /// <summary>收藏时间</summary>
    public DateTime CreatedAt { get; private set; }

    // EF Core 构造函数
    private Favorite() { }

    /// <summary>工厂方法:创建收藏</summary>
    public static Favorite Create(Guid userId, Guid problemId)
    {
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");
        if (problemId == Guid.Empty)
            throw new DomainException("题目 Id 不能为空");

        return new Favorite
        {
            Id = Guid.NewGuid(),
            UserId = userId,
            ProblemId = problemId,
            CreatedAt = DateTime.UtcNow
        };
    }
}
