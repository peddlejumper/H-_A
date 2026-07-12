using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// API 调用基础封装。统一处理鉴权头、错误响应与 JSON 选项。
/// </summary>
public sealed class ApiClient
{
    public const string HttpClientName = "ZZWApi";

    private readonly IHttpClientFactory _factory;
    private readonly AuthState _auth;
    private readonly JsonSerializerOptions _json;

    public ApiClient(IHttpClientFactory factory, AuthState auth)
    {
        _factory = factory;
        _auth = auth;
        _json = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            Converters = { new JsonStringEnumConverter() },
        };
    }

    /// <summary>当前 API 基地址(从首个 HttpClient 推导,用于显示)。</summary>
    public Uri BaseAddress => _factory.CreateClient(HttpClientName).BaseAddress
        ?? new Uri("https://localhost:5001");

    private HttpClient NewClient() => _factory.CreateClient(HttpClientName);

    private void AttachAuth(HttpClient http)
    {
        var token = _auth.AccessToken;
        if (!string.IsNullOrEmpty(token))
        {
            http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        }
    }

    public async Task<TResponse?> GetAsync<TResponse>(string path, CancellationToken ct = default)
    {
        var http = NewClient();
        AttachAuth(http);
        using var resp = await http.GetAsync(path, ct);
        return await ReadOrThrowAsync<TResponse>(resp, ct);
    }

    public async Task<TResponse?> PostAsync<TRequest, TResponse>(string path, TRequest body, CancellationToken ct = default)
    {
        var http = NewClient();
        AttachAuth(http);
        using var resp = await http.PostAsJsonAsync(path, body, _json, ct);
        return await ReadOrThrowAsync<TResponse>(resp, ct);
    }

    public async Task<TResponse?> PutAsync<TRequest, TResponse>(string path, TRequest body, CancellationToken ct = default)
    {
        var http = NewClient();
        AttachAuth(http);
        using var resp = await http.PutAsJsonAsync(path, body, _json, ct);
        return await ReadOrThrowAsync<TResponse>(resp, ct);
    }

    public async Task DeleteAsync(string path, CancellationToken ct = default)
    {
        var http = NewClient();
        AttachAuth(http);
        using var resp = await http.DeleteAsync(path, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var errBody = await resp.Content.ReadAsStringAsync(ct);
            throw new ApiException((int)resp.StatusCode, errBody);
        }
    }

    public async Task PatchAsync(string path, CancellationToken ct = default)
    {
        var http = NewClient();
        AttachAuth(http);
        using var req = new HttpRequestMessage(HttpMethod.Patch, path);
        using var resp = await http.SendAsync(req, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var errBody = await resp.Content.ReadAsStringAsync(ct);
            throw new ApiException((int)resp.StatusCode, errBody);
        }
    }

    public async Task<TResponse?> PatchAsync<TRequest, TResponse>(string path, TRequest? body, CancellationToken ct = default)
    {
        var http = NewClient();
        AttachAuth(http);
        using var req = new HttpRequestMessage(HttpMethod.Patch, path);
        if (body is not null)
            req.Content = JsonContent.Create(body, options: _json);
        using var resp = await http.SendAsync(req, ct);
        return await ReadOrThrowAsync<TResponse>(resp, ct);
    }

    public async Task<HttpResponseMessage> SendRawAsync(HttpMethod method, string path, CancellationToken ct = default)
    {
        var http = NewClient();
        AttachAuth(http);
        var req = new HttpRequestMessage(method, path);
        return await http.SendAsync(req, ct);
    }

    /// <summary>发送请求并返回流(用于 SSE 流式响应,如 AI 打字机效果)。</summary>
    public async Task<Stream> SendStreamAsync(HttpMethod method, string path, object? body, CancellationToken ct = default)
    {
        var http = NewClient();
        AttachAuth(http);
        using var req = new HttpRequestMessage(method, path);
        if (body is not null)
            req.Content = JsonContent.Create(body, options: _json);
        var resp = await http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var errBody = await resp.Content.ReadAsStringAsync(ct);
            throw new ApiException((int)resp.StatusCode, errBody);
        }
        return await resp.Content.ReadAsStreamAsync(ct);
    }

    public async Task<TResponse?> ReadOrThrowAsync<TResponse>(HttpResponseMessage resp, CancellationToken ct)
    {
        if (!resp.IsSuccessStatusCode)
        {
            var errBody = await resp.Content.ReadAsStringAsync(ct);
            throw new ApiException((int)resp.StatusCode, errBody);
        }
        if (resp.Content.Headers.ContentLength is 0)
        {
            return default;
        }
        return await resp.Content.ReadFromJsonAsync<TResponse>(_json, ct);
    }
}

public sealed class ApiException : Exception
{
    public int StatusCode { get; }
    public string Body { get; }

    public ApiException(int statusCode, string body)
        : base($"API 调用失败 ({(int)statusCode}): {Truncate(body, 200)}")
    {
        StatusCode = statusCode;
        Body = body;
    }

    private static string Truncate(string s, int max) => s.Length <= max ? s : s[..max] + "…";
}
