namespace ZZW.CodeTeacher.Application.Queries.Handlers;

using System.Linq;
using AutoMapper;
using MediatR;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Interfaces;
using ZZW.CodeTeacher.Application.Queries;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Exceptions;
using ZZW.CodeTeacher.Domain.Repositories;

// ═════════════════════════ 题解查询 Handler ═════════════════════════

/// <summary>分页查询某题目的题解列表(支持 hot/new/accepted 排序)</summary>
public sealed class ListSolutionsHandler(
    ISolutionRepository solRepo, IUserRepository userRepo)
    : IRequestHandler<ListSolutionsQuery, PagedResult<SolutionListItemDto>>
{
    public async Task<PagedResult<SolutionListItemDto>> Handle(ListSolutionsQuery request, CancellationToken cancellationToken)
    {
        var solutions = await solRepo.ListByProblemAsync(request.ProblemId, request.Page, request.PageSize, request.Sort, cancellationToken);
        var total = await solRepo.CountByProblemAsync(request.ProblemId, cancellationToken);

        var userIds = solutions.Select(s => s.UserId).Distinct().ToList();
        var users = await Task.WhenAll(userIds.Select(id => userRepo.GetByIdAsync(id, cancellationToken)));
        var userDict = users.Where(u => u is not null).ToDictionary(u => u!.Id)!;

        var dtos = solutions.Select(s => new SolutionListItemDto(
            s.Id, s.ProblemId, s.UserId,
            userDict.TryGetValue(s.UserId, out var u) ? u!.Username : "",
            s.Title, s.LikeCount, s.IsAccepted, s.CreatedAt)).ToList();
        return new PagedResult<SolutionListItemDto>(dtos, total, request.Page, request.PageSize);
    }
}

/// <summary>获取题解详情</summary>
public sealed class GetSolutionHandler(
    ISolutionRepository solRepo, IUserRepository userRepo)
    : IRequestHandler<GetSolutionQuery, SolutionDto?>
{
    public async Task<SolutionDto?> Handle(GetSolutionQuery request, CancellationToken cancellationToken)
    {
        var s = await solRepo.GetByIdAsync(request.Id, cancellationToken);
        if (s is null) return null;
        var u = await userRepo.GetByIdAsync(s.UserId, cancellationToken);
        return new SolutionDto(s.Id, s.ProblemId, s.UserId, u?.Username ?? "",
            s.Title, s.Content, s.Code, s.Language, s.LikeCount, s.IsAccepted, s.CreatedAt, s.UpdatedAt);
    }
}

// ═════════════════════════ 公告查询 Handler ═════════════════════════

/// <summary>分页查询公告列表(学员看 active,教师看全部;列表含已读状态)</summary>
public sealed class ListAnnouncementsHandler(
    IAnnouncementRepository annRepo, IUserRepository userRepo, ICurrentUser user)
    : IRequestHandler<ListAnnouncementsQuery, PagedResult<AnnouncementListItemDto>>
{
    public async Task<PagedResult<AnnouncementListItemDto>> Handle(ListAnnouncementsQuery request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? Guid.Empty;
        var isTeacher = user.Role is UserRole.Teacher or UserRole.Admin;
        // 学员只看 active;教师看全部(除非显式 activeOnly)
        var activeOnly = isTeacher ? request.ActiveOnly : true;

        var items = await annRepo.ListAsync(activeOnly, request.Page, request.PageSize, cancellationToken);
        var total = await annRepo.CountAsync(activeOnly, cancellationToken);

        var authorIds = items.Select(a => a.AuthorId).Distinct().ToList();
        var authors = await Task.WhenAll(authorIds.Select(id => userRepo.GetByIdAsync(id, cancellationToken)));
        var authorDict = authors.Where(u => u is not null).ToDictionary(u => u!.Id)!;

        var readIds = userId == Guid.Empty
            ? new HashSet<Guid>()
            : (await annRepo.ListReadIdsAsync(userId, cancellationToken)).ToHashSet();

        var dtos = items.Select(a => new AnnouncementListItemDto(
            a.Id, a.Title, a.AuthorId,
            authorDict.TryGetValue(a.AuthorId, out var u) ? u!.Username : "",
            a.CreatedAt, a.IsActive, a.Pinned, readIds.Contains(a.Id))).ToList();
        return new PagedResult<AnnouncementListItemDto>(dtos, total, request.Page, request.PageSize);
    }
}

