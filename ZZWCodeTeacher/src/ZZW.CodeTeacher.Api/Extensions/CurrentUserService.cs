namespace ZZW.CodeTeacher.Api.Extensions;

using System.Security.Claims;
using ZZW.CodeTeacher.Application.Interfaces;
using ZZW.CodeTeacher.Domain.Enums;

/// <summary>
/// 当前用户上下文实现 —— 从 JWT Claims 中提取用户信息。
/// </summary>
public sealed class CurrentUserService(IHttpContextAccessor accessor) : ICurrentUser
{
    public Guid? UserId
    {
        get
        {
            var sub = accessor.HttpContext?.User?.FindFirst(ClaimTypes.NameIdentifier)?.Value
                ?? accessor.HttpContext?.User?.FindFirst("sub")?.Value;
            return Guid.TryParse(sub, out var id) ? id : null;
        }
    }

    public string Username =>
        accessor.HttpContext?.User?.FindFirst(ClaimTypes.Name)?.Value
        ?? accessor.HttpContext?.User?.FindFirst("unique_name")?.Value
        ?? string.Empty;

    public UserRole Role =>
        Enum.TryParse<UserRole>(accessor.HttpContext?.User?.FindFirst(ClaimTypes.Role)?.Value, out var r)
            ? r : UserRole.Student;

    public bool IsAuthenticated =>
        accessor.HttpContext?.User?.Identity?.IsAuthenticated ?? false;
}
