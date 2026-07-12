namespace ZZW.CodeTeacher.Application.UseCases;

using AutoMapper;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Interfaces;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Exceptions;
using ZZW.CodeTeacher.Domain.Repositories;

// ═════════════════════════ 题解 Use Case ═════════════════════════

/// <summary>创建题解 Use Case</summary>
public sealed class CreateSolutionHandler(
    ISolutionRepository solRepo, IProblemRepository probRepo, IUserRepository userRepo,
    IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<CreateSolutionCommand, SolutionDto>
{
    public async Task<SolutionDto> Handle(CreateSolutionCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        _ = await probRepo.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.ProblemId);

        var solution = Solution.Create(request.ProblemId, userId, request.Title, request.Content, request.Code, request.Language);
        await solRepo.AddAsync(solution, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        var u = await userRepo.GetByIdAsync(userId, cancellationToken);
        return new SolutionDto(solution.Id, solution.ProblemId, solution.UserId,
            u?.Username ?? "", solution.Title, solution.Content, solution.Code, solution.Language,
            solution.LikeCount, solution.IsAccepted, solution.CreatedAt, solution.UpdatedAt);
    }
}

/// <summary>切换题解点赞 Use Case —— 已赞则取消,未赞则添加</summary>
public sealed class ToggleLikeSolutionHandler(
    ISolutionRepository solRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<ToggleLikeSolutionCommand, ToggleLikeResultDto>
{
    public async Task<ToggleLikeResultDto> Handle(ToggleLikeSolutionCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var solution = await solRepo.GetByIdAsync(request.SolutionId, cancellationToken)
            ?? throw new NotFoundException(nameof(Solution), request.SolutionId);

        var existing = await solRepo.GetLikeAsync(request.SolutionId, userId, cancellationToken);
        if (existing is not null)
        {
            await solRepo.DeleteLikeAsync(request.SolutionId, userId, cancellationToken);
            solution.DecrementLike();
            await solRepo.UpdateAsync(solution, cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);
            return new ToggleLikeResultDto(false, solution.LikeCount);
        }

        var like = SolutionLike.Create(request.SolutionId, userId);
        await solRepo.AddLikeAsync(like, cancellationToken);
        solution.IncrementLike();
        await solRepo.UpdateAsync(solution, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return new ToggleLikeResultDto(true, solution.LikeCount);
    }
}

/// <summary>采纳题解 Use Case —— 题解作者或教师/管理员可调</summary>
public sealed class AcceptSolutionHandler(
    ISolutionRepository solRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<AcceptSolutionCommand, Unit>
{
    public async Task<Unit> Handle(AcceptSolutionCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var solution = await solRepo.GetByIdAsync(request.SolutionId, cancellationToken)
            ?? throw new NotFoundException(nameof(Solution), request.SolutionId);

        // 题解作者 或 教师/管理员 可采纳
        var isAuthor = solution.UserId == userId;
        var isTeacher = user.Role is UserRole.Teacher or UserRole.Admin;
        if (!isAuthor && !isTeacher)
            throw new ForbiddenException("仅题解作者或教师可采纳题解");

        solution.Accept();
        await solRepo.UpdateAsync(solution, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return Unit.Value;
    }
}

// ═════════════════════════ 公告 Use Case ═════════════════════════

/// <summary>创建公告 Use Case(仅教师/管理员)</summary>
public sealed class CreateAnnouncementHandler(
    IAnnouncementRepository annRepo, IUserRepository userRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<CreateAnnouncementCommand, AnnouncementDto>
{
    public async Task<AnnouncementDto> Handle(CreateAnnouncementCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        if (user.Role is not (UserRole.Teacher or UserRole.Admin))
            throw new ForbiddenException("仅教师/管理员可发布公告");

        var ann = Announcement.Create(userId, request.Title, request.Content, request.Pinned);
        await annRepo.AddAsync(ann, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        var u = await userRepo.GetByIdAsync(userId, cancellationToken);
        return new AnnouncementDto(ann.Id, ann.Title, ann.Content, ann.AuthorId,
            u?.Username ?? "", ann.CreatedAt, ann.IsActive, ann.Pinned);
    }
}

/// <summary>标记公告已读 Use Case(幂等)</summary>
public sealed class MarkAnnouncementReadHandler(
    IAnnouncementRepository annRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<MarkAnnouncementReadCommand, Unit>
{
    public async Task<Unit> Handle(MarkAnnouncementReadCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        _ = await annRepo.GetByIdAsync(request.AnnouncementId, cancellationToken)
            ?? throw new NotFoundException(nameof(Announcement), request.AnnouncementId);

        var existing = await annRepo.GetReadAsync(request.AnnouncementId, userId, cancellationToken);
        if (existing is null)
        {
            await annRepo.AddReadAsync(AnnouncementRead.Create(request.AnnouncementId, userId), cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);
        }
        return Unit.Value;
    }
}

/// <summary>删除公告 Use Case(仅教师/管理员)</summary>
public sealed class DeleteAnnouncementHandler(
    IAnnouncementRepository annRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<DeleteAnnouncementCommand, Unit>
{
    public async Task<Unit> Handle(DeleteAnnouncementCommand request, CancellationToken cancellationToken)
    {
        if (user.Role is not (UserRole.Teacher or UserRole.Admin))
            throw new ForbiddenException("仅教师/管理员可删除公告");
        await annRepo.DeleteAsync(request.Id, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return Unit.Value;
    }
}

// ═════════════════════════ 题目批量导入 Use Case ═════════════════════════

/// <summary>批量导入题目 Use Case(教师)。逐条创建,失败不影响其他条目</summary>
public sealed class BulkImportProblemsHandler(
    IProblemRepository probRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<BulkImportProblemsCommand, BulkImportResultDto>
{
    public async Task<BulkImportResultDto> Handle(BulkImportProblemsCommand request, CancellationToken cancellationToken)
    {
        if (user.Role is not (UserRole.Teacher or UserRole.Admin))
            throw new ForbiddenException("仅教师/管理员可批量导入题目");

        var success = 0;
        var errors = new List<BulkImportErrorDto>();
        for (var i = 0; i < request.Items.Count; i++)
        {
            var item = request.Items[i];
            try
            {
                var existing = await probRepo.GetByCodeAsync(item.Code, cancellationToken);
                if (existing is not null)
                    throw new DomainException($"题号 {item.Code} 已存在");

                var problem = Problem.Create(item.Code, item.Title, item.Description, item.Difficulty,
                    item.TimeLimitMs, item.MemoryLimitKb, item.Template, item.Tags, item.SupportedLanguages);
                await probRepo.AddAsync(problem, cancellationToken);
                await uow.SaveChangesAsync(cancellationToken);
                success++;
            }
            catch (Exception ex)
            {
                errors.Add(new BulkImportErrorDto(i, ex.Message));
            }
        }
        return new BulkImportResultDto(success, errors.Count, errors);
    }
}

// ═════════════════════════ 班级/小组 Use Case ═════════════════════════

/// <summary>创建班级 Use Case —— 创建者自动成为 Owner</summary>
public sealed class CreateGroupHandler(
    IGroupRepository groupRepo, IUserRepository userRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<CreateGroupCommand, GroupDto>
{
    public async Task<GroupDto> Handle(CreateGroupCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var group = Group.Create(userId, request.Name, request.Description);
        await groupRepo.AddAsync(group, cancellationToken);
        // 创建者自动成为 Owner
        await groupRepo.AddMemberAsync(GroupMember.Create(group.Id, userId, GroupMemberRole.Owner), cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        var u = await userRepo.GetByIdAsync(userId, cancellationToken);
        return new GroupDto(group.Id, group.Name, group.Description, group.CreatorId,
            u?.Username ?? "", group.CreatedAt, group.InviteCode, 1);
    }
}

/// <summary>加入班级 Use Case —— 凭邀请码加入,成为 Member</summary>
public sealed class JoinGroupHandler(
    IGroupRepository groupRepo, IUserRepository userRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<JoinGroupCommand, GroupDto>
{
    public async Task<GroupDto> Handle(JoinGroupCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var group = await groupRepo.GetByInviteCodeAsync(request.InviteCode, cancellationToken)
            ?? throw new NotFoundException(nameof(Group), request.InviteCode);

        var existing = await groupRepo.GetMemberAsync(group.Id, userId, cancellationToken);
        if (existing is null)
        {
            await groupRepo.AddMemberAsync(GroupMember.Create(group.Id, userId, GroupMemberRole.Member), cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);
        }

        var members = await groupRepo.ListMembersAsync(group.Id, cancellationToken);
        var creator = await userRepo.GetByIdAsync(group.CreatorId, cancellationToken);
        return new GroupDto(group.Id, group.Name, group.Description, group.CreatorId,
            creator?.Username ?? "", group.CreatedAt, group.InviteCode, members.Count);
    }
}

/// <summary>移除班级成员 Use Case(仅 Owner 可调,且不能移除自己)</summary>
public sealed class RemoveGroupMemberHandler(
    IGroupRepository groupRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<RemoveGroupMemberCommand, Unit>
{
    public async Task<Unit> Handle(RemoveGroupMemberCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var membership = await groupRepo.GetMemberAsync(request.GroupId, userId, cancellationToken)
            ?? throw new ForbiddenException("您不是该班级成员");

        if (membership.Role != GroupMemberRole.Owner)
            throw new ForbiddenException("仅班长(Owner)可移除成员");
        if (request.UserId == userId)
            throw new DomainException("不能移除自己(班长),请先转让所有权");

        await groupRepo.DeleteMemberAsync(request.GroupId, request.UserId, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return Unit.Value;
    }
}

// ═════════════════════════ 错题复习(SM-2)Use Case ═════════════════════════

/// <summary>复习评分 Use Case —— 触发 SM-2 算法更新复习计划。若无复习项则自动创建</summary>
public sealed class ScheduleReviewHandler(
    IReviewItemRepository reviewRepo, IProblemRepository probRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<ScheduleReviewCommand, ReviewItemDto>
{
    public async Task<ReviewItemDto> Handle(ScheduleReviewCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        _ = await probRepo.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.ProblemId);

        var item = await reviewRepo.GetAsync(userId, request.ProblemId, cancellationToken);
        if (item is null)
        {
            item = ReviewItem.Create(userId, request.ProblemId);
            await reviewRepo.AddAsync(item, cancellationToken);
        }
        item.ScheduleReview(request.Quality);
        await reviewRepo.UpdateAsync(item, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        var problem = await probRepo.GetByIdAsync(request.ProblemId, cancellationToken);
        return new ReviewItemDto(item.Id, item.UserId, item.ProblemId,
            problem?.Code ?? "", problem?.Title ?? "", item.EaseFactor, item.Interval,
            item.Repetitions, item.NextReviewDate, item.LastReviewedAt, item.CreatedAt);
    }
}

// ═════════════════════════ 博客 Use Case ═════════════════════════

/// <summary>创建博客文章 Use Case</summary>
public sealed class CreateBlogPostHandler(
    IBlogPostRepository blogRepo, IUserRepository userRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<CreateBlogPostCommand, BlogPostDto>
{
    public async Task<BlogPostDto> Handle(CreateBlogPostCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var post = BlogPost.Create(userId, request.Title, request.Summary, request.Content, request.Tags, request.IsPublished);
        await blogRepo.AddAsync(post, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        var u = await userRepo.GetByIdAsync(userId, cancellationToken);
        return new BlogPostDto(post.Id, post.AuthorId, u?.Username ?? "", post.Title, post.Summary,
            post.Content, post.Tags, post.ViewCount, post.LikeCount, post.CreatedAt, post.UpdatedAt, post.IsPublished);
    }
}

/// <summary>切换博客点赞 Use Case</summary>
public sealed class ToggleBlogLikeHandler(
    IBlogPostRepository blogRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<ToggleBlogLikeCommand, ToggleLikeResultDto>
{
    public async Task<ToggleLikeResultDto> Handle(ToggleBlogLikeCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var post = await blogRepo.GetByIdAsync(request.BlogPostId, cancellationToken)
            ?? throw new NotFoundException(nameof(BlogPost), request.BlogPostId);

        var existing = await blogRepo.GetLikeAsync(request.BlogPostId, userId, cancellationToken);
        if (existing is not null)
        {
            await blogRepo.DeleteLikeAsync(request.BlogPostId, userId, cancellationToken);
            post.DecrementLike();
            await blogRepo.UpdateAsync(post, cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);
            return new ToggleLikeResultDto(false, post.LikeCount);
        }

        await blogRepo.AddLikeAsync(BlogLike.Create(request.BlogPostId, userId), cancellationToken);
        post.IncrementLike();
        await blogRepo.UpdateAsync(post, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return new ToggleLikeResultDto(true, post.LikeCount);
    }
}

// ═════════════════════════ 知识点 Use Case ═════════════════════════

/// <summary>创建知识点 Use Case</summary>
public sealed class CreateKnowledgePointHandler(
    IKnowledgePointRepository kpRepo, IUnitOfWork uow)
    : IRequestHandler<CreateKnowledgePointCommand, KnowledgePointDto>
{
    public async Task<KnowledgePointDto> Handle(CreateKnowledgePointCommand request, CancellationToken cancellationToken)
    {
        var kp = KnowledgePoint.Create(request.Name, request.Description, request.ParentId);
        await kpRepo.AddAsync(kp, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return new KnowledgePointDto(kp.Id, kp.Name, kp.Description, kp.ParentId, []);
    }
}

/// <summary>关联题目与知识点 Use Case</summary>
public sealed class LinkProblemKnowledgePointHandler(
    IKnowledgePointRepository kpRepo, IProblemRepository probRepo, IUnitOfWork uow)
    : IRequestHandler<LinkProblemKnowledgePointCommand, Unit>
{
    public async Task<Unit> Handle(LinkProblemKnowledgePointCommand request, CancellationToken cancellationToken)
    {
        _ = await probRepo.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.ProblemId);
        _ = await kpRepo.GetByIdAsync(request.KnowledgePointId, cancellationToken)
            ?? throw new NotFoundException(nameof(KnowledgePoint), request.KnowledgePointId);

        await kpRepo.AddLinkAsync(ProblemKnowledgePoint.Create(request.ProblemId, request.KnowledgePointId), cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return Unit.Value;
    }
}
