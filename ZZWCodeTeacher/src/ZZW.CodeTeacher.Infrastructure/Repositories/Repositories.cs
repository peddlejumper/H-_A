namespace ZZW.CodeTeacher.Infrastructure.Repositories;

using Microsoft.EntityFrameworkCore;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Repositories;
using ZZW.CodeTeacher.Infrastructure.Persistence;

/// <summary>
/// 题目仓储实现 —— 使用 EF Core。
/// 利用 .NET 10 的 System.Threading.Lock 替代传统 lock（如需并发控制）。
/// </summary>
public sealed class ProblemRepository(CodeTeacherDbContext db) : IProblemRepository
{
    public Task<Problem?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.Problems.Include(p => p.TestCases).FirstOrDefaultAsync(p => p.Id == id, ct);

    public Task<Problem?> GetByCodeAsync(string code, CancellationToken ct = default) =>
        db.Problems.Include(p => p.TestCases).FirstOrDefaultAsync(p => p.Code == code, ct);

    public async Task<IReadOnlyList<Problem>> ListAsync(
        int page, int pageSize, DifficultyLevel? difficulty = null,
        bool? isActive = null, string? search = null, CancellationToken ct = default)
    {
        var q = db.Problems.AsNoTracking().AsQueryable();
        if (difficulty is not null) q = q.Where(p => p.Difficulty == difficulty);
        if (isActive is not null) q = q.Where(p => p.IsActive == isActive);
        if (!string.IsNullOrWhiteSpace(search))
            q = q.Where(p => EF.Functions.Like(p.Title, $"%{search}%") || EF.Functions.Like(p.Code, $"%{search}%"));
        var items = await q.Include(p => p.TestCases).OrderByDescending(p => p.CreatedAt)
            .Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
        return items;
    }

    public async Task<int> CountAsync(DifficultyLevel? difficulty = null, bool? isActive = null,
        string? search = null, CancellationToken ct = default)
    {
        var q = db.Problems.AsNoTracking().AsQueryable();
        if (difficulty is not null) q = q.Where(p => p.Difficulty == difficulty);
        if (isActive is not null) q = q.Where(p => p.IsActive == isActive);
        if (!string.IsNullOrWhiteSpace(search))
            q = q.Where(p => EF.Functions.Like(p.Title, $"%{search}%") || EF.Functions.Like(p.Code, $"%{search}%"));
        return await q.CountAsync(ct);
    }

    public async Task AddAsync(Problem problem, CancellationToken ct = default)
    {
        await db.Problems.AddAsync(problem, ct);
    }

    public Task UpdateAsync(Problem problem, CancellationToken ct = default)
    {
        // 已跟踪实体(如 GetByIdAsync 加载的)无需显式 Update,ChangeTracker 自动处理;
        // 显式 Update 会导致新加的子实体(如 TestCase,已有 Guid Id)被标记为 Modified 而非 Added
        if (db.Entry(problem).State == EntityState.Detached)
            db.Problems.Update(problem);
        return Task.CompletedTask;
    }

    public async Task AddTestCaseAsync(TestCase testCase, CancellationToken ct = default)
    {
        await db.TestCases.AddAsync(testCase, ct);
    }

    public async Task DeleteAsync(Guid id, CancellationToken ct = default)
    {
        await db.Problems.Where(p => p.Id == id).ExecuteDeleteAsync(ct);
    }
}

/// <summary>用户仓储实现</summary>
public sealed class UserRepository(CodeTeacherDbContext db) : IUserRepository
{
    public Task<User?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.Users.FirstOrDefaultAsync(u => u.Id == id, ct);

    public Task<User?> GetByUsernameAsync(string username, CancellationToken ct = default) =>
        db.Users.FirstOrDefaultAsync(u => u.Username == username, ct);

    public Task<User?> GetByEmailAsync(string email, CancellationToken ct = default) =>
        db.Users.FirstOrDefaultAsync(u => string.Equals(u.Email, email, StringComparison.OrdinalIgnoreCase), ct);

