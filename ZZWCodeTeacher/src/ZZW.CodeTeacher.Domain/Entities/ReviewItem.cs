namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 错题复习项实体 —— 基于 SM-2 间隔重复算法安排错题复习计划。
/// 字段语义遵循 SuperMemo SM-2 标准(EaseFactor 默认 2.5,下限 1.3)。
/// </summary>
public sealed class ReviewItem
{
    /// <summary>复习项唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>题目 Id</summary>
    public Guid ProblemId { get; private set; }

    /// <summary>难度因子(EaseFactor,默认 2.5,下限 1.3)</summary>
    public double EaseFactor { get; private set; } = 2.5;

    /// <summary>下次复习间隔(天)</summary>
    public int Interval { get; private set; } = 1;

    /// <summary>已连续答对次数</summary>
    public int Repetitions { get; private set; }

    /// <summary>下次复习日期</summary>
    public DateOnly NextReviewDate { get; private set; }

    /// <summary>上次复习时间</summary>
    public DateTime? LastReviewedAt { get; private set; }

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    // EF Core 构造函数
    private ReviewItem() { }

    /// <summary>工厂方法:创建复习项(首次加入错题复习计划)</summary>
    public static ReviewItem Create(Guid userId, Guid problemId)
    {
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");
        if (problemId == Guid.Empty)
            throw new DomainException("题目 Id 不能为空");

        return new ReviewItem
        {
            Id = Guid.NewGuid(),
            UserId = userId,
            ProblemId = problemId,
            EaseFactor = 2.5,
            Interval = 1,
            Repetitions = 0,
            NextReviewDate = DateOnly.FromDateTime(DateTime.UtcNow),
            CreatedAt = DateTime.UtcNow
        };
    }

    /// <summary>
    /// SM-2 算法:根据评分(quality 0~5)更新 EaseFactor / Interval / Repetitions / NextReviewDate。
    /// quality: 0~2 视为答错(重置 Repetitions),3~5 视为答对。
    /// </summary>
    public void ScheduleReview(int quality)
    {
        if (quality < 0 || quality > 5)
            throw new DomainException("评分 quality 必须在 0~5 之间");

        // SM-2 公式
        if (quality < 3)
        {
            // 答错:重置
            Repetitions = 0;
            Interval = 1;
        }
        else
        {
            // 答对:递进
            Repetitions += 1;
            Interval = Repetitions switch
            {
                1 => 1,
                2 => 6,
                _ => (int)Math.Round(Interval * EaseFactor)
            };
        }

        // 更新 EaseFactor:EF' = EF + (0.1 - (5 - q)(0.08 + (5 - q) * 0.02)),下限 1.3
        var q = (double)quality;
        var newEf = EaseFactor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02));
        EaseFactor = Math.Max(1.3, Math.Round(newEf, 4));

        NextReviewDate = DateOnly.FromDateTime(DateTime.UtcNow.AddDays(Interval));
        LastReviewedAt = DateTime.UtcNow;
    }
}
