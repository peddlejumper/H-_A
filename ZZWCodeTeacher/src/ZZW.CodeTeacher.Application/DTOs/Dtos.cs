namespace ZZW.CodeTeacher.Application.DTOs;

using ZZW.CodeTeacher.Domain.Enums;

/// <summary>测试样例(题目详情用,供学员 IDE 显示)</summary>
public record ProblemSampleDto(string Input, string Output);

/// <summary>题目 DTO(init 属性风格,AutoMapper 用无参构造 + 属性设置)</summary>
public record ProblemDto
{
    public Guid Id { get; init; }
    public string Code { get; init; } = "";
    public string Title { get; init; } = "";
    public string Description { get; init; } = "";
    public DifficultyLevel Difficulty { get; init; }
    public int TimeLimitMs { get; init; }
    public int MemoryLimitKb { get; init; }
    public string Template { get; init; } = "";
    public IReadOnlyList<string> Tags { get; init; } = [];
    public IReadOnlyList<SupportedLanguage> SupportedLanguages { get; init; } = [];
    public bool IsActive { get; init; }
    public int TestCaseCount { get; init; }
    public IReadOnlyList<ProblemSampleDto> Samples { get; init; } = [];
    public DateTime CreatedAt { get; init; }
}

/// <summary>题目列表项(精简)</summary>
public record ProblemListItemDto(
    Guid Id,
    string Code,
    string Title,
    DifficultyLevel Difficulty,
    IReadOnlyList<SupportedLanguage> SupportedLanguages,
    bool IsActive,
    int TestCaseCount,
    int SubmitCount,
    int PassCount);

/// <summary>创建题目 DTO</summary>
public record CreateProblemDto(
    string Code,
    string Title,
    string Description,
    DifficultyLevel Difficulty,
    int TimeLimitMs,
    int MemoryLimitKb,
    string Template,
    IReadOnlyList<string> Tags,
    IReadOnlyList<SupportedLanguage> SupportedLanguages);

/// <summary>更新题目 DTO</summary>
public record UpdateProblemDto(
    string? Title,
    string? Description,
    DifficultyLevel? Difficulty,
    int? TimeLimitMs,
    int? MemoryLimitKb,
    string? Template,
    IReadOnlyList<string>? Tags,
    IReadOnlyList<SupportedLanguage>? SupportedLanguages);

/// <summary>添加测试用例 DTO</summary>
public record AddTestCaseDto(string Input, string ExpectedOutput, bool IsSample);

/// <summary>用户 DTO</summary>
public record UserDto(
    Guid Id,
    string Username,
    string Email,
    string DisplayName,
    UserRole Role,
    bool IsActive,
    DateTime CreatedAt,
    DateTime? LastLoginAt);

/// <summary>登录 DTO</summary>
public record LoginDto(string Username, string Password);

/// <summary>登录结果 DTO（含 JWT）</summary>
public record AuthResultDto(string AccessToken, string TokenType, int ExpiresIn, UserDto User);

/// <summary>注册 DTO</summary>
public record RegisterDto(
    string Username, string Email, string Password, string DisplayName);

/// <summary>单个测试用例的评测明细</summary>
public record CaseResultDto(
    int Index,
    bool Passed,
    long ElapsedMs,
    long MemoryKb,
    string? Expected,
    string? Actual,
    string? Error);

/// <summary>提交记录 DTO(init 属性风格,AutoMapper 用无参构造 + 属性设置)</summary>
public record SubmissionDto
{
    public Guid Id { get; init; }
    public Guid ProblemId { get; init; }
    public string ProblemCode { get; init; } = "";
    public string ProblemTitle { get; init; } = "";
    public Guid UserId { get; init; }
    public string Username { get; init; } = "";
    public string Code { get; init; } = "";
    public SupportedLanguage Language { get; init; }
    public int LineCount { get; init; }
    public SubmissionStatus Status { get; init; }
    public int Score { get; init; }
    public int PassedCases { get; init; }
    public int TotalCases { get; init; }
    public long ElapsedMs { get; init; }
    public string? ErrorMessage { get; init; }
    public DateTime SubmittedAt { get; init; }
    public DateTime? JudgedAt { get; init; }
    /// <summary>每个测试用例的评测明细(错题分析用)</summary>
    public IReadOnlyList<CaseResultDto> Cases { get; init; } = [];
}

/// <summary>提交代码 DTO</summary>
public record SubmitCodeDto(Guid ProblemId, string Code, SupportedLanguage Language = SupportedLanguage.Python);