    public async Task<IReadOnlyList<User>> ListAsync(
        int page, int pageSize, UserRole? role = null, bool? isActive = null,
        string? search = null, CancellationToken ct = default)
    {
        var q = db.Users.AsNoTracking().AsQueryable();
        if (role is not null) q = q.Where(u => u.Role == role);
        if (isActive is not null) q = q.Where(u => u.IsActive == isActive);
        if (!string.IsNullOrWhiteSpace(search))
            q = q.Where(u => EF.Functions.Like(u.Username, $"%{search}%") || EF.Functions.Like(u.DisplayName, $"%{search}%"));
        return await q.OrderByDescending(u => u.CreatedAt)
            .Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
    }

    public async Task<int> CountAsync(UserRole? role = null, bool? isActive = null,
        string? search = null, CancellationToken ct = default)
    {
        var q = db.Users.AsNoTracking().AsQueryable();
        if (role is not null) q = q.Where(u => u.Role == role);
        if (isActive is not null) q = q.Where(u => u.IsActive == isActive);
        if (!string.IsNullOrWhiteSpace(search))
            q = q.Where(u => EF.Functions.Like(u.Username, $"%{search}%"));
        return await q.CountAsync(ct);
    }

    public async Task AddAsync(User user, CancellationToken ct = default) =>
        await db.Users.AddAsync(user, ct);

    public Task UpdateAsync(User user, CancellationToken ct = default)
    {
        if (db.Entry(user).State == EntityState.Detached)
            db.Users.Update(user);
        return Task.CompletedTask;
    }

    public async Task DeleteAsync(Guid id, CancellationToken ct = default) =>
        await db.Users.Where(u => u.Id == id).ExecuteDeleteAsync(ct);
}

/// <summary>提交记录仓储实现</summary>
public sealed class SubmissionRepository(CodeTeacherDbContext db) : ISubmissionRepository
{
    public Task<Submission?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.Submissions.FirstOrDefaultAsync(s => s.Id == id, ct);

    public async Task<IReadOnlyList<Submission>> ListByUserAsync(Guid userId, int page, int pageSize,
        CancellationToken ct = default)
    {
        return await db.Submissions.AsNoTracking()
            .Where(s => s.UserId == userId)
            .OrderByDescending(s => s.SubmittedAt)
            .Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
    }

    public Task<int> CountByUserAsync(Guid userId, CancellationToken ct = default) =>
        db.Submissions.AsNoTracking().CountAsync(s => s.UserId == userId, ct);

    public async Task<IReadOnlyList<Submission>> ListByProblemAsync(Guid problemId, int page, int pageSize,
        CancellationToken ct = default)
    {
        return await db.Submissions.AsNoTracking()
            .Where(s => s.ProblemId == problemId)
            .OrderByDescending(s => s.SubmittedAt)
            .Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
    }

    public async Task<IReadOnlyList<Submission>> ListAllAsync(int page, int pageSize,
        SubmissionStatus? status = null, CancellationToken ct = default)
    {
        var q = db.Submissions.AsNoTracking().AsQueryable();
        if (status is not null) q = q.Where(s => s.Status == status);
        return await q.OrderByDescending(s => s.SubmittedAt)
            .Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
    }

    public async Task<int> CountAsync(SubmissionStatus? status = null, CancellationToken ct = default)
    {
        var q = db.Submissions.AsNoTracking().AsQueryable();
        if (status is not null) q = q.Where(s => s.Status == status);
        return await q.CountAsync(ct);
    }

    public async Task AddAsync(Submission submission, CancellationToken ct = default) =>
        await db.Submissions.AddAsync(submission, ct);

    public Task UpdateAsync(Submission submission, CancellationToken ct = default)
    {
        if (db.Entry(submission).State == EntityState.Detached)
            db.Submissions.Update(submission);
        return Task.CompletedTask;
    }
}

/// <summary>工作单元实现</summary>
public sealed class UnitOfWork(CodeTeacherDbContext db) : IUnitOfWork
{
    public Task<int> SaveChangesAsync(CancellationToken ct = default) =>
        db.SaveChangesAsync(ct);

    public void Dispose() => db.Dispose();
}

/// <summary>收藏仓储实现</summary>
public sealed class FavoriteRepository(CodeTeacherDbContext db) : IFavoriteRepository
{
    public Task<Favorite?> GetAsync(Guid userId, Guid problemId, CancellationToken ct = default) =>
        db.Favorites.FirstOrDefaultAsync(f => f.UserId == userId && f.ProblemId == problemId, ct);

