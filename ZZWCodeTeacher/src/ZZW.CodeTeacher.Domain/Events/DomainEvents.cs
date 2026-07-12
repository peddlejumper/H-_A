namespace ZZW.CodeTeacher.Domain.Events;

/// <summary>
/// 领域事件标记接口。所有领域事件实现此接口，由基础设施层发布到消息总线。
/// </summary>
public interface IDomainEvent
{
    Guid AggregateId { get; }
    DateTime OccurredOn { get; }
}

public abstract record DomainEventBase(Guid AggregateId) : IDomainEvent
{
    public DateTime OccurredOn { get; } = DateTime.UtcNow;
}

/// <summary>题目创建事件</summary>
public sealed record ProblemCreatedEvent(Guid ProblemId, string Code)
    : DomainEventBase(ProblemId);

/// <summary>题目状态变更事件</summary>
public sealed record ProblemStatusChangedEvent(Guid ProblemId, string Code, bool IsActive)
    : DomainEventBase(ProblemId);

/// <summary>用户创建事件</summary>
public sealed record UserCreatedEvent(Guid UserId, string Username, Enums.UserRole Role)
    : DomainEventBase(UserId);

/// <summary>提交创建事件</summary>
public sealed record SubmissionCreatedEvent(Guid SubmissionId, Guid ProblemId, Guid UserId)
    : DomainEventBase(SubmissionId);

/// <summary>提交测评完成事件</summary>
public sealed record SubmissionJudgedEvent(
    Guid SubmissionId, Guid ProblemId, Guid UserId,
    Enums.SubmissionStatus Status, int Score) : DomainEventBase(SubmissionId);
