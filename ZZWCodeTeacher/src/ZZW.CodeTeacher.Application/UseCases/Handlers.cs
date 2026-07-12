namespace ZZW.CodeTeacher.Application.UseCases;

using AutoMapper;
using MediatR;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Application.Interfaces;
using ZZW.CodeTeacher.Application.Queries;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Exceptions;
using ZZW.CodeTeacher.Domain.Repositories;
using ZZW.CodeTeacher.Domain.Services;
using ZZW.CodeTeacher.Domain.ValueObjects;

// ═════════════════════════ 题目 Use Case ═════════════════════════

/// <summary>创建题目 Use Case</summary>
public sealed class CreateProblemHandler(IProblemRepository repo, IUnitOfWork uow, IMapper mapper)
    : IRequestHandler<CreateProblemCommand, ProblemDto>
{
    public async Task<ProblemDto> Handle(CreateProblemCommand request, CancellationToken cancellationToken)
    {
        var existing = await repo.GetByCodeAsync(request.Code, cancellationToken);
        if (existing is not null)
            throw new DomainException($"题号 {request.Code} 已存在");

        var problem = Problem.Create(request.Code, request.Title, request.Description, request.Difficulty,
            request.TimeLimitMs, request.MemoryLimitKb, request.Template, request.Tags, request.SupportedLanguages);
        await repo.AddAsync(problem, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return mapper.Map<ProblemDto>(problem);
    }
}

/// <summary>更新题目 Use Case</summary>
public sealed class UpdateProblemHandler(IProblemRepository repo, IUnitOfWork uow, IMapper mapper)
    : IRequestHandler<UpdateProblemCommand, ProblemDto>
{
    public async Task<ProblemDto> Handle(UpdateProblemCommand request, CancellationToken cancellationToken)
    {
        var problem = await repo.GetByIdAsync(request.Id, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.Id);
        problem.Update(request.Title, request.Description, request.Difficulty, request.TimeLimitMs,
            request.MemoryLimitKb, request.Template, request.Tags, request.SupportedLanguages);
        await repo.UpdateAsync(problem, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return mapper.Map<ProblemDto>(problem);
    }
}

/// <summary>添加测试用例 Use Case</summary>
public sealed class AddTestCaseHandler(IProblemRepository repo, IUnitOfWork uow)
    : IRequestHandler<AddTestCaseCommand, Unit>
{
    public async Task<Unit> Handle(AddTestCaseCommand request, CancellationToken cancellationToken)
    {
        var problem = await repo.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.ProblemId);
        var tc = problem.AddTestCase(request.Input, request.ExpectedOutput, request.IsSample);
        await repo.UpdateAsync(problem, cancellationToken);       // 更新 Problem.UpdatedAt
        await repo.AddTestCaseAsync(tc, cancellationToken);        // 显式 Add TestCase(避免 EF Core 将其标记为 Modified)
        await uow.SaveChangesAsync(cancellationToken);
        return Unit.Value;
    }
}

/// <summary>删除题目 Use Case</summary>
public sealed class DeleteProblemHandler(IProblemRepository repo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<DeleteProblemCommand, Unit>
{
    public async Task<Unit> Handle(DeleteProblemCommand request, CancellationToken cancellationToken)
    {
        AuthorizationService.EnsureCanManageProblems(user.Role);
        await repo.DeleteAsync(request.Id, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return Unit.Value;
    }
}

/// <summary>切换题目状态 Use Case</summary>
public sealed class ToggleProblemHandler(IProblemRepository repo, IUnitOfWork uow)
    : IRequestHandler<ToggleProblemCommand, Unit>
{
    public async Task<Unit> Handle(ToggleProblemCommand request, CancellationToken cancellationToken)
    {
        var problem = await repo.GetByIdAsync(request.Id, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.Id);
        problem.SetActive(request.IsActive);
        await repo.UpdateAsync(problem, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return Unit.Value;
    }
}

// ═════════════════════════ 用户 Use Case ═════════════════════════

/// <summary>注册 Use Case</summary>
public sealed class RegisterHandler(
    IUserRepository repo, IUnitOfWork uow, IPasswordHasher hasher,
    ITokenService tokens, IMapper mapper)
    : IRequestHandler<RegisterCommand, AuthResultDto>
{
    public async Task<AuthResultDto> Handle(RegisterCommand request, CancellationToken cancellationToken)
    {
        if (await repo.GetByUsernameAsync(request.Username, cancellationToken) is not null)
            throw new DomainException("用户名已被占用");
        if (await repo.GetByEmailAsync(request.Email, cancellationToken) is not null)
            throw new DomainException("邮箱已被注册");

        var hash = hasher.Hash(request.Password);
        var user = User.Create(request.Username, request.Email, hash, request.DisplayName);
        await repo.AddAsync(user, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        var (token, exp) = tokens.GenerateToken(user);
        return new AuthResultDto(token, "Bearer", exp, mapper.Map<UserDto>(user));
    }
}

/// <summary>登录 Use Case</summary>
public sealed class LoginHandler(
    IUserRepository repo, IPasswordHasher hasher, ITokenService tokens, IMapper mapper)
    : IRequestHandler<LoginCommand, AuthResultDto>
{
    public async Task<AuthResultDto> Handle(LoginCommand request, CancellationToken cancellationToken)
    {
        var user = await repo.GetByUsernameAsync(request.Username, cancellationToken)
            ?? throw new DomainException("用户名或密码错误");
        if (!user.IsActive)
            throw new DomainException("账号已被禁用");
        if (!hasher.Verify(request.Password, user.PasswordHash))
            throw new DomainException("用户名或密码错误");

        user.RecordLogin();
        await repo.UpdateAsync(user, cancellationToken);

        var (token, exp) = tokens.GenerateToken(user);
        return new AuthResultDto(token, "Bearer", exp, mapper.Map<UserDto>(user));
    }
}

// ═════════════════════════ 提交 Use Case ═════════════════════════

/// <summary>提交代码 Use Case —— 多语言教学核心:校验语言 → 编译 → 评测 → 落库</summary>
public sealed class SubmitCodeHandler(
    IProblemRepository probRepo, ISubmissionRepository subRepo,
    ICodeJudgeRunner judge, IUnitOfWork uow, IMapper mapper, ICurrentUser user)
    : IRequestHandler<SubmitCodeCommand, SubmissionDto>
{
    public async Task<SubmissionDto> Handle(SubmitCodeCommand request, CancellationToken cancellationToken)
    {
        var problem = await probRepo.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.ProblemId);
        if (!problem.IsActive)
            throw new DomainException("题目未启用");
        if (!problem.Supports(request.Language))
            throw new DomainException($"该题目不支持语言 {request.Language.DisplayName()};支持的:{string.Join(", ", problem.SupportedLanguages.Select(l => l.DisplayName()))}");
        if (!judge.IsLanguageAvailable(request.Language))
            throw new DomainException($"当前服务器未安装 {request.Language.DisplayName()} 运行时,无法评测");

        // 创建 submission 并标记 Running
        var submission = Submission.Create(request.ProblemId, user.UserId ?? Guid.Empty,
            request.Code, request.Language);
        await subRepo.AddAsync(submission, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        try
        {
            submission.MarkRunning();
            await subRepo.UpdateAsync(submission, cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);

            // 编译型语言先编译,失败直接 CompileError
            var (compileOk, compileErr) = await judge.CompileAsync(request.Language, request.Code, cancellationToken);
            if (!compileOk)
            {
                submission.MarkError(compileErr ?? "编译失败");
                submission.SetResult(
                    new JudgeReport(problem.TestCases.Count, 0, 0, 0, []),
                    SubmissionStatus.CompileError);
                await subRepo.UpdateAsync(submission, cancellationToken);
                await uow.SaveChangesAsync(cancellationToken);
                return mapper.Map<SubmissionDto>(submission);
            }

            // 执行所有测试用例
            var report = await judge.JudgeAsync(
                request.Language, request.Code, problem.TestCases,
                problem.TimeLimitMs, problem.MemoryLimitKb, problem.CheckerType, cancellationToken);

            // 推断最终状态
            var finalStatus = InferStatus(report);
            submission.SetResult(report, finalStatus);
            await subRepo.UpdateAsync(submission, cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);

            return mapper.Map<SubmissionDto>(submission);
        }
        catch (Exception ex)
        {
            submission.MarkError(ex.Message);
            await subRepo.UpdateAsync(submission, cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);
            return mapper.Map<SubmissionDto>(submission);
        }
    }

    /// <summary>根据报告里第一个失败用例的错误标记推断细分状态</summary>
    internal static SubmissionStatus InferStatus(JudgeReport report)
    {
        if (report.AllPassed) return SubmissionStatus.Accepted;
        var firstFail = report.Cases.FirstOrDefault(c => !c.Passed);
        if (firstFail.Error is null) return SubmissionStatus.WrongAnswer;
        var err = firstFail.Error;
        if (err.Contains("MLE", StringComparison.Ordinal) || err.Contains("MemoryLimit", StringComparison.Ordinal))
            return SubmissionStatus.MemoryLimitExceeded;
        if (err.Contains("TLE", StringComparison.Ordinal) || err.Contains("TimeLimit", StringComparison.Ordinal))
            return SubmissionStatus.TimeLimitExceeded;
        if (err.Contains("RuntimeError", StringComparison.Ordinal) || err.Contains("Exception", StringComparison.Ordinal))
            return SubmissionStatus.RuntimeError;
        return SubmissionStatus.WrongAnswer;
    }
}

/// <summary>重新评测 Use Case</summary>
public sealed class RejudgeHandler(
    ISubmissionRepository subRepo, IProblemRepository probRepo,
    ICodeJudgeRunner judge, IUnitOfWork uow, IMapper mapper)
    : IRequestHandler<RejudgeCommand, SubmissionDto>
{
    public async Task<SubmissionDto> Handle(RejudgeCommand request, CancellationToken cancellationToken)
    {
        var submission = await subRepo.GetByIdAsync(request.SubmissionId, cancellationToken)
            ?? throw new NotFoundException(nameof(Submission), request.SubmissionId);
        var problem = await probRepo.GetByIdAsync(submission.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), submission.ProblemId);

        submission.MarkRunning();
        await subRepo.UpdateAsync(submission, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        try
        {
            var (compileOk, compileErr) = await judge.CompileAsync(
                submission.Code.Language, submission.Code.Content, cancellationToken);
            if (!compileOk)
            {
                submission.MarkError(compileErr ?? "编译失败");
                submission.SetResult(
                    new JudgeReport(problem.TestCases.Count, 0, 0, 0, []),
                    SubmissionStatus.CompileError);
            }
            else
            {
                var report = await judge.JudgeAsync(
                    submission.Code.Language, submission.Code.Content, problem.TestCases,
                    problem.TimeLimitMs, problem.MemoryLimitKb, problem.CheckerType, cancellationToken);
                var finalStatus = SubmitCodeHandler.InferStatus(report);
                submission.SetResult(report, finalStatus);
            }
            await subRepo.UpdateAsync(submission, cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);
        }
        catch (Exception ex)
        {
            submission.MarkError(ex.Message);
            await subRepo.UpdateAsync(submission, cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);
        }

        var dto = mapper.Map<SubmissionDto>(submission);
        return dto with { ProblemCode = problem.Code, ProblemTitle = problem.Title };
    }
}

// ═════════════════════════ 用户 Use Case 补充 ═════════════════════════

/// <summary>获取当前登录用户</summary>
public sealed class GetCurrentUserHandler(IUserRepository repo, ICurrentUser user, IMapper mapper)
    : IRequestHandler<GetCurrentUserQuery, UserDto?>
{
    public async Task<UserDto?> Handle(GetCurrentUserQuery request, CancellationToken cancellationToken)
    {
        if (user.UserId is null) return null;
        var u = await repo.GetByIdAsync(user.UserId.Value, cancellationToken);
        return u is null ? null : mapper.Map<UserDto>(u);
    }
}

/// <summary>更新用户角色</summary>
public sealed class UpdateUserRoleHandler(IUserRepository repo, IUnitOfWork uow, IMapper mapper)
    : IRequestHandler<UpdateUserRoleCommand, UserDto>
{
    public async Task<UserDto> Handle(UpdateUserRoleCommand request, CancellationToken cancellationToken)
    {
        var user = await repo.GetByIdAsync(request.UserId, cancellationToken)
            ?? throw new NotFoundException(nameof(User), request.UserId);
        user.UpdateProfile(null, request.Role);
        await repo.UpdateAsync(user, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return mapper.Map<UserDto>(user);
    }
}

// ═════════════════════════ 收藏 Use Case ═════════════════════════

/// <summary>切换收藏 Use Case —— 已收藏则取消,未收藏则添加,返回当前状态</summary>
public sealed class ToggleFavoriteHandler(
    IFavoriteRepository favRepo, IProblemRepository probRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<ToggleFavoriteCommand, bool>
{
    public async Task<bool> Handle(ToggleFavoriteCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        // 校验题目存在
        _ = await probRepo.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.ProblemId);

        var existing = await favRepo.GetAsync(userId, request.ProblemId, cancellationToken);
        if (existing is not null)
        {
            await favRepo.DeleteAsync(userId, request.ProblemId, cancellationToken);
            await uow.SaveChangesAsync(cancellationToken);
            return false; // 已取消收藏
        }

        var fav = Favorite.Create(userId, request.ProblemId);
        await favRepo.AddAsync(fav, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);
        return true; // 已收藏
    }
}

// ═════════════════════════ 打卡 Use Case ═════════════════════════

/// <summary>每日打卡 Use Case —— 若今日已打卡返回当前状态不重复加;否则插入并计算连续天数</summary>
public sealed class CheckInHandler(
    ICheckInRepository checkInRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<CheckInCommand, CheckInResultDto>
{
    public async Task<CheckInResultDto> Handle(CheckInCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var today = DateOnly.FromDateTime(DateTime.UtcNow);

        var existing = await checkInRepo.GetAsync(userId, today, cancellationToken);
        if (existing is not null)
        {
            // 今日已打卡,幂等返回当前状态
            var streak = await CalculateStreakAsync(userId, today, checkInRepo, cancellationToken);
            var total = await checkInRepo.CountByUserAsync(userId, cancellationToken);
            return new CheckInResultDto(streak, true, total);
        }

        var checkIn = CheckIn.Create(userId, today);
        await checkInRepo.AddAsync(checkIn, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        var newStreak = await CalculateStreakAsync(userId, today, checkInRepo, cancellationToken);
        var newTotal = await checkInRepo.CountByUserAsync(userId, cancellationToken);
        return new CheckInResultDto(newStreak, true, newTotal);
    }

    /// <summary>连续天数算法:从今天往前数连续打卡的日期数</summary>
    internal static async Task<int> CalculateStreakAsync(Guid userId, DateOnly today,
        ICheckInRepository repo, CancellationToken cancellationToken)
    {
        var all = await repo.ListByUserAsync(userId, cancellationToken);
        var dateSet = all.Select(c => c.CheckInDate).ToHashSet();
        var streak = 0;
        var cursor = today;
        while (dateSet.Contains(cursor))
        {
            streak++;
            cursor = cursor.AddDays(-1);
        }
        return streak;
    }
}

// ═════════════════════════ 讨论 Use Case ═════════════════════════

/// <summary>创建讨论 Use Case</summary>
public sealed class CreateDiscussionHandler(
    IDiscussionRepository discRepo, IProblemRepository probRepo, IUserRepository userRepo,
    IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<CreateDiscussionCommand, DiscussionDto>
{
    public async Task<DiscussionDto> Handle(CreateDiscussionCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        _ = await probRepo.GetByIdAsync(request.ProblemId, cancellationToken)
            ?? throw new NotFoundException(nameof(Problem), request.ProblemId);

        var discussion = Discussion.Create(request.ProblemId, userId, request.Title, request.Content);
        await discRepo.AddAsync(discussion, cancellationToken);
        await uow.SaveChangesAsync(cancellationToken);

        var u = await userRepo.GetByIdAsync(userId, cancellationToken);
        return new DiscussionDto(discussion.Id, discussion.ProblemId, discussion.UserId,
            u?.Username ?? "", discussion.Title, discussion.Content, discussion.CreatedAt,
            discussion.ReplyCount);
    }
}

/// <summary>创建回复 Use Case —— 通过聚合根 AddReply 维护计数一致性</summary>
public sealed class CreateReplyHandler(
    IDiscussionRepository discRepo, IUserRepository userRepo, IUnitOfWork uow, ICurrentUser user)
    : IRequestHandler<CreateReplyCommand, DiscussionReplyDto>
{
    public async Task<DiscussionReplyDto> Handle(CreateReplyCommand request, CancellationToken cancellationToken)
    {
        var userId = user.UserId ?? throw new DomainException("未登录");
        var discussion = await discRepo.GetByIdAsync(request.DiscussionId, cancellationToken)
            ?? throw new NotFoundException(nameof(Discussion), request.DiscussionId);

        var reply = discussion.AddReply(userId, request.Content);
        await discRepo.UpdateAsync(discussion, cancellationToken);   // 更新 ReplyCount(已跟踪实体)
        await discRepo.AddReplyAsync(reply, cancellationToken);       // 显式 Add 回复(避免 EF 标记异常)
        await uow.SaveChangesAsync(cancellationToken);

        var u = await userRepo.GetByIdAsync(userId, cancellationToken);
        return new DiscussionReplyDto(reply.Id, reply.DiscussionId, reply.UserId,
            u?.Username ?? "", reply.Content, reply.CreatedAt);
    }
}