    public Task<bool> ExistsAsync(Guid userId, Guid problemId, CancellationToken ct = default) =>
        db.Favorites.AsNoTracking().AnyAsync(f => f.UserId == userId && f.ProblemId == problemId, ct);

    public async Task AddAsync(Favorite favorite, CancellationToken ct = default) =>
        await db.Favorites.AddAsync(favorite, ct);

    public async Task DeleteAsync(Guid userId, Guid problemId, CancellationToken ct = default) =>
        await db.Favorites.Where(f => f.UserId == userId && f.ProblemId == problemId).ExecuteDeleteAsync(ct);

    public async Task<IReadOnlyList<Favorite>> ListAsync(Guid userId, int page, int pageSize,
        CancellationToken ct = default)
    {
        return await db.Favorites.AsNoTracking()
            .Where(f => f.UserId == userId)
            .OrderByDescending(f => f.CreatedAt)
            .Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
    }

    public Task<int> CountAsync(Guid userId, CancellationToken ct = default) =>
        db.Favorites.AsNoTracking().CountAsync(f => f.UserId == userId, ct);
}

/// <summary>每日打卡仓储实现</summary>
public sealed class CheckInRepository(CodeTeacherDbContext db) : ICheckInRepository
{
    public Task<CheckIn?> GetAsync(Guid userId, DateOnly checkInDate, CancellationToken ct = default) =>
        db.CheckIns.FirstOrDefaultAsync(c => c.UserId == userId && c.CheckInDate == checkInDate, ct);

    public async Task AddAsync(CheckIn checkIn, CancellationToken ct = default) =>
        await db.CheckIns.AddAsync(checkIn, ct);

    public async Task<IReadOnlyList<CheckIn>> ListByUserAsync(Guid userId, CancellationToken ct = default)
    {
        return await db.CheckIns.AsNoTracking()
            .Where(c => c.UserId == userId)
            .OrderByDescending(c => c.CheckInDate)
            .ToListAsync(ct);
    }

    public Task<int> CountByUserAsync(Guid userId, CancellationToken ct = default) =>
        db.CheckIns.AsNoTracking().CountAsync(c => c.UserId == userId, ct);
}

/// <summary>讨论仓储实现</summary>
public sealed class DiscussionRepository(CodeTeacherDbContext db) : IDiscussionRepository
{
    public Task<Discussion?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.Discussions.FirstOrDefaultAsync(d => d.Id == id, ct);

    public async Task<IReadOnlyList<Discussion>> ListByProblemAsync(Guid problemId, int page, int pageSize,
        CancellationToken ct = default)
    {
        return await db.Discussions.AsNoTracking()
            .Where(d => d.ProblemId == problemId)
            .OrderByDescending(d => d.CreatedAt)
            .Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
    }

    public Task<int> CountByProblemAsync(Guid problemId, CancellationToken ct = default) =>
        db.Discussions.AsNoTracking().CountAsync(d => d.ProblemId == problemId, ct);

    public async Task AddAsync(Discussion discussion, CancellationToken ct = default) =>
        await db.Discussions.AddAsync(discussion, ct);

    public Task UpdateAsync(Discussion discussion, CancellationToken ct = default)
    {
        if (db.Entry(discussion).State == EntityState.Detached)
            db.Discussions.Update(discussion);
        return Task.CompletedTask;
    }

    public async Task AddReplyAsync(DiscussionReply reply, CancellationToken ct = default) =>
        await db.DiscussionReplies.AddAsync(reply, ct);

    public async Task<IReadOnlyList<DiscussionReply>> ListRepliesAsync(Guid discussionId, CancellationToken ct = default)
    {
        return await db.DiscussionReplies.AsNoTracking()
            .Where(r => r.DiscussionId == discussionId)
            .OrderBy(r => r.CreatedAt)
            .ToListAsync(ct);
    }
}

/// <summary>题解仓储实现</summary>
public sealed class SolutionRepository(CodeTeacherDbContext db) : ISolutionRepository
{
    public Task<Solution?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.Solutions.FirstOrDefaultAsync(s => s.Id == id, ct);

