namespace ZZW.CodeTeacher.Application.Commands;

using MediatR;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Domain.Enums;

// ═════════════════════════ 题目命令 ═════════════════════════

/// <summary>创建题目命令</summary>
public record CreateProblemCommand(
    string Code, string Title, string Description,
    DifficultyLevel Difficulty, int TimeLimitMs, int MemoryLimitKb,
    string Template, IReadOnlyList<string> Tags,
    IReadOnlyList<SupportedLanguage> SupportedLanguages) : IRequest<ProblemDto>;

/// <summary>更新题目命令</summary>
public record UpdateProblemCommand(
    Guid Id, string? Title, string? Description, DifficultyLevel? Difficulty,
    int? TimeLimitMs, int? MemoryLimitKb, string? Template,
    IReadOnlyList<string>? Tags,
    IReadOnlyList<SupportedLanguage>? SupportedLanguages = null) : IRequest<ProblemDto>;

/// <summary>添加测试用例命令</summary>
public record AddTestCaseCommand(
    Guid ProblemId, string Input, string ExpectedOutput, bool IsSample) : IRequest<Unit>;

/// <summary>删除题目命令</summary>
public record DeleteProblemCommand(Guid Id) : IRequest<Unit>;

/// <summary>切换题目启用状态命令</summary>
public record ToggleProblemCommand(Guid Id, bool IsActive) : IRequest<Unit>;

// ═════════════════════════ 用户命令 ═════════════════════════

/// <summary>注册命令</summary>
public record RegisterCommand(
    string Username, string Email, string Password, string DisplayName) : IRequest<AuthResultDto>;

/// <summary>登录命令</summary>
public record LoginCommand(string Username, string Password) : IRequest<AuthResultDto>;

/// <summary>更新用户角色命令</summary>
public record UpdateUserRoleCommand(Guid UserId, UserRole Role) : IRequest<UserDto>;

// ═════════════════════════ 提交命令 ═════════════════════════

/// <summary>提交代码命令</summary>
public record SubmitCodeCommand(Guid ProblemId, string Code, SupportedLanguage Language) : IRequest<SubmissionDto>;

/// <summary>重新评测命令</summary>
public record RejudgeCommand(Guid SubmissionId) : IRequest<SubmissionDto>;

// ═════════════════════════ 收藏命令 ═════════════════════════

/// <summary>切换收藏命令(已收藏则取消,未收藏则添加)。UserId 从 ICurrentUser 获取</summary>
public record ToggleFavoriteCommand(Guid ProblemId) : IRequest<bool>;

// ═════════════════════════ 打卡命令 ═════════════════════════

/// <summary>每日打卡命令。UserId 从 ICurrentUser 获取</summary>
public record CheckInCommand() : IRequest<CheckInResultDto>;

// ═════════════════════════ 讨论命令 ═════════════════════════

/// <summary>创建讨论命令。UserId 从 ICurrentUser 获取</summary>
public record CreateDiscussionCommand(Guid ProblemId, string Title, string Content) : IRequest<DiscussionDto>;

/// <summary>创建回复命令。UserId 从 ICurrentUser 获取</summary>
public record CreateReplyCommand(Guid DiscussionId, string Content) : IRequest<DiscussionReplyDto>;

// ═════════════════════════ 题解命令 ═════════════════════════

/// <summary>创建题解命令。UserId 从 ICurrentUser 获取</summary>
public record CreateSolutionCommand(
    Guid ProblemId, string Title, string Content,
    string? Code, SupportedLanguage? Language) : IRequest<SolutionDto>;

/// <summary>切换题解点赞命令。UserId 从 ICurrentUser 获取</summary>
public record ToggleLikeSolutionCommand(Guid SolutionId) : IRequest<ToggleLikeResultDto>;

/// <summary>采纳题解命令(题目作者或教师可调)</summary>
public record AcceptSolutionCommand(Guid SolutionId) : IRequest<Unit>;

// ═════════════════════════ 公告命令 ═════════════════════════

/// <summary>创建公告命令(教师)。AuthorId 从 ICurrentUser 获取</summary>
public record CreateAnnouncementCommand(string Title, string Content, bool Pinned = false)
    : IRequest<AnnouncementDto>;

/// <summary>标记公告已读命令。UserId 从 ICurrentUser 获取</summary>
public record MarkAnnouncementReadCommand(Guid AnnouncementId) : IRequest<Unit>;

/// <summary>删除公告命令(教师)</summary>
public record DeleteAnnouncementCommand(Guid Id) : IRequest<Unit>;

// ═════════════════════════ 题目批量导入命令 ═════════════════════════

/// <summary>批量导入题目命令(教师)。逐条创建并汇总结果</summary>
public record BulkImportProblemsCommand(IReadOnlyList<CreateProblemDto> Items)
    : IRequest<BulkImportResultDto>;

// ═════════════════════════ 班级/小组命令 ═════════════════════════

/// <summary>创建班级命令。CreatorId 从 ICurrentUser 获取</summary>
public record CreateGroupCommand(string Name, string Description) : IRequest<GroupDto>;

/// <summary>加入班级命令。UserId 从 ICurrentUser 获取</summary>
public record JoinGroupCommand(string InviteCode) : IRequest<GroupDto>;

/// <summary>移除班级成员命令(仅 Owner 可调)</summary>
public record RemoveGroupMemberCommand(Guid GroupId, Guid UserId) : IRequest<Unit>;

// ═════════════════════════ 错题复习(SM-2)命令 ═════════════════════════

/// <summary>复习评分命令(quality 0~5,触发 SM-2 更新)</summary>
public record ScheduleReviewCommand(Guid ProblemId, int Quality) : IRequest<ReviewItemDto>;

// ═════════════════════════ 博客命令 ═════════════════════════

/// <summary>创建博客文章命令。AuthorId 从 ICurrentUser 获取</summary>
public record CreateBlogPostCommand(
    string Title, string Summary, string Content,
    IReadOnlyList<string> Tags, bool IsPublished = true) : IRequest<BlogPostDto>;

/// <summary>切换博客点赞命令。UserId 从 ICurrentUser 获取</summary>
public record ToggleBlogLikeCommand(Guid BlogPostId) : IRequest<ToggleLikeResultDto>;

// ═════════════════════════ 知识点命令 ═════════════════════════

/// <summary>创建知识点命令</summary>
public record CreateKnowledgePointCommand(string Name, string Description, Guid? ParentId = null)
    : IRequest<KnowledgePointDto>;

/// <summary>关联题目与知识点命令</summary>
public record LinkProblemKnowledgePointCommand(Guid ProblemId, Guid KnowledgePointId)
    : IRequest<Unit>;
