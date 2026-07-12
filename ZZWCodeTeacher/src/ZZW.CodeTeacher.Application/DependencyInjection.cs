namespace ZZW.CodeTeacher.Application.Services;

using FluentValidation;
using Microsoft.Extensions.DependencyInjection;
using ZZW.CodeTeacher.Application.Mappings;

/// <summary>
/// Application 层依赖注入扩展。
/// </summary>
public static class DependencyInjection
{
    public static IServiceCollection AddApplication(this IServiceCollection services)
    {
        var assembly = typeof(DependencyInjection).Assembly;

        // MediatR —— 注册所有 Use Case
        services.AddMediatR(cfg => cfg.RegisterServicesFromAssembly(assembly));

        // AutoMapper —— 显式注册映射配置
        services.AddAutoMapper(cfg => cfg.AddProfile<MappingProfile>());

        // FluentValidation —— 自动注册所有验证器
        services.AddValidatorsFromAssembly(assembly);

        // MediatR 管道行为（顺序：验证 → 日志 → 异常）
        services.AddTransient(typeof(MediatR.IPipelineBehavior<,>), typeof(Behaviors.ValidationBehavior<,>));
        services.AddTransient(typeof(MediatR.IPipelineBehavior<,>), typeof(Behaviors.LoggingBehavior<,>));

        return services;
    }
}
