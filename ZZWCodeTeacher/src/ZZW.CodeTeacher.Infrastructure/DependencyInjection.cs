namespace ZZW.CodeTeacher.Infrastructure;

using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.EntityFrameworkCore;
using ZZW.CodeTeacher.Application.Interfaces;
using ZZW.CodeTeacher.Domain.Repositories;
using ZZW.CodeTeacher.Infrastructure.Authentication;
using ZZW.CodeTeacher.Infrastructure.Caching;
using ZZW.CodeTeacher.Infrastructure.Judging;
using ZZW.CodeTeacher.Infrastructure.Persistence;
using ZZW.CodeTeacher.Infrastructure.Repositories;

/// <summary>
/// 基础设施层依赖注入扩展。
/// </summary>
public static class DependencyInjection
{
    /// <summary>JSON 序列化选项 —— 使用 .NET 10 新特性</summary>
    public static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull, // .NET 10
        WriteIndented = true,
        IndentCharacter = ' ',  // .NET 10：自定义缩进字符
        IndentSize = 2,
        Converters = { new JsonStringEnumConverter() }
    };

    public static IServiceCollection AddInfrastructure(this IServiceCollection services, IConfiguration config)
    {
        // EF Core —— SQLite（开发） / 可切换为 PostgreSQL（生产）
        services.AddDbContext<CodeTeacherDbContext>(opt =>
            opt.UseSqlite(config.GetConnectionString("DefaultConnection")
                ?? "Data Source=codeteacher.db"));

        // 仓储与工作单元
        services.AddScoped<IProblemRepository, ProblemRepository>();
        services.AddScoped<IUserRepository, UserRepository>();
        services.AddScoped<ISubmissionRepository, SubmissionRepository>();
        services.AddScoped<IFavoriteRepository, FavoriteRepository>();
        services.AddScoped<ICheckInRepository, CheckInRepository>();
        services.AddScoped<IDiscussionRepository, DiscussionRepository>();
        services.AddScoped<ISolutionRepository, SolutionRepository>();
        services.AddScoped<ISolutionLikeRepository, SolutionLikeRepository>();
        services.AddScoped<IAnnouncementRepository, AnnouncementRepository>();
        services.AddScoped<IGroupRepository, GroupRepository>();
        services.AddScoped<IReviewItemRepository, ReviewItemRepository>();
        services.AddScoped<IBlogPostRepository, BlogPostRepository>();
        services.AddScoped<IKnowledgePointRepository, KnowledgePointRepository>();
        services.AddScoped<IUnitOfWork, UnitOfWork>();

        // 认证服务
        services.AddSingleton<IPasswordHasher, PasswordHasher>();
        services.AddSingleton<ITokenService, JwtTokenService>();

        // 缓存
        services.AddSingleton<ICacheService, MemoryCacheService>();

        // 多语言代码评测器(进程隔离 + 资源限制)—— Scoped 以便依赖 IHSharpScriptRunner
        services.AddScoped<ICodeJudgeRunner, ProcessIsolatedCodeJudgeRunner>();

        return services;
    }
}