// ═════════════════════════ 排行榜查询 Handler ═════════════════════════

/// <summary>多维排行榜 Handler —— 按周/月/全部聚合 Submission,可选语言过滤。复用 TopUserDto</summary>
public sealed class LeaderboardHandler(
    ISubmissionRepository subRepo, IUserRepository userRepo)
    : IRequestHandler<LeaderboardQuery, IReadOnlyList<TopUserDto>>
{
    public async Task<IReadOnlyList<TopUserDto>> Handle(LeaderboardQuery request, CancellationToken cancellationToken)
    {
        var subs = await subRepo.ListAllAsync(1, int.MaxValue, null, cancellationToken);

        var cutoff = request.Scope switch
        {
            LeaderboardScope.Week => DateTime.UtcNow.AddDays(-7),
            LeaderboardScope.Month => DateTime.UtcNow.AddDays(-30),
            _ => DateTime.MinValue
        };
        var filtered = subs.Where(s => s.SubmittedAt >= cutoff);
        if (request.Language is not null)
            filtered = filtered.Where(s => s.Code.Language == request.Language.Value);

        // .NET 10 AggregateBy 按用户聚合
        var aggregated = filtered
            .AggregateBy(
                keySelector: s => s.UserId,
                seed: (Total: 0, Accepted: 0),
                func: (acc, s) => (acc.Total + 1,
                    acc.Accepted + (s.Status == SubmissionStatus.Accepted ? 1 : 0)))
            .OrderByDescending(kv => kv.Value.Accepted)
            .ThenByDescending(kv => kv.Value.Total)
            .Take(50)
            .ToList();

        if (aggregated.Count == 0) return [];

        var userIds = aggregated.Select(kv => kv.Key).ToList();
        var users = await Task.WhenAll(userIds.Select(id => userRepo.GetByIdAsync(id, cancellationToken)));
        var userDict = users.Where(u => u is not null).ToDictionary(u => u!.Id)!;

        return aggregated
            .Where(kv => userDict.ContainsKey(kv.Key))
            .Select(kv =>
            {
                var u = userDict[kv.Key];
                return new TopUserDto(u!.Id, u!.Username, u!.DisplayName,
                    kv.Value.Total, kv.Value.Accepted,
                    kv.Value.Total == 0 ? 0 : (double)kv.Value.Accepted / kv.Value.Total);
            }).ToList();
    }
}

// ═════════════════════════ 学员进度查询 Handler ═════════════════════════

