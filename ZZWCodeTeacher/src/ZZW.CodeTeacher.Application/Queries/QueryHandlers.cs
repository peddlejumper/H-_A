namespace ZZW.CodeTeacher.Application.Queries.Handlers;

using System.Linq; // Enumerable.Order / CountBy / AggregateBy（.NET 10 新特性）
using AutoMapper;
using MediatR;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Interfaces;
using ZZW.CodeTeacher.Application.Queries;
using ZZW.CodeTeacher.Application.UseCases;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Exceptions;
using ZZW.CodeTeacher.Domain.Repositories;

/// <summary>分页查询题目列表(含真实提交统计)</summary>
public sealed class ListProblemsHandler(
    IProblemRepository repo, ISubmissionRepository subRepo)
    : IRequestHandler<ListProblemsQuery, PagedResult<ProblemListItemDto>>
{
    public async Task<PagedResult<ProblemListItemDto>> Handle(ListProblemsQuery request, CancellationToken cancellationToken)
    {
        var items = await repo.ListAsync(request.Page, request.PageSize, request.Difficulty, request.IsActive, request.Search, cancellationToken);
        var total = await repo.CountAsync(request.Difficulty, request.IsActive, request.Search, cancellationToken);

        // 批量统计每道题的提交数/通过数(避免 N+1:一次性拉全部提交再分组)
        var allSubs = await subRepo.ListAllAsync(1, int.MaxValue, null, cancellationToken);
        var statsByProblem = allSubs
            .AggregateBy(
                keySelector: s => s.ProblemId,
                seed: (Total: 0, Accepted: 0),
                func: (acc, s) => (acc.Total + 1,
                    acc.Accepted + (s.Status == SubmissionStatus.Accepted ? 1 : 0)))
            .ToDictionary(kv => kv.Key, kv => kv.Value);

        var dtos = items.Select(p =>
        {
            statsByProblem.TryGetValue(p.Id, out var st);
            return new ProblemListItemDto(
                p.Id, p.Code, p.Title, p.Difficulty, p.SupportedLanguages, p.IsActive,
                p.TestCases.Count, st.Total, st.Accepted);
        }).ToList();
        return new PagedResult<ProblemListItemDto>(dtos, total, request.Page, request.PageSize);
    }
}

/// <summary>获取题目详情</summary>
public sealed class GetProblemByIdHandler(IProblemRepository repo, IMapper mapper)
    : IRequestHandler<GetProblemByIdQuery, ProblemDto?>
{
    public async Task<ProblemDto?> Handle(GetProblemByIdQuery request, CancellationToken cancellationToken)
    {
        var p = await repo.GetByIdAsync(request.Id, cancellationToken);
        return p is null ? null : mapper.Map<ProblemDto>(p);
    }
}

/// <summary>分页查询用户列表</summary>
public sealed class ListUsersHandler(IUserRepository repo, IMapper mapper)
    : IRequestHandler<ListUsersQuery, PagedResult<UserDto>>
{
    public async Task<PagedResult<UserDto>> Handle(ListUsersQuery request, CancellationToken cancellationToken)
    {
        var items = await repo.ListAsync(request.Page, request.PageSize, request.Role, request.IsActive, request.Search, cancellationToken);
        var total = await repo.CountAsync(request.Role, request.IsActive, request.Search, cancellationToken);
        return new PagedResult<UserDto>(items.Select(mapper.Map<UserDto>).ToList(),
            total, request.Page, request.PageSize);
    }
}

