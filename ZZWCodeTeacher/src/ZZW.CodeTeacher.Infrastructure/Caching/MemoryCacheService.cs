namespace ZZW.CodeTeacher.Infrastructure.Caching;

using Microsoft.Extensions.Caching.Memory;
using ZZW.CodeTeacher.Application.Interfaces;

/// <summary>
/// 内存缓存服务实现 —— 使用 .NET 10 优化。
/// 生产环境可替换为 Redis 分布式缓存。
/// </summary>
public sealed class MemoryCacheService : ICacheService, IDisposable
{
    private readonly MemoryCache _cache = new(new MemoryCacheOptions());

    public Task<T?> GetAsync<T>(string key, CancellationToken ct = default)
    {
        var value = _cache.Get(key);
        return Task.FromResult(value is T t ? t : default);
    }

    public Task SetAsync<T>(string key, T value, TimeSpan? expiry = null, CancellationToken ct = default)
    {
        var options = new MemoryCacheEntryOptions();
        if (expiry.HasValue)
            options.AbsoluteExpirationRelativeToNow = expiry.Value;
        _cache.Set(key, value, options);
        return Task.CompletedTask;
    }

    public Task RemoveAsync(string key, CancellationToken ct = default)
    {
        _cache.Remove(key);
        return Task.CompletedTask;
    }

    public void Dispose() => _cache.Dispose();
}