/// <summary>查询单学员学习进度 —— 复用 Submission 聚合</summary>
public sealed class GetUserProgressHandler(
    ISubmissionRepository subRepo, IProblemRepository probRepo, IUserRepository userRepo, IMapper mapper)
    : IRequestHandler<GetUserProgressQuery, UserProgressDto>
{
    private static readonly HashSet<SubmissionStatus> WrongStatuses =
    [
        SubmissionStatus.WrongAnswer, SubmissionStatus.TimeLimitExceeded,
        SubmissionStatus.RuntimeError, SubmissionStatus.CompileError,
        SubmissionStatus.MemoryLimitExceeded
    ];

    public async Task<UserProgressDto> Handle(GetUserProgressQuery request, CancellationToken cancellationToken)
    {
        var u = await userRepo.GetByIdAsync(request.UserId, cancellationToken)
            ?? throw new NotFoundException(nameof(User), request.UserId);

        // 拉取该用户全部提交
        var all = await subRepo.ListByUserAsync(request.UserId, 1, int.MaxValue, cancellationToken);

        // 涉及的题目(批量加载用于按难度统计)
        var probIds = all.Select(s => s.ProblemId).Distinct().ToList();
        var problems = await Task.WhenAll(probIds.Select(id => probRepo.GetByIdAsync(id, cancellationToken)));
        var probDict = problems.Where(p => p is not null).ToDictionary(p => p!.Id)!;

        var total = all.Count;
        var accepted = all.Count(s => s.Status == SubmissionStatus.Accepted);
        var rate = total == 0 ? 0 : (double)accepted / total;

        // 按语言统计(.NET 10 AggregateBy)
        var byLanguage = all
            .AggregateBy(
                keySelector: s => s.Code.Language,
                seed: (Submitted: 0, Accepted: 0),
                func: (acc, s) => (acc.Submitted + 1,
                    acc.Accepted + (s.Status == SubmissionStatus.Accepted ? 1 : 0)))
            .OrderBy(kv => kv.Key)
            .Select(kv => new LanguageStatDto(kv.Key, kv.Value.Submitted, kv.Value.Accepted))
            .ToList();

        // 按难度统计(需关联 Problem)
        var byDifficulty = all
            .Where(s => probDict.ContainsKey(s.ProblemId))
            .AggregateBy(
                keySelector: s => probDict[s.ProblemId]!.Difficulty,
                seed: (Submitted: 0, Accepted: 0),
                func: (acc, s) => (acc.Submitted + 1,
                    acc.Accepted + (s.Status == SubmissionStatus.Accepted ? 1 : 0)))
            .OrderBy(kv => kv.Key)
            .Select(kv => new DifficultyStatDto(kv.Key, kv.Value.Submitted, kv.Value.Accepted))
            .ToList();

        // 最近 10 条未通过
        var recentWrong = all
            .Where(s => WrongStatuses.Contains(s.Status))
            .OrderByDescending(s => s.SubmittedAt)
            .Take(10)
            .ToList();
        var recentWrongDtos = await ListSubmissionsByUserHandler.EnrichBatchAsync(
            recentWrong, probRepo, userRepo, mapper, cancellationToken);

        // 已通过的题目 Id(去重)
        var solved = all
            .Where(s => s.Status == SubmissionStatus.Accepted)
            .Select(s => s.ProblemId).Distinct().ToList();

        return new UserProgressDto(request.UserId, u.Username, total, accepted, rate,
            byLanguage, byDifficulty, recentWrongDtos, solved);
    }
}

// ═════════════════════════ 题目导出查询 Handler ═════════════════════════

/// <summary>导出题目(全部或按 ids)</summary>
public sealed class ExportProblemsHandler(IProblemRepository probRepo, IMapper mapper)
    : IRequestHandler<ExportProblemsQuery, IReadOnlyList<ProblemDto>>
{
    public async Task<IReadOnlyList<ProblemDto>> Handle(ExportProblemsQuery request, CancellationToken cancellationToken)
    {
        if (request.Ids is null || request.Ids.Count == 0)
        {
            var all = await probRepo.ListAsync(1, int.MaxValue, null, null, null, cancellationToken);
            return all.Select(mapper.Map<ProblemDto>).ToList();
        }

        var problems = await Task.WhenAll(request.Ids.Select(id => probRepo.GetByIdAsync(id, cancellationToken)));
        return problems.Where(p => p is not null).Select(p => mapper.Map<ProblemDto>(p!)).ToList();
    }
}

// ═════════════════════════ AI 题目推荐查询 Handler ═════════════════════════

