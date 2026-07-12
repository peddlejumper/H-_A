namespace ZZW.CodeTeacher.Domain.Repositories;

using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;

/// <summary>
/// 题目仓储接口 —— 定义在领域层，由基础设施层实现。
/// 使用规范模式（Specification）封装查询条件。
/// </summary>
public interface IProblemRepository
{
    Task<Problem?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<Problem?> GetByCodeAsync(string code, CancellationToken ct = default);
    Task<IReadOnlyList<Problem>> ListAsync(
        int page, int pageSize,
        DifficultyLevel? difficulty = null,
        bool? isActive = null,
        string? search = null,
        CancellationToken ct = default);
    Task<int> CountAsync(DifficultyLevel? difficulty = null, bool? isActive = null,
        string? search = null, CancellationToken ct = default);
    Task AddAsync(Problem problem, CancellationToken ct = default);
    Task UpdateAsync(Problem problem, CancellationToken ct = default);
    Task AddTestCaseAsync(TestCase testCase, CancellationToken ct = default);
    Task DeleteAsync(Guid id, CancellationToken ct = default);
}

/// <summary>用户仓储接口</summary>
public interface IUserRepository
{
    Task<User?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<User?> GetByUsernameAsync(string username, CancellationToken ct = default);
    Task<User?> GetByEmailAsync(string email, CancellationToken ct = default);
    Task<IReadOnlyList<User>> ListAsync(int page, int pageSize, UserRole? role = null,
        bool? isActive = null, string? search = null, CancellationToken ct = default);
    Task<int> CountAsync(UserRole? role = null, bool? isActive = null,
        string? search = null, CancellationToken ct = default);
    Task AddAsync(User user, CancellationToken ct = default);
    Task UpdateAsync(User user, CancellationToken ct = default);
    Task DeleteAsync(Guid id, CancellationToken ct = default);
}

/// <summary>提交记录仓储接口</summary>
public interface ISubmissionRepository
{
    Task<Submission?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<Submission>> ListByUserAsync(Guid userId, int page, int pageSize,
        CancellationToken ct = default);
    Task<int> CountByUserAsync(Guid userId, CancellationToken ct = default);
    Task<IReadOnlyList<Submission>> ListByProblemAsync(Guid problemId, int page, int pageSize,
        CancellationToken ct = default);
    Task<IReadOnlyList<Submission>> ListAllAsync(int page, int pageSize,
        SubmissionStatus? status = null, CancellationToken ct = default);
    Task<int> CountAsync(SubmissionStatus? status = null, CancellationToken ct = default);
    Task AddAsync(Submission submission, CancellationToken ct = default);
    Task UpdateAsync(Submission submission, CancellationToken ct = default);
}

/// <summary>收藏仓储接口</summary>
public interface IFavoriteRepository
{
    Task<Favorite?> GetAsync(Guid userId, Guid problemId, CancellationToken ct = default);
    Task<bool> ExistsAsync(Guid userId, Guid problemId, CancellationToken ct = default);
    Task AddAsync(Favorite favorite, CancellationToken ct = default);
    Task DeleteAsync(Guid userId, Guid problemId, CancellationToken ct = default);
    Task<IReadOnlyList<Favorite>> ListAsync(Guid userId, int page, int pageSize,
        CancellationToken ct = default);
    Task<int> CountAsync(Guid userId, CancellationToken ct = default);
}

/// <summary>每日打卡仓储接口</summary>
public interface ICheckInRepository
{
    Task<CheckIn?> GetAsync(Guid userId, DateOnly checkInDate, CancellationToken ct = default);
    Task AddAsync(CheckIn checkIn, CancellationToken ct = default);
    Task<IReadOnlyList<CheckIn>> ListByUserAsync(Guid userId, CancellationToken ct = default);
    Task<int> CountByUserAsync(Guid userId, CancellationToken ct = default);
}

/// <summary>讨论仓储接口</summary>
public interface IDiscussionRepository
{
    Task<Discussion?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<Discussion>> ListByProblemAsync(Guid problemId, int page, int pageSize,
        CancellationToken ct = default);
    Task<int> CountByProblemAsync(Guid problemId, CancellationToken ct = default);
    Task AddAsync(Discussion discussion, CancellationToken ct = default);
    Task UpdateAsync(Discussion discussion, CancellationToken ct = default);
    Task AddReplyAsync(DiscussionReply reply, CancellationToken ct = default);
    Task<IReadOnlyList<DiscussionReply>> ListRepliesAsync(Guid discussionId, CancellationToken ct = default);
}