/// <summary>仪表盘统计 DTO</summary>
public record DashboardStatsDto(
    int TotalProblems,
    int ActiveProblems,
    int TotalUsers,
    int TotalSubmissions,
    int AcceptedSubmissions,
    double AcceptanceRate,
    IReadOnlyList<DifficultyDistributionDto> DifficultyDistribution,
    IReadOnlyList<DailySubmissionDto> RecentSubmissions,
    IReadOnlyList<TopUserDto> TopUsers)
{
    /// <summary>按语言维度的提交统计(后端扩展字段;未就绪时为空,客户端优雅降级)</summary>
    public IReadOnlyList<LanguageStatDto> ByLanguage { get; init; } = Array.Empty<LanguageStatDto>();
    /// <summary>按标签维度的提交统计(后端扩展字段;未就绪时为空,客户端优雅降级)</summary>
    public IReadOnlyList<TagStatDto> ByTag { get; init; } = Array.Empty<TagStatDto>();
}

public record DifficultyDistributionDto(DifficultyLevel Difficulty, int Count, int Total);

public record DailySubmissionDto(DateTime Date, int Submissions, int Accepted);

public record TopUserDto(Guid UserId, string Username, string DisplayName,
    int TotalSubmissions, int Accepted, double AcceptanceRate);

/// <summary>按标签维度的提交统计(Top N;后端扩展字段;客户端空集合时不报错)</summary>
public record TagStatDto(string Tag, int Count, int Accepted);

// ═════════════════════════ 收藏 DTO ═════════════════════════

/// <summary>收藏 DTO</summary>
public record FavoriteDto(Guid Id, Guid UserId, Guid ProblemId, DateTime CreatedAt);

// ═════════════════════════ 打卡 DTO ═════════════════════════

/// <summary>打卡结果 DTO</summary>
public record CheckInResultDto(int StreakDays, bool TodayCheckedIn, int TotalCheckIns);

// ═════════════════════════ 讨论 DTO ═════════════════════════

/// <summary>讨论详情 DTO</summary>
public record DiscussionDto(
    Guid Id,
    Guid ProblemId,
    Guid UserId,
    string Username,
    string Title,
    string Content,
    DateTime CreatedAt,
    int ReplyCount);

/// <summary>讨论列表项(精简)</summary>
public record DiscussionListItemDto(
    Guid Id,
    Guid ProblemId,
    string Title,
    Guid UserId,
    string Username,
    int ReplyCount,
    DateTime CreatedAt);

/// <summary>讨论回复 DTO</summary>
public record DiscussionReplyDto(
    Guid Id,
    Guid DiscussionId,
    Guid UserId,
    string Username,
    string Content,
    DateTime CreatedAt);

/// <summary>创建讨论 DTO</summary>
public record CreateDiscussionDto(string Title, string Content);

/// <summary>创建回复 DTO</summary>
public record CreateReplyDto(string Content);

/// <summary>分页结果</summary>
public record PagedResult<T>(IReadOnlyList<T> Items, int Total, int Page, int PageSize)
{
    public int TotalPages => (int)Math.Ceiling((double)Total / PageSize);
    public bool HasPrevious => Page > 1;
    public bool HasNext => Page < TotalPages;
}

/// <summary>统一 API 响应</summary>
public record ApiResponse<T>(bool Success, T? Data, string? Message, string? ErrorCode)
{
#pragma warning disable CA1000
    public static ApiResponse<T> Ok(T data) => new(true, data, null, null);
    public static ApiResponse<T> Fail(string message, string? code = null) =>
        new(false, default, message, code);
#pragma warning restore CA1000
}

// ═════════════════════════ 题解 DTO ═════════════════════════

/// <summary>题解详情 DTO</summary>
public record SolutionDto(
    Guid Id,
    Guid ProblemId,
    Guid UserId,
    string Username,
    string Title,
    string Content,
    string? Code,
    SupportedLanguage? Language,
    int LikeCount,
    bool IsAccepted,
    DateTime CreatedAt,
    DateTime UpdatedAt);

/// <summary>题解列表项(精简)</summary>
public record SolutionListItemDto(
    Guid Id,
    Guid ProblemId,
    Guid UserId,
    string Username,
    string Title,
    int LikeCount,
    bool IsAccepted,
    DateTime CreatedAt);

/// <summary>创建题解 DTO</summary>
public record CreateSolutionDto(
    string Title, string Content, string? Code, SupportedLanguage? Language);

/// <summary>切换点赞结果 DTO</summary>
public record ToggleLikeResultDto(bool Liked, int LikeCount);

// ═════════════════════════ 公告 DTO ═════════════════════════

/// <summary>公告详情 DTO</summary>
public record AnnouncementDto(
    Guid Id, string Title, string Content, Guid AuthorId, string AuthorName,
    DateTime CreatedAt, bool IsActive, bool Pinned)
{
    /// <summary>当前用户是否已读(客户端标记用;后端如未返回默认 false)。init 以支持 record with 表达式。</summary>
    public bool IsRead { get; init; }
}