/// <summary>获取仪表盘统计 —— 使用 .NET 10 Enumerable.CountBy / AggregateBy</summary>
public sealed class GetDashboardStatsHandler(
    IProblemRepository probRepo, IUserRepository userRepo, ISubmissionRepository subRepo)
    : IRequestHandler<GetDashboardStatsQuery, DashboardStatsDto>
{
    public async Task<DashboardStatsDto> Handle(GetDashboardStatsQuery request, CancellationToken cancellationToken)
    {
        var problems = await probRepo.ListAsync(1, int.MaxValue, null, null, null, cancellationToken);
        var users = await userRepo.ListAsync(1, int.MaxValue, null, null, null, cancellationToken);
        var subs = await subRepo.ListAllAsync(1, int.MaxValue, null, cancellationToken);

        // .NET 10 新特性：CountBy 按难度统计题目分布
        var diffDist = problems
            .CountBy(p => p.Difficulty)
            .Select(kv => new DifficultyDistributionDto(kv.Key, kv.Value, problems.Count))
            .OrderBy(d => d.Difficulty)
            .ToList();

        // .NET 10 新特性：AggregateBy 按用户聚合提交统计
        var topUsers = subs
            .AggregateBy(
                keySelector: s => s.UserId,
                seed: (Total: 0, Accepted: 0),
                func: (acc, s) => (acc.Total + 1, acc.Accepted + (s.Status == SubmissionStatus.Accepted ? 1 : 0)))
            .OrderByDescending(kv => kv.Value.Accepted)
            .Take(10)
            .Join(users, kv => kv.Key, u => u.Id, (kv, u) => new TopUserDto(
                u.Id, u.Username, u.DisplayName, kv.Value.Total, kv.Value.Accepted,
                kv.Value.Total == 0 ? 0 : (double)kv.Value.Accepted / kv.Value.Total))
            .ToList();

        // 按日聚合（最近 7 天）
        var recent = subs
            .Where(s => s.SubmittedAt >= DateTime.UtcNow.AddDays(-7))
            .GroupBy(s => s.SubmittedAt.Date)
            .Select(g => new DailySubmissionDto(g.Key, g.Count(),
                g.Count(s => s.Status == SubmissionStatus.Accepted)))
            .OrderBy(d => d.Date)
            .ToList();

        var accepted = subs.Count(s => s.Status == SubmissionStatus.Accepted);
        var acceptanceRate = subs.Count == 0 ? 0 : (double)accepted / subs.Count;

        return new DashboardStatsDto(
            problems.Count, problems.Count(p => p.IsActive),
            users.Count, subs.Count, accepted, acceptanceRate,
            diffDist, recent, topUsers);
    }
}

// ═════════════════════════ 提交查询 Handler ═════════════════════════

/// <summary>获取提交详情</summary>
public sealed class GetSubmissionByIdHandler(
    ISubmissionRepository subRepo, IProblemRepository probRepo, IUserRepository userRepo, IMapper mapper)
    : IRequestHandler<GetSubmissionByIdQuery, SubmissionDto?>
{
    public async Task<SubmissionDto?> Handle(GetSubmissionByIdQuery request, CancellationToken cancellationToken)
    {
        var sub = await subRepo.GetByIdAsync(request.Id, cancellationToken);
        if (sub is null) return null;
        return await EnrichAsync(sub, probRepo, userRepo, mapper, cancellationToken);
    }

    internal static async Task<SubmissionDto> EnrichAsync(Submission sub,
        IProblemRepository probRepo, IUserRepository userRepo, IMapper mapper, CancellationToken cancellationToken)
    {
        var dto = mapper.Map<SubmissionDto>(sub);
        var problem = await probRepo.GetByIdAsync(sub.ProblemId, cancellationToken);
        var user = await userRepo.GetByIdAsync(sub.UserId, cancellationToken);
        return dto with
        {
            ProblemCode = problem?.Code ?? "",
            ProblemTitle = problem?.Title ?? "",
            Username = user?.Username ?? ""
        };
    }
}

/// <summary>按用户查询提交记录</summary>
public sealed class ListSubmissionsByUserHandler(
    ISubmissionRepository subRepo, IProblemRepository probRepo, IUserRepository userRepo, IMapper mapper)
    : IRequestHandler<ListSubmissionsByUserQuery, PagedResult<SubmissionDto>>
{
    public async Task<PagedResult<SubmissionDto>> Handle(ListSubmissionsByUserQuery request, CancellationToken cancellationToken)
    {
        var subs = await subRepo.ListByUserAsync(request.UserId, request.Page, request.PageSize, cancellationToken);
        var total = await subRepo.CountByUserAsync(request.UserId, cancellationToken);
        var dtos = await EnrichBatchAsync(subs, probRepo, userRepo, mapper, cancellationToken);
        return new PagedResult<SubmissionDto>(dtos, total, request.Page, request.PageSize);
    }

    internal static async Task<List<SubmissionDto>> EnrichBatchAsync(IReadOnlyList<Submission> subs,
        IProblemRepository probRepo, IUserRepository userRepo, IMapper mapper, CancellationToken cancellationToken)
    {
        if (subs.Count == 0) return [];
        var probIds = subs.Select(s => s.ProblemId).Distinct().ToList();
        var userIds = subs.Select(s => s.UserId).Distinct().ToList();
        var problems = await Task.WhenAll(probIds.Select(id => probRepo.GetByIdAsync(id, cancellationToken)));
        var users = await Task.WhenAll(userIds.Select(id => userRepo.GetByIdAsync(id, cancellationToken)));
        var probDict = problems.Where(p => p is not null).ToDictionary(p => p!.Id)!;
        var userDict = users.Where(u => u is not null).ToDictionary(u => u!.Id)!;
        return subs.Select(s =>
        {
            var dto = mapper.Map<SubmissionDto>(s);
            if (probDict.TryGetValue(s.ProblemId, out var p))
                dto = dto with { ProblemCode = p!.Code, ProblemTitle = p!.Title };
            if (userDict.TryGetValue(s.UserId, out var u))
                dto = dto with { Username = u!.Username };
            return dto;
        }).ToList();
    }
}