/// <summary>
/// 推荐题目(错题驱动,规则版不引入 ML):
/// 1.取用户错题 ProblemId 去重 2.统计错题 Tags 3.找未做过的含这些 tag 的题 4.不足补未做过的 Easy
/// </summary>
public sealed class GetRecommendedProblemsHandler(
    ISubmissionRepository subRepo, IProblemRepository probRepo, ICurrentUser user)
    : IRequestHandler<GetRecommendedProblemsQuery, IReadOnlyList<RecommendedProblemDto>>
{
    private static readonly HashSet<SubmissionStatus> WrongStatuses =
    [
        SubmissionStatus.WrongAnswer, SubmissionStatus.TimeLimitExceeded,
        SubmissionStatus.RuntimeError, SubmissionStatus.CompileError,
        SubmissionStatus.MemoryLimitExceeded
    ];

    public async Task<IReadOnlyList<RecommendedProblemDto>> Handle(GetRecommendedProblemsQuery request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var limit = request.Limit <= 0 ? 5 : Math.Min(request.Limit, 50);

        // 用户全部提交,得出做过的题 + 错题
        var subs = await subRepo.ListByUserAsync(userId, 1, int.MaxValue, cancellationToken);
        var attemptedProblemIds = subs.Select(s => s.ProblemId).ToHashSet();
        var wrongProblemIds = subs
            .Where(s => WrongStatuses.Contains(s.Status))
            .Select(s => s.ProblemId).Distinct().ToHashSet();

        // 全部题目(用于筛选未做过的)
        var allProblems = await probRepo.ListAsync(1, int.MaxValue, null, true, null, cancellationToken);
        var wrongProblems = allProblems.Where(p => wrongProblemIds.Contains(p.Id)).ToList();

        // 统计错题涉及的 tag 出错次数(.NET 10 CountBy)
        var tagWrongCounts = wrongProblems
            .SelectMany(p => p.Tags)
            .CountBy(t => t)
            .OrderByDescending(kv => kv.Value)
            .ToDictionary(kv => kv.Key, kv => kv.Value);

        var result = new List<RecommendedProblemDto>();
        var picked = new HashSet<Guid>();

        // 3. 找未做过的、含这些 tag 的题目,按"该 tag 错的次数"排序
        if (tagWrongCounts.Count > 0)
        {
            var candidates = allProblems
                .Where(p => !attemptedProblemIds.Contains(p.Id))
                .Select(p => new
                {
                    Problem = p,
                    Score = p.Tags.Sum(t => tagWrongCounts.TryGetValue(t, out var c) ? c : 0)
                })
                .Where(x => x.Score > 0)
                .OrderByDescending(x => x.Score)
                .ToList();

            foreach (var x in candidates)
            {
                if (result.Count >= limit) break;
                var topTag = x.Problem.Tags
                    .Where(t => tagWrongCounts.ContainsKey(t))
                    .OrderByDescending(t => tagWrongCounts[t])
                    .First();
                result.Add(new RecommendedProblemDto(x.Problem.Id, x.Problem.Code, x.Problem.Title,
                    x.Problem.Difficulty, $"你曾在「{topTag}」标签题目上出错,试试这道"));
                picked.Add(x.Problem.Id);
            }
        }

        // 4. 不足补未做过的 Easy 题目
        if (result.Count < limit)
        {
            var easyFill = allProblems
                .Where(p => !attemptedProblemIds.Contains(p.Id) && !picked.Contains(p.Id)
                            && p.Difficulty == DifficultyLevel.Easy)
                .OrderByDescending(p => p.CreatedAt)
                .Take(limit - result.Count);
            foreach (var p in easyFill)
            {
                result.Add(new RecommendedProblemDto(p.Id, p.Code, p.Title, p.Difficulty, "推荐入门题"));
            }
        }

        return result;
    }
}

// ═════════════════════════ 班级查询 Handler ═════════════════════════

/// <summary>列出我的班级</summary>
public sealed class ListMyGroupsHandler(
    IGroupRepository groupRepo, IUserRepository userRepo, ICurrentUser user)
    : IRequestHandler<ListMyGroupsQuery, IReadOnlyList<GroupDto>>
{
    public async Task<IReadOnlyList<GroupDto>> Handle(ListMyGroupsQuery request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var groups = await groupRepo.ListByUserAsync(userId, cancellationToken);
        if (groups.Count == 0) return [];

        var creatorIds = groups.Select(g => g.CreatorId).Distinct().ToList();
        var creators = await Task.WhenAll(creatorIds.Select(id => userRepo.GetByIdAsync(id, cancellationToken)));
        var creatorDict = creators.Where(u => u is not null).ToDictionary(u => u!.Id)!;

        var dtos = new List<GroupDto>();
        foreach (var g in groups)
        {
            var members = await groupRepo.ListMembersAsync(g.Id, cancellationToken);
            dtos.Add(new GroupDto(g.Id, g.Name, g.Description, g.CreatorId,
                creatorDict.TryGetValue(g.CreatorId, out var u) ? u!.Username : "",
                g.CreatedAt, g.InviteCode, members.Count));
        }
        return dtos;
    }
}

