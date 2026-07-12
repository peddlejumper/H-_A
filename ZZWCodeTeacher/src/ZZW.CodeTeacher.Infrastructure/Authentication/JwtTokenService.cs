namespace ZZW.CodeTeacher.Infrastructure.Authentication;

using System.Globalization;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Configuration;
using Microsoft.IdentityModel.Tokens;
using ZZW.CodeTeacher.Application.Interfaces;
using ZZW.CodeTeacher.Domain.Entities;

/// <summary>
/// JWT 令牌服务实现。
/// </summary>
public sealed class JwtTokenService(IConfiguration config) : ITokenService
{
    public (string token, int expiresIn) GenerateToken(User user)
    {
        var key = config["Jwt:Secret"] ?? throw new InvalidOperationException("JWT 密钥未配置");
        var issuer = config["Jwt:Issuer"] ?? "ZZW.CodeTeacher";
        var audience = config["Jwt:Audience"] ?? "ZZW.CodeTeacher.Web";
        var expiresIn = int.Parse(config["Jwt:ExpiresIn"] ?? "3600", CultureInfo.InvariantCulture);

        var claims = new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, user.Id.ToString()),
            new Claim(JwtRegisteredClaimNames.UniqueName, user.Username),
            new Claim(JwtRegisteredClaimNames.Email, user.Email),
            new Claim(ClaimTypes.Role, user.Role.ToString()),
            new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString())
        };

        var keyBytes = Encoding.UTF8.GetBytes(key);
        var creds = new SigningCredentials(
            new SymmetricSecurityKey(keyBytes), SecurityAlgorithms.HmacSha256);

        var token = new JwtSecurityToken(
            issuer: issuer, audience: audience,
            claims: claims, expires: DateTime.UtcNow.AddSeconds(expiresIn),
            signingCredentials: creds);

        return (new JwtSecurityTokenHandler().WriteToken(token), expiresIn);
    }
}

/// <summary>
/// 密码哈希服务 —— 使用 PBKDF2。
/// </summary>
public sealed class PasswordHasher : IPasswordHasher
{
    private const int SaltSize = 16;
    private const int HashSize = 32;
    private const int Iterations = 100_000;

    public string Hash(string password)
    {
        var salt = RandomNumberGenerator.GetBytes(SaltSize);
        var hash = Rfc2898DeriveBytes.Pbkdf2(password, salt, Iterations, HashAlgorithmName.SHA256, HashSize);
        return $"{Convert.ToBase64String(salt)}.{Convert.ToBase64String(hash)}";
    }

    public bool Verify(string password, string hash)
    {
        if (string.IsNullOrEmpty(hash) || !hash.Contains('.')) return false;
        var parts = hash.Split('.');
        var salt = Convert.FromBase64String(parts[0]);
        var expected = Convert.FromBase64String(parts[1]);
        var actual = Rfc2898DeriveBytes.Pbkdf2(password, salt, Iterations, HashAlgorithmName.SHA256, HashSize);
        return CryptographicOperations.FixedTimeEquals(actual, expected);
    }
}