/// <summary>分页查询全部提交</summary>
public sealed class ListAllSubmissionsHandler(
    ISubmissionRepository subRepo, IProblemRepository probRepo, IUserRepository userRepo, IMapper mapper)
    : IRequestHandler<ListAllSubmissionsQuery, PagedResult<SubmissionDto>>
{
    public async Task<PagedResult<SubmissionDto>> Handle(ListAllSubmissionsQuery request, CancellationToken cancellationToken)
    {
        var subs = await subRepo.ListAllAsync(request.Page, request.PageSize, request.Status, cancellationToken);
        var total = await subRepo.CountAsync(request.Status, cancellationToken);
        var dtos = await ListSubmissionsByUserHandler.EnrichBatchAsync(subs, probRepo, userRepo, mapper, cancellationToken);
        return new PagedResult<SubmissionDto>(dtos, total, request.Page, request.PageSize);
    }
}

/// <summary>查询用户的错题本:未通过的提交,按题目去重保留最近一次失败</summary>
public sealed class ListWrongSubmissionsHandler(
    ISubmissionRepository subRepo, IProblemRepository probRepo, IUserRepository userRepo, IMapper mapper)
    : IRequestHandler<ListWrongSubmissionsQuery, PagedResult<SubmissionDto>>
{
    private static readonly HashSet<SubmissionStatus> WrongStatuses =
    [
        SubmissionStatus.WrongAnswer,
        SubmissionStatus.TimeLimitExceeded,
        SubmissionStatus.RuntimeError,
        SubmissionStatus.CompileError
    ];

    public async Task<PagedResult<SubmissionDto>> Handle(ListWrongSubmissionsQuery request, CancellationToken cancellationToken)
    {
        // 拉取该用户全部提交,内存中按题目去重(保留最近一次失败)
        var all = await subRepo.ListByUserAsync(request.UserId, 1, int.MaxValue, cancellationToken);
        var wrong = all
            .Where(s => WrongStatuses.Contains(s.Status))
            .GroupBy(s => s.ProblemId)
            .Select(g => g.OrderByDescending(s => s.SubmittedAt).First())
            .OrderByDescending(s => s.SubmittedAt)
            .ToList();

        var total = wrong.Count;
        var page = wrong.Skip((request.Page - 1) * request.PageSize).Take(request.PageSize).ToList();
        var dtos = await ListSubmissionsByUserHandler.EnrichBatchAsync(page, probRepo, userRepo, mapper, cancellationToken);
        return new PagedResult<SubmissionDto>(dtos, total, request.Page, request.PageSize);
    }
}

// ═════════════════════════ 收藏查询 Handler ═════════════════════════

