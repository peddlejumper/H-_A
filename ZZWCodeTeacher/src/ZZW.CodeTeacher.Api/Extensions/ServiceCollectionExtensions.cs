namespace ZZW.CodeTeacher.Api.Extensions;

using System.Text;
using Asp.Versioning;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Serilog;
using System.Threading.RateLimiting;
using ZZW.CodeTeacher.Application.Interfaces;

/// <summary>
/// API 层服务注册扩展。
/// </summary>
public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddApiServices(this IServiceCollection services, IConfiguration config)
    {
        // 当前用户上下文
        services.AddHttpContextAccessor();
        services.AddScoped<ICurrentUser, CurrentUserService>();

        // API 版本控制
        services.AddApiVersioning(opt =>
        {
            opt.DefaultApiVersion = new ApiVersion(1, 0);
            opt.AssumeDefaultVersionWhenUnspecified = true;
            opt.ReportApiVersions = true;
        }).AddApiExplorer(opt =>
        {
            opt.GroupNameFormat = "'v'VVV";
            opt.SubstituteApiVersionInUrl = true;
        });

        // JWT 认证
        var key = config["Jwt:Secret"] ?? "ZZWCodeTeacher_DefaultSecretKey_Min32Chars!";
        services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
            .AddJwtBearer(opt =>
            {
                opt.TokenValidationParameters = new TokenValidationParameters
                {
                    ValidateIssuer = true,
                    ValidateAudience = true,
                    ValidateLifetime = true,
                    ValidateIssuerSigningKey = true,
                    ValidIssuer = config["Jwt:Issuer"] ?? "ZZW.CodeTeacher",
                    ValidAudience = config["Jwt:Audience"] ?? "ZZW.CodeTeacher.Web",
                    IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(key)),
                    ClockSkew = TimeSpan.Zero
                };
            });

        // CORS —— 允许前端跨域
        services.AddCors(opt => opt.AddDefaultPolicy(p => p
            .WithOrigins(config.GetSection("Cors:Origins").Get<string[]>() ?? ["http://localhost:5173"])
            .AllowAnyMethod().AllowAnyHeader().AllowCredentials()));

        // 限流 —— .NET 10 内置 RateLimiting
        services.AddRateLimiter(opt =>
        {
            opt.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(http =>
                RateLimitPartition.GetFixedWindowLimiter(
                    partitionKey: http.Connection.RemoteIpAddress?.ToString() ?? "anon",
                    factory: _ => new FixedWindowRateLimiterOptions
                    {
                        PermitLimit = 100,
                        Window = TimeSpan.FromMinutes(1)
                    }));
            opt.OnRejected = (ctx, ct) =>
            {
                ctx.HttpContext.Response.StatusCode = 429;
                return new ValueTask(ctx.HttpContext.Response.WriteAsync("请求过于频繁，请稍后再试", ct));
            };
        });

        // OpenAPI —— .NET 10 内置
        services.AddOpenApi();

        // H# 脚本执行器
        services.AddScoped<IHSharpScriptRunner, HSharpPanel.HSharpScriptRunner>();

        return services;
    }
}
