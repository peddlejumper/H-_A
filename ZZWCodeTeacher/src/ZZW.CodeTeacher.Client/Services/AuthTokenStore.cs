using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// Auth Token 本地持久化(免重登)。
/// JSON 文件存 %AppData%/ZZWCodeTeacher/auth.json,内容含 accessToken/expiresAt/userId/username/role 等。
/// 安全性说明:本地明文存 token 是桌面 app 常见做法(参考 VSCode 的 GitHub Token、各种 CLI 凭证存储),
/// 风险等同于本机已登录用户即可读取。可选增强:Windows 用 DPAPI 加密、macOS 用 Keychain,
/// 本次按需求采用明文存储,后续如需加密只需替换 Persist/Load 两处。
/// </summary>
public sealed class AuthTokenStore
{
    private static readonly string Dir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ZZWCodeTeacher");
    private static readonly string FilePath = Path.Combine(Dir, "auth.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    /// <summary>尝试加载已保存的登录态;token 过期/文件缺失/损坏均返回 null。</summary>
    public static AuthSnapshot? TryLoad()
    {
        try
        {
            if (!File.Exists(FilePath)) return null;
            var json = File.ReadAllText(FilePath);
            var doc = JsonSerializer.Deserialize<TokenFile>(json, JsonOpts);
            if (doc is null || string.IsNullOrEmpty(doc.AccessToken)) return null;
            if (doc.ExpiresAt <= DateTime.UtcNow) return null; // 已过期
            if (!Enum.TryParse<UserRole>(doc.Role, true, out var role)) return null;
            if (doc.UserId == Guid.Empty) return null;
            var user = new UserDto(
                doc.UserId,
                doc.Username ?? "",
                doc.Email ?? "",
                string.IsNullOrWhiteSpace(doc.DisplayName) ? (doc.Username ?? "") : doc.DisplayName,
                role, true,
                doc.CreatedAt == default ? DateTime.UtcNow : doc.CreatedAt,
                doc.LastLoginAt);
            return new AuthSnapshot(doc.AccessToken, doc.ExpiresAt, user);
        }
        catch
        {
            // 文件损坏/读取失败 → 视为未登录,不阻塞启动
            return null;
        }
    }

    /// <summary>登录成功后持久化(明文,见类注释)。</summary>
    public static void Save(AuthResultDto auth)
    {
        try
        {
            Directory.CreateDirectory(Dir);
            // expiresAt 按 ExpiresIn 计算,最小 60s 兜底
            var expiresAt = DateTime.UtcNow.AddSeconds(Math.Max(auth.ExpiresIn, 60));
            var file = new TokenFile
            {
                AccessToken = auth.AccessToken,
                ExpiresAt = expiresAt,
                UserId = auth.User.Id,
                Username = auth.User.Username,
                Email = auth.User.Email,
                DisplayName = auth.User.DisplayName,
                Role = auth.User.Role.ToString(),
                CreatedAt = auth.User.CreatedAt,
                LastLoginAt = auth.User.LastLoginAt
            };
            var json = JsonSerializer.Serialize(file, JsonOpts);
            File.WriteAllText(FilePath, json);
        }
        catch
        {
            // 持久化失败不阻塞登录流程,内存态仍可用
        }
    }

    /// <summary>退出登录时清除本地凭证。</summary>
    public static void Clear()
    {
        try { if (File.Exists(FilePath)) File.Delete(FilePath); }
        catch { /* 删除失败不阻塞 */ }
    }

    /// <summary>配置文件路径(供 UI 显示)</summary>
    public static string GetFilePath() => FilePath;

    private sealed class TokenFile
    {
        [JsonPropertyName("accessToken")] public string AccessToken { get; set; } = "";
        [JsonPropertyName("expiresAt")] public DateTime ExpiresAt { get; set; }
        [JsonPropertyName("userId")] public Guid UserId { get; set; }
        [JsonPropertyName("username")] public string Username { get; set; } = "";
        [JsonPropertyName("email")] public string Email { get; set; } = "";
        [JsonPropertyName("displayName")] public string DisplayName { get; set; } = "";
        [JsonPropertyName("role")] public string Role { get; set; } = "";
        [JsonPropertyName("createdAt")] public DateTime CreatedAt { get; set; }
        [JsonPropertyName("lastLoginAt")] public DateTime? LastLoginAt { get; set; }
    }
}

/// <summary>从本地恢复的登录态快照(供 AuthState 启动时加载)。</summary>
public sealed record AuthSnapshot(string AccessToken, DateTime ExpiresAt, UserDto User);