/// <summary>列出我的收藏(分页,返回题目列表项,含提交统计)</summary>
public sealed class ListFavoritesHandler(
    IFavoriteRepository favRepo, IProblemRepository probRepo,
    ISubmissionRepository subRepo, ICurrentUser user)
    : IRequestHandler<ListFavoritesQuery, PagedResult<ProblemListItemDto>>
{
    public async Task<PagedResult<ProblemListItemDto>> Handle(ListFavoritesQuery request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var favorites = await favRepo.ListAsync(userId, request.Page, request.PageSize, cancellationToken);
        var total = await favRepo.CountAsync(userId, cancellationToken);

        var problemIds = favorites.Select(f => f.ProblemId).Distinct().ToList();
        var problems = await Task.WhenAll(problemIds.Select(id => probRepo.GetByIdAsync(id, cancellationToken)));
        var probDict = problems.Where(p => p is not null).ToDictionary(p => p!.Id)!;

        // 批量统计每道题的提交数/通过数(与 ListProblemsHandler 一致)
        var allSubs = await subRepo.ListAllAsync(1, int.MaxValue, null, cancellationToken);
        var statsByProblem = allSubs
            .AggregateBy(
                keySelector: s => s.ProblemId,
                seed: (Total: 0, Accepted: 0),
                func: (acc, s) => (acc.Total + 1,
                    acc.Accepted + (s.Status == SubmissionStatus.Accepted ? 1 : 0)))
            .ToDictionary(kv => kv.Key, kv => kv.Value);

        var dtos = favorites
            .Select(f =>
            {
                if (!probDict.TryGetValue(f.ProblemId, out var p) || p is null) return null;
                statsByProblem.TryGetValue(p.Id, out var st);
                return new ProblemListItemDto(
                    p.Id, p.Code, p.Title, p.Difficulty, p.SupportedLanguages, p.IsActive,
                    p.TestCases.Count, st.Total, st.Accepted);
            })
            .Where(d => d is not null)
            .Cast<ProblemListItemDto>()
            .ToList();

        return new PagedResult<ProblemListItemDto>(dtos, total, request.Page, request.PageSize);
    }
}

// ═════════════════════════ 打卡查询 Handler ═════════════════════════

/// <summary>获取当前用户打卡状态</summary>
public sealed class GetCheckInStatusHandler(
    ICheckInRepository checkInRepo, ICurrentUser user)
    : IRequestHandler<GetCheckInStatusQuery, CheckInResultDto>
{
    public async Task<CheckInResultDto> Handle(GetCheckInStatusQuery request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var today = DateOnly.FromDateTime(DateTime.UtcNow);
        var todayChecked = await checkInRepo.GetAsync(userId, today, cancellationToken) is not null;
        var streak = await CheckInHandler.CalculateStreakAsync(userId, today, checkInRepo, cancellationToken);
        var total = await checkInRepo.CountByUserAsync(userId, cancellationToken);
        return new CheckInResultDto(streak, todayChecked, total);
    }
}

// ═════════════════════════ 讨论查询 Handler ═════════════════════════

/// <summary>分页查询某题目的讨论列表</summary>
public sealed class ListDiscussionsHandler(
    IDiscussionRepository discRepo, IUserRepository userRepo)
    : IRequestHandler<ListDiscussionsQuery, PagedResult<DiscussionListItemDto>>
{
    public async Task<PagedResult<DiscussionListItemDto>> Handle(ListDiscussionsQuery request, CancellationToken cancellationToken)
    {
        var discussions = await discRepo.ListByProblemAsync(request.ProblemId, request.Page, request.PageSize, cancellationToken);
        var total = await discRepo.CountByProblemAsync(request.ProblemId, cancellationToken);

        var userIds = discussions.Select(d => d.UserId).Distinct().ToList();
        var users = await Task.WhenAll(userIds.Select(id => userRepo.GetByIdAsync(id, cancellationToken)));
        var userDict = users.Where(u => u is not null).ToDictionary(u => u!.Id)!;

        var dtos = discussions.Select(d => new DiscussionListItemDto(
            d.Id, d.ProblemId, d.Title, d.UserId,
            userDict.TryGetValue(d.UserId, out var u) ? u!.Username : "",
            d.ReplyCount, d.CreatedAt)).ToList();
        return new PagedResult<DiscussionListItemDto>(dtos, total, request.Page, request.PageSize);
    }
}

/// <summary>查询某讨论的回复列表(按时间正序)</summary>
public sealed class ListRepliesHandler(
    IDiscussionRepository discRepo, IUserRepository userRepo)
    : IRequestHandler<ListRepliesQuery, IReadOnlyList<DiscussionReplyDto>>
{
    public async Task<IReadOnlyList<DiscussionReplyDto>> Handle(ListRepliesQuery request, CancellationToken cancellationToken)
    {
        var replies = await discRepo.ListRepliesAsync(request.DiscussionId, cancellationToken);

        var userIds = replies.Select(r => r.UserId).Distinct().ToList();
        var users = await Task.WhenAll(userIds.Select(id => userRepo.GetByIdAsync(id, cancellationToken)));
        var userDict = users.Where(u => u is not null).ToDictionary(u => u!.Id)!;

        return replies.Select(r => new DiscussionReplyDto(
            r.Id, r.DiscussionId, r.UserId,
            userDict.TryGetValue(r.UserId, out var u) ? u!.Username : "",
            r.Content, r.CreatedAt)).ToList();
    }
}