    public async Task<IReadOnlyList<Solution>> ListByProblemAsync(Guid problemId, int page, int pageSize,
        string? sort = null, CancellationToken ct = default)
    {
        var q = db.Solutions.AsNoTracking().Where(s => s.ProblemId == problemId);
        q = sort?.ToLowerInvariant() switch
        {
            "new" => q.OrderByDescending(s => s.CreatedAt),
            "accepted" => q.OrderByDescending(s => s.IsAccepted).ThenByDescending(s => s.LikeCount),
            _ => q.OrderByDescending(s => s.LikeCount).ThenByDescending(s => s.CreatedAt) // hot
        };
        return await q.Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
    }

    public Task<int> CountByProblemAsync(Guid problemId, CancellationToken ct = default) =>
        db.Solutions.AsNoTracking().CountAsync(s => s.ProblemId == problemId, ct);

    public async Task AddAsync(Solution solution, CancellationToken ct = default) =>
        await db.Solutions.AddAsync(solution, ct);

    public Task UpdateAsync(Solution solution, CancellationToken ct = default)
    {
        if (db.Entry(solution).State == EntityState.Detached)
            db.Solutions.Update(solution);
        return Task.CompletedTask;
    }

    public Task<SolutionLike?> GetLikeAsync(Guid solutionId, Guid userId, CancellationToken ct = default) =>
        db.SolutionLikes.FirstOrDefaultAsync(l => l.SolutionId == solutionId && l.UserId == userId, ct);

    public async Task AddLikeAsync(SolutionLike solutionLike, CancellationToken ct = default) =>
        await db.SolutionLikes.AddAsync(solutionLike, ct);

    public async Task DeleteLikeAsync(Guid solutionId, Guid userId, CancellationToken ct = default) =>
        await db.SolutionLikes.Where(l => l.SolutionId == solutionId && l.UserId == userId).ExecuteDeleteAsync(ct);
}

/// <summary>题解点赞关联仓储实现</summary>
public sealed class SolutionLikeRepository(CodeTeacherDbContext db) : ISolutionLikeRepository
{
    public Task<SolutionLike?> GetAsync(Guid solutionId, Guid userId, CancellationToken ct = default) =>
        db.SolutionLikes.FirstOrDefaultAsync(l => l.SolutionId == solutionId && l.UserId == userId, ct);

    public async Task AddAsync(SolutionLike solutionLikeEntity, CancellationToken ct = default) =>
        await db.SolutionLikes.AddAsync(solutionLikeEntity, ct);

    public async Task DeleteAsync(Guid solutionId, Guid userId, CancellationToken ct = default) =>
        await db.SolutionLikes.Where(l => l.SolutionId == solutionId && l.UserId == userId).ExecuteDeleteAsync(ct);
}

/// <summary>公告仓储实现</summary>
public sealed class AnnouncementRepository(CodeTeacherDbContext db) : IAnnouncementRepository
{
    public Task<Announcement?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.Announcements.FirstOrDefaultAsync(a => a.Id == id, ct);

    public async Task<IReadOnlyList<Announcement>> ListAsync(bool? activeOnly, int page, int pageSize,
        CancellationToken ct = default)
    {
        var q = db.Announcements.AsNoTracking().AsQueryable();
        if (activeOnly is true) q = q.Where(a => a.IsActive);
        // 置顶优先,再按创建时间倒序
        return await q.OrderByDescending(a => a.Pinned).ThenByDescending(a => a.CreatedAt)
            .Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
    }

    public async Task<int> CountAsync(bool? activeOnly, CancellationToken ct = default)
    {
        var q = db.Announcements.AsNoTracking().AsQueryable();
        if (activeOnly is true) q = q.Where(a => a.IsActive);
        return await q.CountAsync(ct);
    }

    public async Task AddAsync(Announcement announcement, CancellationToken ct = default) =>
        await db.Announcements.AddAsync(announcement, ct);

    public async Task DeleteAsync(Guid id, CancellationToken ct = default) =>
        await db.Announcements.Where(a => a.Id == id).ExecuteDeleteAsync(ct);

    public Task<AnnouncementRead?> GetReadAsync(Guid announcementId, Guid userId, CancellationToken ct = default) =>
        db.AnnouncementReads.FirstOrDefaultAsync(r => r.AnnouncementId == announcementId && r.UserId == userId, ct);

