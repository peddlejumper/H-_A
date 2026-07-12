namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Events;
using ZZW.CodeTeacher.Domain.Exceptions;
using ZZW.CodeTeacher.Domain.ValueObjects;

/// <summary>
/// 用户聚合根。
/// </summary>
public sealed class User
{
    private readonly List<IDomainEvent> _domainEvents = [];

    public Guid Id { get; private set; }
    public string Username { get; private set; } = string.Empty;
    public string Email { get; private set; } = string.Empty;
    public string PasswordHash { get; private set; } = string.Empty;
    public string DisplayName { get; private set; } = string.Empty;
    public UserRole Role { get; private set; }
    public bool IsActive { get; private set; }
    public DateTime CreatedAt { get; private set; }
    public DateTime? LastLoginAt { get; private set; }

    public IReadOnlyList<IDomainEvent> DomainEvents => _domainEvents.AsReadOnly();

    private User() { }

    public static User Create(string username, string email, string passwordHash,
        string displayName, UserRole role = UserRole.Student)
    {
        ValidateUsername(username);
        ValidateEmail(email);

        var user = new User
        {
            Id = Guid.NewGuid(),
            Username = username.Trim(),
            Email = email.Trim().ToLowerInvariant(),
            PasswordHash = passwordHash,
            DisplayName = string.IsNullOrWhiteSpace(displayName) ? username.Trim() : displayName.Trim(),
            Role = role,
            IsActive = true,
            CreatedAt = DateTime.UtcNow
        };
        user._domainEvents.Add(new UserCreatedEvent(user.Id, user.Username, user.Role));
        return user;
    }

    public void UpdateProfile(string? displayName, UserRole? role)
    {
        if (displayName is not null) DisplayName = displayName.Trim();
        if (role is not null) Role = role.Value;
    }

    public void RecordLogin() => LastLoginAt = DateTime.UtcNow;

    public void SetActive(bool active)
    {
        if (IsActive == active) return;
        IsActive = active;
    }

    public void ChangePassword(string newPasswordHash)
    {
        if (string.IsNullOrWhiteSpace(newPasswordHash))
            throw new DomainException("密码哈希不能为空");
        PasswordHash = newPasswordHash;
    }

    public void ClearDomainEvents() => _domainEvents.Clear();

    private static void ValidateUsername(string username)
    {
        if (string.IsNullOrWhiteSpace(username))
            throw new DomainException("用户名不能为空");
        if (username.Length is < 3 or > 32)
            throw new DomainException("用户名长度必须在 3 ~ 32 之间");
    }

    private static void ValidateEmail(string email)
    {
        if (string.IsNullOrWhiteSpace(email))
            throw new DomainException("邮箱不能为空");
        if (!email.Contains('@'))
            throw new DomainException("邮箱格式不合法");
    }
}

/// <summary>
/// 提交记录聚合根 —— 记录学生的一次代码提交与测评结果。
/// </summary>
public sealed class Submission
{
    private readonly List<IDomainEvent> _domainEvents = [];

    public Guid Id { get; private set; }
    public Guid ProblemId { get; private set; }
    public Guid UserId { get; private set; }
    public CodeSnapshot Code { get; private set; }
    public SubmissionStatus Status { get; private set; }
    public JudgeReport? Report { get; private set; }
    public string? ErrorMessage { get; private set; }
    public int Score { get; private set; }
    public DateTime SubmittedAt { get; private set; }
    public DateTime? JudgedAt { get; private set; }

    public IReadOnlyList<IDomainEvent> DomainEvents => _domainEvents.AsReadOnly();

    private Submission() { }

    public static Submission Create(Guid problemId, Guid userId, string code, SupportedLanguage language)
    {
        var snapshot = CodeSnapshot.Create(code, language);
        var submission = new Submission
        {
            Id = Guid.NewGuid(),
            ProblemId = problemId,
            UserId = userId,
            Code = snapshot,
            Status = SubmissionStatus.Pending,
            Score = 0,
            SubmittedAt = DateTime.UtcNow
        };
        submission._domainEvents.Add(new SubmissionCreatedEvent(submission.Id, problemId, userId));
        return submission;
    }

    public void MarkRunning()
    {
        if (Status != SubmissionStatus.Pending)
            throw new DomainException($"不能将状态从 {Status} 切换到 Running");
        Status = SubmissionStatus.Running;
    }

    public void SetResult(JudgeReport report, SubmissionStatus? finalStatus = null)
    {
        Report = report;
        JudgedAt = DateTime.UtcNow;
        // 若评测器给出了明确状态(如 CompileError/TLE/RuntimeError)则优先采用;
        // 否则按通过/失败二选一
        Status = finalStatus ?? (report.AllPassed
            ? SubmissionStatus.Accepted
            : SubmissionStatus.WrongAnswer);
        Score = (int)Math.Round(report.PassRate * 100);
        _domainEvents.Add(new SubmissionJudgedEvent(Id, ProblemId, UserId, Status, Score));
    }

    public void MarkError(string errorMessage)
    {
        ErrorMessage = errorMessage;
        Status = SubmissionStatus.RuntimeError;
        JudgedAt = DateTime.UtcNow;
        Score = 0;
    }

    public void ClearDomainEvents() => _domainEvents.Clear();
}