/// <summary>列出班级成员</summary>
public sealed class ListGroupMembersHandler(
    IGroupRepository groupRepo, IUserRepository userRepo)
    : IRequestHandler<ListGroupMembersQuery, IReadOnlyList<GroupMemberDto>>
{
    public async Task<IReadOnlyList<GroupMemberDto>> Handle(ListGroupMembersQuery request, CancellationToken cancellationToken)
    {
        var members = await groupRepo.ListMembersAsync(request.GroupId, cancellationToken);
        var userIds = members.Select(m => m.UserId).Distinct().ToList();
        var users = await Task.WhenAll(userIds.Select(id => userRepo.GetByIdAsync(id, cancellationToken)));
        var userDict = users.Where(u => u is not null).ToDictionary(u => u!.Id)!;

        return members.Select(m => new GroupMemberDto(
            m.UserId,
            userDict.TryGetValue(m.UserId, out var u) ? u!.Username : "",
            userDict.TryGetValue(m.UserId, out u) ? u!.DisplayName : "",
            m.Role.ToString(), m.JoinedAt)).ToList();
    }
}

// ═════════════════════════ 错题复习查询 Handler ═════════════════════════

/// <summary>查询今日待复习项</summary>
public sealed class GetDueReviewsHandler(
    IReviewItemRepository reviewRepo, IProblemRepository probRepo, ICurrentUser user)
    : IRequestHandler<GetDueReviewsQuery, IReadOnlyList<ReviewItemDto>>
{
    public async Task<IReadOnlyList<ReviewItemDto>> Handle(GetDueReviewsQuery request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var today = DateOnly.FromDateTime(DateTime.UtcNow);
        var items = await reviewRepo.ListDueAsync(userId, today, cancellationToken);
        if (items.Count == 0) return [];

        var probIds = items.Select(i => i.ProblemId).Distinct().ToList();
        var problems = await Task.WhenAll(probIds.Select(id => probRepo.GetByIdAsync(id, cancellationToken)));
        var probDict = problems.Where(p => p is not null).ToDictionary(p => p!.Id)!;

        return items.Select(i => new ReviewItemDto(i.Id, i.UserId, i.ProblemId,
            probDict.TryGetValue(i.ProblemId, out var p) ? p!.Code : "",
            probDict.TryGetValue(i.ProblemId, out p) ? p!.Title : "",
            i.EaseFactor, i.Interval, i.Repetitions, i.NextReviewDate, i.LastReviewedAt, i.CreatedAt)).ToList();
    }
}

// ═════════════════════════ 博客查询 Handler ═════════════════════════

/// <summary>分页查询博客列表(默认仅已发布)</summary>
public sealed class ListBlogPostsHandler(
    IBlogPostRepository blogRepo, IUserRepository userRepo)
    : IRequestHandler<ListBlogPostsQuery, PagedResult<BlogPostListItemDto>>
{
    public async Task<PagedResult<BlogPostListItemDto>> Handle(ListBlogPostsQuery request, CancellationToken cancellationToken)
    {
        var posts = await blogRepo.ListAsync(true, request.Page, request.PageSize, request.Search, cancellationToken);
        var total = await blogRepo.CountAsync(true, request.Search, cancellationToken);

        var authorIds = posts.Select(p => p.AuthorId).Distinct().ToList();
        var authors = await Task.WhenAll(authorIds.Select(id => userRepo.GetByIdAsync(id, cancellationToken)));
        var authorDict = authors.Where(u => u is not null).ToDictionary(u => u!.Id)!;

        var dtos = posts.Select(p => new BlogPostListItemDto(
            p.Id, p.AuthorId,
            authorDict.TryGetValue(p.AuthorId, out var u) ? u!.Username : "",
            p.Title, p.Summary, p.Tags, p.ViewCount, p.LikeCount, p.CreatedAt)).ToList();
        return new PagedResult<BlogPostListItemDto>(dtos, total, request.Page, request.PageSize);
    }
}

