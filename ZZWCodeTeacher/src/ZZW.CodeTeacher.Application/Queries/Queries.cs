namespace ZZW.CodeTeacher.Application.Queries;

using MediatR;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Domain.Enums;

// ═════════════════════════ 题目查询 ═════════════════════════

/// <summary>获取题目详情</summary>
public record GetProblemByIdQuery(Guid Id) : IRequest<ProblemDto?>;

/// <summary>分页查询题目列表</summary>
public record ListProblemsQuery(
    int Page = 1, int PageSize = 20,
    DifficultyLevel? Difficulty = null,
    bool? IsActive = null,
    string? Search = null) : IRequest<PagedResult<ProblemListItemDto>>;

// ═════════════════════════ 用户查询 ═════════════════════════

/// <summary>获取当前用户信息</summary>
public record GetCurrentUserQuery() : IRequest<UserDto?>;

/// <summary>分页查询用户列表</summary>
public record ListUsersQuery(
    int Page = 1, int PageSize = 20,
    UserRole? Role = null, bool? IsActive = null,
    string? Search = null) : IRequest<PagedResult<UserDto>>;

// ═════════════════════════ 提交查询 ═════════════════════════

/// <summary>获取提交详情</summary>
public record GetSubmissionByIdQuery(Guid Id) : IRequest<SubmissionDto?>;

/// <summary>按用户查询提交记录</summary>
public record ListSubmissionsByUserQuery(
    Guid UserId, int Page = 1, int PageSize = 20) : IRequest<PagedResult<SubmissionDto>>;

/// <summary>分页查询全部提交</summary>
public record ListAllSubmissionsQuery(
    int Page = 1, int PageSize = 20,
    SubmissionStatus? Status = null) : IRequest<PagedResult<SubmissionDto>>;

/// <summary>查询某用户的错题本(未通过的提交,按题目去重取最近一次)</summary>
public record ListWrongSubmissionsQuery(
    Guid UserId, int Page = 1, int PageSize = 50) : IRequest<PagedResult<SubmissionDto>>;

// ═════════════════════════ 统计查询 ═════════════════════════

/// <summary>获取仪表盘统计数据（TREA 风格前端用）</summary>
public record GetDashboardStatsQuery() : IRequest<DashboardStatsDto>;

// ═════════════════════════ 收藏查询 ═════════════════════════

/// <summary>列出我的收藏(分页)。UserId 从 ICurrentUser 获取</summary>
public record ListFavoritesQuery(int Page = 1, int PageSize = 20) : IRequest<PagedResult<ProblemListItemDto>>;

// ═════════════════════════ 打卡查询 ═════════════════════════

/// <summary>获取当前用户打卡状态。UserId 从 ICurrentUser 获取</summary>
public record GetCheckInStatusQuery() : IRequest<CheckInResultDto>;

// ═════════════════════════ 讨论查询 ═════════════════════════

/// <summary>分页查询某题目的讨论列表</summary>
public record ListDiscussionsQuery(Guid ProblemId, int Page = 1, int PageSize = 20)
    : IRequest<PagedResult<DiscussionListItemDto>>;

/// <summary>查询某讨论的回复列表</summary>
public record ListRepliesQuery(Guid DiscussionId) : IRequest<IReadOnlyList<DiscussionReplyDto>>;

// ═════════════════════════ 题解查询 ═════════════════════════

/// <summary>分页查询某题目的题解列表(sort=hot|new|accepted)</summary>
public record ListSolutionsQuery(Guid ProblemId, int Page = 1, int PageSize = 20, string Sort = "hot")
    : IRequest<PagedResult<SolutionListItemDto>>;

/// <summary>获取题解详情</summary>
public record GetSolutionQuery(Guid Id) : IRequest<SolutionDto?>;

// ═════════════════════════ 公告查询 ═════════════════════════

/// <summary>分页查询公告列表(学员看 active,教师看全部)</summary>
public record ListAnnouncementsQuery(bool ActiveOnly, int Page = 1, int PageSize = 20)
    : IRequest<PagedResult<AnnouncementListItemDto>>;

// ═════════════════════════ 排行榜查询 ═════════════════════════

/// <summary>多维排行榜查询(scope=week|month|all,可选 language 过滤)</summary>
public record LeaderboardQuery(LeaderboardScope Scope, SupportedLanguage? Language = null)
    : IRequest<IReadOnlyList<TopUserDto>>;

// ═════════════════════════ 学员进度查询 ═════════════════════════

/// <summary>查询单学员学习进度</summary>
public record GetUserProgressQuery(Guid UserId) : IRequest<UserProgressDto>;

// ═════════════════════════ 题目导出查询 ═════════════════════════

/// <summary>导出题目(全部或按 ids)</summary>
public record ExportProblemsQuery(IReadOnlyList<Guid>? Ids = null)
    : IRequest<IReadOnlyList<ProblemDto>>;

// ═════════════════════════ AI 题目推荐查询 ═════════════════════════

/// <summary>获取推荐题目(错题驱动)。UserId 从 ICurrentUser 获取</summary>
public record GetRecommendedProblemsQuery(int Limit = 5)
    : IRequest<IReadOnlyList<RecommendedProblemDto>>;

// ═════════════════════════ 班级查询 ═════════════════════════

/// <summary>列出我的班级</summary>
public record ListMyGroupsQuery() : IRequest<IReadOnlyList<GroupDto>>;

/// <summary>列出班级成员</summary>
public record ListGroupMembersQuery(Guid GroupId) : IRequest<IReadOnlyList<GroupMemberDto>>;

// ═════════════════════════ 错题复习查询 ═════════════════════════

/// <summary>查询今日待复习项。UserId 从 ICurrentUser 获取</summary>
public record GetDueReviewsQuery() : IRequest<IReadOnlyList<ReviewItemDto>>;

// ═════════════════════════ 博客查询 ═════════════════════════

/// <summary>分页查询博客列表(默认仅已发布)</summary>
public record ListBlogPostsQuery(int Page = 1, int PageSize = 20, string? Search = null)
    : IRequest<PagedResult<BlogPostListItemDto>>;

/// <summary>获取博客文章详情(同时增加浏览量)</summary>
public record GetBlogPostQuery(Guid Id) : IRequest<BlogPostDto?>;

// ═════════════════════════ 知识点查询 ═════════════════════════

/// <summary>获取知识点树</summary>
public record GetKnowledgeTreeQuery() : IRequest<IReadOnlyList<KnowledgePointDto>>;

/// <summary>按知识点查询题目</summary>
public record GetProblemsByKnowledgePointQuery(Guid KnowledgePointId)
    : IRequest<IReadOnlyList<ProblemListItemDto>>;