    public async Task AddReadAsync(AnnouncementRead read, CancellationToken ct = default) =>
        await db.AnnouncementReads.AddAsync(read, ct);

    public async Task<IReadOnlyList<Guid>> ListReadIdsAsync(Guid userId, CancellationToken ct = default) =>
        await db.AnnouncementReads.AsNoTracking()
            .Where(r => r.UserId == userId)
            .Select(r => r.AnnouncementId).ToListAsync(ct);
}

/// <summary>班级/小组仓储实现</summary>
public sealed class GroupRepository(CodeTeacherDbContext db) : IGroupRepository
{
    public Task<Group?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.Groups.FirstOrDefaultAsync(g => g.Id == id, ct);

    public Task<Group?> GetByInviteCodeAsync(string inviteCode, CancellationToken ct = default) =>
        db.Groups.FirstOrDefaultAsync(g => g.InviteCode == inviteCode, ct);

    public async Task<IReadOnlyList<Group>> ListByUserAsync(Guid userId, CancellationToken ct = default)
    {
        // 用户所在班级 = 该用户作为成员的所有班级
        var groupIds = db.GroupMembers.AsNoTracking()
            .Where(m => m.UserId == userId).Select(m => m.GroupId);
        return await db.Groups.AsNoTracking()
            .Where(g => groupIds.Contains(g.Id))
            .OrderByDescending(g => g.CreatedAt).ToListAsync(ct);
    }

    public async Task AddAsync(Group group, CancellationToken ct = default) =>
        await db.Groups.AddAsync(group, ct);

    public async Task AddMemberAsync(GroupMember member, CancellationToken ct = default) =>
        await db.GroupMembers.AddAsync(member, ct);

    public Task<GroupMember?> GetMemberAsync(Guid groupId, Guid userId, CancellationToken ct = default) =>
        db.GroupMembers.FirstOrDefaultAsync(m => m.GroupId == groupId && m.UserId == userId, ct);

    public async Task<IReadOnlyList<GroupMember>> ListMembersAsync(Guid groupId, CancellationToken ct = default) =>
        await db.GroupMembers.AsNoTracking()
            .Where(m => m.GroupId == groupId)
            .OrderByDescending(m => m.Role).ThenBy(m => m.JoinedAt).ToListAsync(ct);

    public async Task DeleteMemberAsync(Guid groupId, Guid userId, CancellationToken ct = default) =>
        await db.GroupMembers.Where(m => m.GroupId == groupId && m.UserId == userId).ExecuteDeleteAsync(ct);
}

/// <summary>错题复习项仓储实现(SM-2)</summary>
public sealed class ReviewItemRepository(CodeTeacherDbContext db) : IReviewItemRepository
{
    public Task<ReviewItem?> GetAsync(Guid userId, Guid problemId, CancellationToken ct = default) =>
        db.ReviewItems.FirstOrDefaultAsync(r => r.UserId == userId && r.ProblemId == problemId, ct);

    public Task<ReviewItem?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.ReviewItems.FirstOrDefaultAsync(r => r.Id == id, ct);

    public async Task<IReadOnlyList<ReviewItem>> ListDueAsync(Guid userId, DateOnly today, CancellationToken ct = default) =>
        await db.ReviewItems.AsNoTracking()
            .Where(r => r.UserId == userId && r.NextReviewDate <= today)
            .OrderBy(r => r.NextReviewDate).ToListAsync(ct);

    public async Task<IReadOnlyList<ReviewItem>> ListByUserAsync(Guid userId, CancellationToken ct = default) =>
        await db.ReviewItems.AsNoTracking()
            .Where(r => r.UserId == userId)
            .OrderBy(r => r.NextReviewDate).ToListAsync(ct);

    public async Task AddAsync(ReviewItem item, CancellationToken ct = default) =>
        await db.ReviewItems.AddAsync(item, ct);

    public Task UpdateAsync(ReviewItem item, CancellationToken ct = default)
    {
        if (db.Entry(item).State == EntityState.Detached)
            db.ReviewItems.Update(item);
        return Task.CompletedTask;
    }
}