/// <summary>获取博客文章详情(同时增加浏览量)</summary>
public sealed class GetBlogPostHandler(
    IBlogPostRepository blogRepo, IUserRepository userRepo, IUnitOfWork uow)
    : IRequestHandler<GetBlogPostQuery, BlogPostDto?>
{
    public async Task<BlogPostDto?> Handle(GetBlogPostQuery request, CancellationToken cancellationToken)
    {
        var post = await blogRepo.GetByIdAsync(request.Id, cancellationToken);
        if (post is null) return null;

        post.IncrementView();
        await blogRepo.UpdateAsync(post, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        var u = await userRepo.GetByIdAsync(post.AuthorId, cancellationToken);
        return new BlogPostDto(post.Id, post.AuthorId, u?.Username ?? "", post.Title, post.Summary,
            post.Content, post.Tags, post.ViewCount, post.LikeCount, post.CreatedAt, post.UpdatedAt, post.IsPublished);
    }
}

// ═════════════════════════ 知识点查询 Handler ═════════════════════════

/// <summary>获取知识点树(内存中构建 ParentId → Children 树)</summary>
public sealed class GetKnowledgeTreeHandler(IKnowledgePointRepository kpRepo)
    : IRequestHandler<GetKnowledgeTreeQuery, IReadOnlyList<KnowledgePointDto>>
{
    public async Task<IReadOnlyList<KnowledgePointDto>> Handle(GetKnowledgeTreeQuery request, CancellationToken cancellationToken)
    {
        var all = await kpRepo.ListAllAsync(cancellationToken);
        var lookup = all.ToLookup(k => k.ParentId);

        List<KnowledgePointDto> BuildChildren(Guid? parentId)
        {
            return lookup[parentId]
                .Select(k => new KnowledgePointDto(k.Id, k.Name, k.Description, k.ParentId, BuildChildren(k.Id)))
                .ToList();
        }

        return BuildChildren(null);
    }
}

/// <summary>按知识点查询题目</summary>
public sealed class GetProblemsByKnowledgePointHandler(
    IKnowledgePointRepository kpRepo, IProblemRepository probRepo, ISubmissionRepository subRepo)
    : IRequestHandler<GetProblemsByKnowledgePointQuery, IReadOnlyList<ProblemListItemDto>>
{
    public async Task<IReadOnlyList<ProblemListItemDto>> Handle(GetProblemsByKnowledgePointQuery request, CancellationToken cancellationToken)
    {
        var links = await kpRepo.ListByKnowledgePointAsync(request.KnowledgePointId, cancellationToken);
        if (links.Count == 0) return [];

        var probIds = links.Select(l => l.ProblemId).Distinct().ToList();
        var problems = await Task.WhenAll(probIds.Select(id => probRepo.GetByIdAsync(id, cancellationToken)));
        var probList = problems.Where(p => p is not null).Cast<Problem>().ToList();

        // 提交统计(与 ListProblemsHandler 一致)
        var allSubs = await subRepo.ListAllAsync(1, int.MaxValue, null, cancellationToken);
        var statsByProblem = allSubs
            .AggregateBy(
                keySelector: s => s.ProblemId,
                seed: (Total: 0, Accepted: 0),
                func: (acc, s) => (acc.Total + 1,
                    acc.Accepted + (s.Status == SubmissionStatus.Accepted ? 1 : 0)))
            .ToDictionary(kv => kv.Key, kv => kv.Value);

        return probList.Select(p =>
        {
            statsByProblem.TryGetValue(p.Id, out var st);
            return new ProblemListItemDto(
                p.Id, p.Code, p.Title, p.Difficulty, p.SupportedLanguages, p.IsActive,
                p.TestCases.Count, st.Total, st.Accepted);
        }).ToList();
    }
}
