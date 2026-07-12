namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 每日打卡实体 —— 记录用户的学习打卡(每日一次)。
/// UserId + CheckInDate 唯一(同用户同日不可重复打卡)。
/// </summary>
public sealed class CheckIn
{
    /// <summary>打卡唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>打卡日期(UTC)</summary>
    public DateOnly CheckInDate { get; private set; }

    /// <summary>记录创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    // EF Core 构造函数
    private CheckIn() { }

    /// <summary>工厂方法:创建打卡记录</summary>
    public static CheckIn Create(Guid userId, DateOnly checkInDate)
    {
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");

        return new CheckIn
        {
            Id = Guid.NewGuid(),
            UserId = userId,
            CheckInDate = checkInDate,
            CreatedAt = DateTime.UtcNow
        };
    }
}