/// <summary>博客文章仓储实现</summary>
public sealed class BlogPostRepository(CodeTeacherDbContext db) : IBlogPostRepository
{
    public Task<BlogPost?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.BlogPosts.FirstOrDefaultAsync(b => b.Id == id, ct);

    public async Task<IReadOnlyList<BlogPost>> ListAsync(bool publishedOnly, int page, int pageSize,
        string? search = null, CancellationToken ct = default)
    {
        var q = db.BlogPosts.AsNoTracking().AsQueryable();
        if (publishedOnly) q = q.Where(b => b.IsPublished);
        if (!string.IsNullOrWhiteSpace(search))
            q = q.Where(b => EF.Functions.Like(b.Title, $"%{search}%") || EF.Functions.Like(b.Summary, $"%{search}%"));
        return await q.OrderByDescending(b => b.CreatedAt)
            .Skip((page - 1) * pageSize).Take(pageSize).ToListAsync(ct);
    }

    public async Task<int> CountAsync(bool publishedOnly, string? search = null, CancellationToken ct = default)
    {
        var q = db.BlogPosts.AsNoTracking().AsQueryable();
        if (publishedOnly) q = q.Where(b => b.IsPublished);
        if (!string.IsNullOrWhiteSpace(search))
            q = q.Where(b => EF.Functions.Like(b.Title, $"%{search}%") || EF.Functions.Like(b.Summary, $"%{search}%"));
        return await q.CountAsync(ct);
    }

    public async Task<IReadOnlyList<BlogPost>> ListByAuthorAsync(Guid authorId, CancellationToken ct = default) =>
        await db.BlogPosts.AsNoTracking()
            .Where(b => b.AuthorId == authorId)
            .OrderByDescending(b => b.CreatedAt).ToListAsync(ct);

    public async Task AddAsync(BlogPost post, CancellationToken ct = default) =>
        await db.BlogPosts.AddAsync(post, ct);

    public Task UpdateAsync(BlogPost post, CancellationToken ct = default)
    {
        if (db.Entry(post).State == EntityState.Detached)
            db.BlogPosts.Update(post);
        return Task.CompletedTask;
    }

    public Task<BlogLike?> GetLikeAsync(Guid blogPostId, Guid userId, CancellationToken ct = default) =>
        db.BlogLikes.FirstOrDefaultAsync(l => l.BlogPostId == blogPostId && l.UserId == userId, ct);

    public async Task AddLikeAsync(BlogLike blogLike, CancellationToken ct = default) =>
        await db.BlogLikes.AddAsync(blogLike, ct);

    public async Task DeleteLikeAsync(Guid blogPostId, Guid userId, CancellationToken ct = default) =>
        await db.BlogLikes.Where(l => l.BlogPostId == blogPostId && l.UserId == userId).ExecuteDeleteAsync(ct);
}

/// <summary>知识点仓储实现</summary>
public sealed class KnowledgePointRepository(CodeTeacherDbContext db) : IKnowledgePointRepository
{
    public Task<KnowledgePoint?> GetByIdAsync(Guid id, CancellationToken ct = default) =>
        db.KnowledgePoints.FirstOrDefaultAsync(k => k.Id == id, ct);

    public async Task<IReadOnlyList<KnowledgePoint>> ListAllAsync(CancellationToken ct = default) =>
        await db.KnowledgePoints.AsNoTracking().OrderBy(k => k.Name).ToListAsync(ct);

    public async Task AddAsync(KnowledgePoint kp, CancellationToken ct = default) =>
        await db.KnowledgePoints.AddAsync(kp, ct);

    public async Task<IReadOnlyList<ProblemKnowledgePoint>> ListByKnowledgePointAsync(Guid kpId, CancellationToken ct = default) =>
        await db.ProblemKnowledgePoints.AsNoTracking().Where(p => p.KnowledgePointId == kpId).ToListAsync(ct);

    public async Task<IReadOnlyList<ProblemKnowledgePoint>> ListByProblemAsync(Guid problemId, CancellationToken ct = default) =>
        await db.ProblemKnowledgePoints.AsNoTracking().Where(p => p.ProblemId == problemId).ToListAsync(ct);

    public async Task AddLinkAsync(ProblemKnowledgePoint link, CancellationToken ct = default) =>
        await db.ProblemKnowledgePoints.AddAsync(link, ct);
}