/// <summary>题解仓储接口</summary>
public interface ISolutionRepository
{
    Task<Solution?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<Solution>> ListByProblemAsync(Guid problemId, int page, int pageSize,
        string? sort = null, CancellationToken ct = default);
    Task<int> CountByProblemAsync(Guid problemId, CancellationToken ct = default);
    Task AddAsync(Solution solution, CancellationToken ct = default);
    Task UpdateAsync(Solution solution, CancellationToken ct = default);
    Task<SolutionLike?> GetLikeAsync(Guid solutionId, Guid userId, CancellationToken ct = default);
    Task AddLikeAsync(SolutionLike solutionLike, CancellationToken ct = default);
    Task DeleteLikeAsync(Guid solutionId, Guid userId, CancellationToken ct = default);
}

/// <summary>公告仓储接口</summary>
public interface IAnnouncementRepository
{
    Task<Announcement?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<Announcement>> ListAsync(bool? activeOnly, int page, int pageSize,
        CancellationToken ct = default);
    Task<int> CountAsync(bool? activeOnly, CancellationToken ct = default);
    Task AddAsync(Announcement announcement, CancellationToken ct = default);
    Task DeleteAsync(Guid id, CancellationToken ct = default);
    Task<AnnouncementRead?> GetReadAsync(Guid announcementId, Guid userId, CancellationToken ct = default);
    Task AddReadAsync(AnnouncementRead read, CancellationToken ct = default);
    Task<IReadOnlyList<Guid>> ListReadIdsAsync(Guid userId, CancellationToken ct = default);
}

/// <summary>班级/小组仓储接口</summary>
public interface IGroupRepository
{
    Task<Group?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<Group?> GetByInviteCodeAsync(string inviteCode, CancellationToken ct = default);
    Task<IReadOnlyList<Group>> ListByUserAsync(Guid userId, CancellationToken ct = default);
    Task AddAsync(Group group, CancellationToken ct = default);
    Task AddMemberAsync(GroupMember member, CancellationToken ct = default);
    Task<GroupMember?> GetMemberAsync(Guid groupId, Guid userId, CancellationToken ct = default);
    Task<IReadOnlyList<GroupMember>> ListMembersAsync(Guid groupId, CancellationToken ct = default);
    Task DeleteMemberAsync(Guid groupId, Guid userId, CancellationToken ct = default);
}

/// <summary>错题复习项仓储接口(SM-2)</summary>
public interface IReviewItemRepository
{
    Task<ReviewItem?> GetAsync(Guid userId, Guid problemId, CancellationToken ct = default);
    Task<ReviewItem?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<ReviewItem>> ListDueAsync(Guid userId, DateOnly today, CancellationToken ct = default);
    Task<IReadOnlyList<ReviewItem>> ListByUserAsync(Guid userId, CancellationToken ct = default);
    Task AddAsync(ReviewItem item, CancellationToken ct = default);
    Task UpdateAsync(ReviewItem item, CancellationToken ct = default);
}

/// <summary>博客文章仓储接口</summary>
public interface IBlogPostRepository
{
    Task<BlogPost?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<BlogPost>> ListAsync(bool publishedOnly, int page, int pageSize,
        string? search = null, CancellationToken ct = default);
    Task<int> CountAsync(bool publishedOnly, string? search = null, CancellationToken ct = default);
    Task<IReadOnlyList<BlogPost>> ListByAuthorAsync(Guid authorId, CancellationToken ct = default);
    Task AddAsync(BlogPost post, CancellationToken ct = default);
    Task UpdateAsync(BlogPost post, CancellationToken ct = default);
    Task<BlogLike?> GetLikeAsync(Guid blogPostId, Guid userId, CancellationToken ct = default);
    Task AddLikeAsync(BlogLike blogLike, CancellationToken ct = default);
    Task DeleteLikeAsync(Guid blogPostId, Guid userId, CancellationToken ct = default);
}

/// <summary>知识点仓储接口</summary>
public interface IKnowledgePointRepository
{
    Task<KnowledgePoint?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<KnowledgePoint>> ListAllAsync(CancellationToken ct = default);
    Task AddAsync(KnowledgePoint kp, CancellationToken ct = default);
    Task<IReadOnlyList<ProblemKnowledgePoint>> ListByKnowledgePointAsync(Guid kpId, CancellationToken ct = default);
    Task<IReadOnlyList<ProblemKnowledgePoint>> ListByProblemAsync(Guid problemId, CancellationToken ct = default);
    Task AddLinkAsync(ProblemKnowledgePoint link, CancellationToken ct = default);
}

/// <summary>题解点赞关联仓储(独立查询用,主操作走 ISolutionRepository)</summary>
public interface ISolutionLikeRepository
{
    Task<SolutionLike?> GetAsync(Guid solutionId, Guid userId, CancellationToken ct = default);
    Task AddAsync(SolutionLike solutionLikeEntity, CancellationToken ct = default);
    Task DeleteAsync(Guid solutionId, Guid userId, CancellationToken ct = default);
}

/// <summary>
/// 工作单元接口 —— 确保跨聚合的操作在同一个事务中完成。
/// </summary>
public interface IUnitOfWork : IDisposable
{
    Task<int> SaveChangesAsync(CancellationToken ct = default);
}