/// <summary>公告列表项(含已读/置顶状态)</summary>
public record AnnouncementListItemDto(
    Guid Id, string Title, Guid AuthorId, string AuthorName,
    DateTime CreatedAt, bool IsActive, bool IsPinned, bool IsRead);

/// <summary>创建公告 DTO(教师用)</summary>
public record CreateAnnouncementDto(string Title, string Content, bool Pinned = false);

// ═════════════════════════ 用户进度 DTO ═════════════════════════

/// <summary>单学员进度 DTO</summary>
public record UserProgressDto(
    Guid UserId,
    string Username,
    int TotalSubmissions,
    int Accepted,
    double AcceptanceRate,
    IReadOnlyList<LanguageStatDto> ByLanguage,
    IReadOnlyList<DifficultyStatDto> ByDifficulty,
    IReadOnlyList<SubmissionDto> RecentWrong,
    IReadOnlyList<Guid> SolvedProblemIds);

/// <summary>按语言统计 DTO</summary>
public record LanguageStatDto(SupportedLanguage Language, int Submitted, int Accepted);

/// <summary>按难度统计 DTO</summary>
public record DifficultyStatDto(DifficultyLevel Difficulty, int Submitted, int Accepted);

/// <summary>排行榜查询作用域</summary>
public enum LeaderboardScope { Week, Month, All }

// ═════════════════════════ 题目批量导入/导出 DTO ═════════════════════════

/// <summary>批量导入题目 DTO</summary>
public record BulkImportProblemsDto(IReadOnlyList<CreateProblemDto> Items);

/// <summary>批量导入结果 DTO</summary>
public record BulkImportResultDto(
    int SuccessCount, int FailedCount, IReadOnlyList<BulkImportErrorDto> Errors);

/// <summary>批量导入错误项</summary>
public record BulkImportErrorDto(int Index, string Error);

// ═════════════════════════ 推荐题目 DTO ═════════════════════════

/// <summary>推荐题目 DTO</summary>
public record RecommendedProblemDto(
    Guid ProblemId, string Code, string Title, DifficultyLevel Difficulty, string Reason);

// ═════════════════════════ 班级/小组 DTO ═════════════════════════

/// <summary>班级 DTO</summary>
public record GroupDto(
    Guid Id, string Name, string Description, Guid CreatorId, string CreatorName,
    DateTime CreatedAt, string InviteCode, int MemberCount);

/// <summary>创建班级 DTO</summary>
public record CreateGroupDto(string Name, string Description);

/// <summary>加入班级 DTO</summary>
public record JoinGroupDto(string InviteCode);

/// <summary>班级成员 DTO</summary>
public record GroupMemberDto(
    Guid UserId, string Username, string DisplayName, string Role, DateTime JoinedAt);

// ═════════════════════════ 错题复习(SM-2) DTO ═════════════════════════

/// <summary>复习项 DTO</summary>
public record ReviewItemDto(
    Guid Id, Guid UserId, Guid ProblemId, string ProblemCode, string ProblemTitle,
    double EaseFactor, int Interval, int Repetitions,
    DateOnly NextReviewDate, DateTime? LastReviewedAt, DateTime CreatedAt);

/// <summary>复习评分 DTO(quality 0~5)</summary>
public record ScheduleReviewDto(int Quality);

// ═════════════════════════ 博客 DTO ═════════════════════════

/// <summary>博客文章详情 DTO</summary>
public record BlogPostDto(
    Guid Id, Guid AuthorId, string AuthorName, string Title, string Summary,
    string Content, IReadOnlyList<string> Tags, int ViewCount, int LikeCount,
    DateTime CreatedAt, DateTime UpdatedAt, bool IsPublished);

/// <summary>博客列表项(精简)</summary>
public record BlogPostListItemDto(
    Guid Id, Guid AuthorId, string AuthorName, string Title, string Summary,
    IReadOnlyList<string> Tags, int ViewCount, int LikeCount, DateTime CreatedAt);

/// <summary>创建博客文章 DTO</summary>
public record CreateBlogPostDto(
    string Title, string Summary, string Content, IReadOnlyList<string> Tags, bool IsPublished = true);

// ═════════════════════════ 知识点 DTO ═════════════════════════

/// <summary>知识点 DTO(树形)</summary>
public record KnowledgePointDto(
    Guid Id, string Name, string Description, Guid? ParentId,
    IReadOnlyList<KnowledgePointDto> Children);

/// <summary>创建知识点 DTO</summary>
public record CreateKnowledgePointDto(string Name, string Description, Guid? ParentId = null);

/// <summary>关联题目与知识点 DTO</summary>
public record LinkProblemKnowledgePointDto(Guid ProblemId, Guid KnowledgePointId);
