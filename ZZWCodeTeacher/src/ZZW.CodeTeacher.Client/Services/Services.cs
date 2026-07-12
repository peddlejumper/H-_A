using System.Net.Http;
using System.Net.Http.Json;
using System.Runtime.CompilerServices;
using System.Text.Json;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>认证/用户相关 API(登录、注册、当前用户)。</summary>
public sealed class AuthService
{
    private readonly ApiClient _api;
    public AuthService(ApiClient api) => _api = api;

    public Task<AuthResultDto?> LoginAsync(string username, string password, CancellationToken ct = default)
        => _api.PostAsync<LoginDto, AuthResultDto>("/api/v1/users/login",
            new LoginDto(username, password), ct);

    public Task<AuthResultDto?> RegisterAsync(RegisterDto dto, CancellationToken ct = default)
        => _api.PostAsync<RegisterDto, AuthResultDto>("/api/v1/users/register", dto, ct);

    public Task<UserDto?> GetMeAsync(CancellationToken ct = default)
        => _api.GetAsync<UserDto>("/api/v1/users/me", ct);
}

/// <summary>题目相关 API(列表、详情、增删改、用例管理)。</summary>
public sealed class ProblemService
{
    private readonly ApiClient _api;
    public ProblemService(ApiClient api) => _api = api;

    /// <summary>分页查询题目列表(支持搜索/难度过滤)</summary>
    public Task<PagedResult<ProblemListItemDto>?> ListAsync(
        int page = 1, int pageSize = 50,
        string? search = null, DifficultyLevel? difficulty = null,
        CancellationToken ct = default)
    {
        var q = new List<string> { $"page={page}", $"pageSize={pageSize}" };
        if (!string.IsNullOrWhiteSpace(search)) q.Add($"search={Uri.EscapeDataString(search.Trim())}");
        if (difficulty is not null) q.Add($"difficulty={(int)difficulty.Value}");
        return _api.GetAsync<PagedResult<ProblemListItemDto>>($"/api/v1/problems?{string.Join('&', q)}", ct);
    }

    public Task<ProblemDto?> GetAsync(Guid id, CancellationToken ct = default)
        => _api.GetAsync<ProblemDto>($"/api/v1/problems/{id}", ct);

    // ── 教师/管理员:题目 CRUD ──
    public Task<ProblemDto?> CreateAsync(CreateProblemDto dto, CancellationToken ct = default)
        => _api.PostAsync<CreateProblemDto, ProblemDto>("/api/v1/problems", dto, ct);

    public Task<ProblemDto?> UpdateAsync(Guid id, UpdateProblemDto dto, CancellationToken ct = default)
        => _api.PutAsync<UpdateProblemDto, ProblemDto>($"/api/v1/problems/{id}", dto, ct);

    public Task DeleteAsync(Guid id, CancellationToken ct = default)
        => _api.DeleteAsync($"/api/v1/problems/{id}", ct);

    public Task ToggleAsync(Guid id, bool active, CancellationToken ct = default)
        => _api.PatchAsync($"/api/v1/problems/{id}/active?active={active.ToString().ToLowerInvariant()}", ct);

    public Task AddTestCaseAsync(Guid problemId, AddTestCaseDto dto, CancellationToken ct = default)
        => _api.PostAsync<AddTestCaseDto, object>($"/api/v1/problems/{problemId}/testcases", dto, ct);
}

/// <summary>用户管理 API(列表/角色更新)。</summary>
public sealed class UserService
{
    private readonly ApiClient _api;
    public UserService(ApiClient api) => _api = api;

    public Task<PagedResult<UserDto>?> ListAsync(
        int page = 1, int pageSize = 50,
        UserRole? role = null, string? search = null,
        CancellationToken ct = default)
    {
        var q = new List<string> { $"page={page}", $"pageSize={pageSize}" };
        if (role is not null) q.Add($"role={(int)role.Value}");
        if (!string.IsNullOrWhiteSpace(search)) q.Add($"search={Uri.EscapeDataString(search.Trim())}");
        return _api.GetAsync<PagedResult<UserDto>>($"/api/v1/users?{string.Join('&', q)}", ct);
    }

    public Task<UserDto?> UpdateRoleAsync(Guid userId, UserRole role, CancellationToken ct = default)
        => _api.PatchAsync<UserDto, UserDto>($"/api/v1/users/{userId}/role?role={(int)role}", null, ct);
}

/// <summary>提交管理 API(全部提交/重新评测,教师用)。</summary>
public sealed class SubmissionAdminService
{
    private readonly ApiClient _api;
    public SubmissionAdminService(ApiClient api) => _api = api;

    public Task<PagedResult<SubmissionDto>?> ListAllAsync(
        int page = 1, int pageSize = 50,
        SubmissionStatus? status = null, CancellationToken ct = default)
    {
        var q = new List<string> { $"page={page}", $"pageSize={pageSize}" };
        if (status is not null) q.Add($"status={(int)status.Value}");
        return _api.GetAsync<PagedResult<SubmissionDto>>($"/api/v1/submissions?{string.Join('&', q)}", ct);
    }

    public Task<SubmissionDto?> RejudgeAsync(Guid id, CancellationToken ct = default)
        => _api.PostAsync<object, SubmissionDto>($"/api/v1/submissions/{id}/rejudge", new { }, ct);
}

/// <summary>代码提交与查询。</summary>
public sealed class SubmissionService
{
    private readonly ApiClient _api;
    public SubmissionService(ApiClient api) => _api = api;

    public Task<SubmissionDto?> SubmitAsync(SubmitCodeDto dto, CancellationToken ct = default)
        => _api.PostAsync<SubmitCodeDto, SubmissionDto>("/api/v1/submissions", dto, ct);

    public Task<SubmissionDto?> GetAsync(Guid id, CancellationToken ct = default)
        => _api.GetAsync<SubmissionDto>($"/api/v1/submissions/{id}", ct);

    public Task<PagedResult<SubmissionDto>?> ListByUserAsync(Guid userId, int page = 1, int pageSize = 20, CancellationToken ct = default)
        => _api.GetAsync<PagedResult<SubmissionDto>>(
            $"/api/v1/submissions/user/{userId}?page={page}&pageSize={pageSize}", ct);

    /// <summary>查询某用户的错题本(未通过提交,按题目去重)</summary>
    public Task<PagedResult<SubmissionDto>?> ListWrongByUserAsync(Guid userId, int page = 1, int pageSize = 50, CancellationToken ct = default)
        => _api.GetAsync<PagedResult<SubmissionDto>>(
            $"/api/v1/submissions/user/{userId}/wrong?page={page}&pageSize={pageSize}", ct);

    /// <summary>查询某题的提交历史(当前用户)。后端如未提供此端点(404),返回 null,调用方应 try/catch 优雅降级。</summary>
    public async Task<PagedResult<SubmissionDto>?> ListByProblemAsync(Guid problemId, int page = 1, int pageSize = 20, CancellationToken ct = default)
    {
        try
        {
            return await _api.GetAsync<PagedResult<SubmissionDto>>(
                $"/api/v1/submissions/problem/{problemId}?page={page}&pageSize={pageSize}", ct);
        }
        catch (ApiException ex) when (ex.StatusCode == 404)
        {
            // 端点未就绪:优雅降级,返回 null(调用方按空集合处理)
            return null;
        }
    }
}

/// <summary>
/// 代码草稿本地持久化。按 (userId, problemId, language) 维度保存到本地 JSON。
/// 切题/切语言不丢代码,刷新页面也能恢复。
/// </summary>
public sealed class DraftStore
{
    private readonly string _rootDir;
    private readonly Dictionary<string, string> _cache = new();
    private readonly object _lock = new();

    public DraftStore()
    {
        _rootDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "ZZWCodeTeacher");
        Directory.CreateDirectory(_rootDir);
        Load();
    }

    private string FilePath => Path.Combine(_rootDir, "drafts.json");

    private void Load()
    {
        try
        {
            if (!File.Exists(FilePath)) return;
            var json = File.ReadAllText(FilePath);
            var dict = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, string>>(json);
            if (dict is not null)
                foreach (var kv in dict) _cache[kv.Key] = kv.Value;
        }
        catch { /* 草稿文件损坏则忽略,不影响主流程 */ }
    }

    /// <summary>读取草稿;不存在返回 null。</summary>
    public string? Get(Guid userId, Guid problemId, string language)
    {
        var key = Key(userId, problemId, language);
        lock (_lock) return _cache.TryGetValue(key, out var v) ? v : null;
    }

    /// <summary>保存草稿(写穿到磁盘)。</summary>
    public void Save(Guid userId, Guid problemId, string language, string code)
    {
        var key = Key(userId, problemId, language);
        lock (_lock)
        {
            if (string.IsNullOrWhiteSpace(code))
            {
                if (_cache.Remove(key)) Persist();
                return;
            }
            _cache[key] = code;
            Persist();
        }
    }

    private void Persist()
    {
        try
        {
            var json = System.Text.Json.JsonSerializer.Serialize(_cache);
            File.WriteAllText(FilePath, json);
        }
        catch { /* 磁盘写入失败不阻塞 UI */ }
    }

    private static string Key(Guid userId, Guid problemId, string language)
        => $"{userId:N}:{problemId:N}:{language}";
}

/// <summary>
/// AI 教练服务 —— 直连用户配置的 AI 提供商(豆包/飞书/OpenAI/自定义),走 OpenAI Chat Completions 兼容协议。
/// 不再依赖 H# 8765 服务,彻底绕开字段名错位与鉴权断链问题。
/// 提供商配置来自 <see cref="AiSettingsStore"/>(本地 ai_settings.json)。
/// </summary>
public sealed class AiService : IDisposable
{
    private readonly AiSettingsStore _store;
    private HttpClient? _http;
    private AiSettings _settings;

    private static readonly JsonSerializerOptions JsonOpts = new(JsonSerializerDefaults.Web)
    {
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    public AiService(AiSettingsStore store)
    {
        _store = store;
        _settings = store.Current;
        RebuildClient();
        _store.Changed += OnSettingsChanged;
    }

    private void OnSettingsChanged(object? sender, AiSettings s)
    {
        _settings = s;
        RebuildClient();
        SettingsChanged?.Invoke(this, s);
    }

    private void RebuildClient()
    {
        _http?.Dispose();
        _http = new HttpClient { Timeout = TimeSpan.FromSeconds(Math.Max(5, _settings.TimeoutSeconds)) };
    }

    /// <summary>当前 AI 是否可用(已启用且配置完整)</summary>
    public bool IsAvailable => _settings.Enabled && _settings.IsConfigured;

    /// <summary>当前配置(供 UI 显示状态)</summary>
    public AiSettings Settings => _settings;

    /// <summary>配置变更事件(VM 监听以刷新 IsAvailable 等状态)</summary>
    public event EventHandler<AiSettings>? SettingsChanged;

    /// <summary>思路提示</summary>
    public Task<AiReply?> HintAsync(AiRequest req, CancellationToken ct = default)
        => AskAsync(BuildHintMessages(req), ct);

    /// <summary>错误解释</summary>
    public Task<AiReply?> ExplainAsync(AiRequest req, CancellationToken ct = default)
        => AskAsync(BuildExplainMessages(req), ct);

    /// <summary>代码审查</summary>
    public Task<AiReply?> ReviewAsync(AiRequest req, CancellationToken ct = default)
        => AskAsync(BuildReviewMessages(req), ct);

    /// <summary>自由对话</summary>
    public Task<AiReply?> ChatAsync(AiChatRequest req, CancellationToken ct = default)
        => AskAsync(BuildChatMessages(req), ct);

    /// <summary>测试连接(发送一句 ping,返回成功/失败与耗时)</summary>
    public async Task<(bool Ok, string Message, long ElapsedMs)> TestConnectionAsync(AiSettings? overrideSettings = null, CancellationToken ct = default)
    {
        var s = overrideSettings ?? _settings;
        if (!s.IsConfigured)
            return (false, "未配置完整(Endpoint/ApiKey/Model 均不能为空)", 0);

        var http = overrideSettings is null ? _http : new HttpClient { Timeout = TimeSpan.FromSeconds(Math.Max(5, s.TimeoutSeconds)) };
        try
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            var payload = BuildPayload(s, new List<ChatMsg>
            {
                new("你是代码教学助手,请简短回复。", "system"),
                new("ping", "user")
            });
            using var req2 = new HttpRequestMessage(HttpMethod.Post, s.Endpoint)
            {
                Content = JsonContent.Create(payload, options: JsonOpts)
            };
            req2.Headers.Add("Authorization", $"Bearer {s.ApiKey}");
            using var resp = await http!.SendAsync(req2, ct);
            sw.Stop();
            var body = await resp.Content.ReadAsStringAsync(ct);
            if (resp.IsSuccessStatusCode)
            {
                var answer = ExtractAnswer(body);
                return (true, $"连接成功({sw.ElapsedMilliseconds}ms): {Truncate(answer, 80)}", sw.ElapsedMilliseconds);
            }
            return (false, $"HTTP {resp.StatusCode}: {Truncate(body, 200)}", sw.ElapsedMilliseconds);
        }
        catch (Exception ex)
        {
            return (false, "连接失败: " + ex.Message, 0);
        }
        finally
        {
            if (overrideSettings is not null) http?.Dispose();
        }
    }

    private async Task<AiReply?> AskAsync(List<ChatMsg> messages, CancellationToken ct)
    {
        if (!IsAvailable)
            throw new ApiException(0, "AI 未配置或未启用,请先在「AI 设置」中接入飞书智能体 / 豆包 / OpenAI。");

        var payload = BuildPayload(_settings, messages);
        using var req = new HttpRequestMessage(HttpMethod.Post, _settings.Endpoint)
        {
            Content = JsonContent.Create(payload, options: JsonOpts)
        };
        req.Headers.Add("Authorization", $"Bearer {_settings.ApiKey}");

        using var resp = await _http!.SendAsync(req, ct);
        var body = await resp.Content.ReadAsStringAsync(ct);
        if (!resp.IsSuccessStatusCode)
            throw new ApiException((int)resp.StatusCode, Truncate(body, 500));

        var answer = ExtractAnswer(body);
        return new AiReply(answer);
    }

    /// <summary>流式问答:逐 token 返回答案内容(OpenAI SSE 兼容)。
    /// 供 ViewModel 实现打字机效果。完成后返回的 IAsyncEnumerable 自然结束。</summary>
    public async IAsyncEnumerable<string> AskStreamAsync(IReadOnlyList<ChatMessage> messages, [EnumeratorCancellation] CancellationToken ct = default)
    {
        if (!IsAvailable)
            throw new ApiException(0, "AI 未配置或未启用,请先在「AI 设置」中接入飞书智能体 / 豆包 / OpenAI。");

        var internalMessages = messages.Select(m => new ChatMsg(m.Content, m.Role)).ToList();
        var payload = BuildStreamPayload(_settings, internalMessages);
        using var req = new HttpRequestMessage(HttpMethod.Post, _settings.Endpoint)
        {
            Content = JsonContent.Create(payload, options: JsonOpts)
        };
        req.Headers.Add("Authorization", $"Bearer {_settings.ApiKey}");

        // ResponseHeadersRead:拿到响应头即返回,正文随后流式读取
        using var resp = await _http!.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
        if (!resp.IsSuccessStatusCode)
        {
            var errBody = await resp.Content.ReadAsStringAsync(ct);
            throw new ApiException((int)resp.StatusCode, Truncate(errBody, 500));
        }

        using var stream = await resp.Content.ReadAsStreamAsync(ct);
        using var reader = new StreamReader(stream);
        while (true)
        {
            ct.ThrowIfCancellationRequested();
            var line = await reader.ReadLineAsync(ct);
            if (line is null) break; // 流结束(替代 EndOfStream,避免潜在阻塞)
            if (string.IsNullOrEmpty(line)) continue;
            if (!line.StartsWith("data:", StringComparison.OrdinalIgnoreCase)) continue;
            var data = line["data:".Length..].Trim();
            if (data == "[DONE]") yield break;
            var delta = ExtractDelta(data);
            if (!string.IsNullOrEmpty(delta)) yield return delta;
        }
    }

    /// <summary>暴露系统提示(供 ViewModel 初始化历史消息)</summary>
    public string GetSystemPrompt(string? extraRule = null)
    {
        var basePrompt = EffectiveSystemPrompt();
        return string.IsNullOrEmpty(extraRule) ? basePrompt : basePrompt + "\n\n" + extraRule;
    }

    /// <summary>从 SSE 单行 data 中提取 delta.content(OpenAI 格式)</summary>
    private static string ExtractDelta(string data)
    {
        try
        {
            using var doc = JsonDocument.Parse(data);
            if (doc.RootElement.TryGetProperty("choices", out var choices) && choices.GetArrayLength() > 0)
            {
                var first = choices[0];
                if (first.TryGetProperty("delta", out var delta) && delta.TryGetProperty("content", out var content))
                    return content.GetString() ?? "";
                // 兼容部分提供商把内容放在 message.content
                if (first.TryGetProperty("message", out var msg) && msg.TryGetProperty("content", out var msgContent))
                    return msgContent.GetString() ?? "";
            }
            return "";
        }
        catch
        {
            return "";
        }
    }

    // ── Prompt 构建(只给思路不写答案的铁律) ──

    private List<ChatMsg> BuildHintMessages(AiRequest r)
    {
        var sys = EffectiveSystemPrompt() + "\n\n铁律:只给思路和方向,绝不直接写出完整答案代码。用引导式提问启发学生。";
        var user = $"当前语言: {r.Language ?? "未知"}\n题目ID: {r.ProblemId ?? "(无)"}\n学生代码:\n```\n{r.Code ?? "(空)"}\n```\n错误: {r.Error ?? "(无)"}\n\n请给出这道题的解题思路提示,不要直接给答案。";
        return [new(sys, "system"), new(user, "user")];
    }

    private List<ChatMsg> BuildExplainMessages(AiRequest r)
    {
        var sys = EffectiveSystemPrompt() + "\n\n铁律:解释错误原因与定位方法,不要直接给出修正后的完整代码,可以指出哪一行哪一类问题。";
        var user = $"当前语言: {r.Language ?? "未知"}\n学生代码:\n```\n{r.Code ?? "(空)"}\n```\n报错信息:\n{r.Error ?? "(无)"}\n\n请解释这个错误的含义、产生原因,并提示如何修复,但不要直接写出完整答案。";
        return [new(sys, "system"), new(user, "user")];
    }

    private List<ChatMsg> BuildReviewMessages(AiRequest r)
    {
        var sys = EffectiveSystemPrompt() + "\n\n铁律:审查代码质量(可读性/边界/性能/风格),指出问题与改进方向,但不要直接重写整段代码。";
        var user = $"当前语言: {r.Language ?? "未知"}\n请审查以下代码并给出改进建议:\n```\n{r.Code ?? "(空)"}\n```\n\n从可读性、边界条件、性能、语言风格四个维度简短点评。";
        return [new(sys, "system"), new(user, "user")];
    }

    private List<ChatMsg> BuildChatMessages(AiChatRequest r)
    {
        var sys = EffectiveSystemPrompt() + "\n\n你是编程学习助手,回答简洁,优先启发而非代写。";
        return [new(sys, "system"), new(r.Message, "user")];
    }

    private string EffectiveSystemPrompt() =>
        string.IsNullOrWhiteSpace(_settings.SystemPrompt)
            ? "你是一位专业的编程教学 AI 教练,擅长用苏格拉底式提问引导学生自主思考。"
            : _settings.SystemPrompt;

    // ── OpenAI 兼容协议 ──

    private static object BuildPayload(AiSettings s, List<ChatMsg> messages) => new
    {
        model = s.Model,
        messages,
        temperature = s.Temperature,
        max_tokens = s.MaxTokens,
        stream = false
    };

    private static object BuildStreamPayload(AiSettings s, List<ChatMsg> messages) => new
    {
        model = s.Model,
        messages,
        temperature = s.Temperature,
        max_tokens = s.MaxTokens,
        stream = true
    };

    private static string ExtractAnswer(string body)
    {
        try
        {
            using var doc = JsonDocument.Parse(body);
            // 标准 OpenAI: choices[0].message.content
            if (doc.RootElement.TryGetProperty("choices", out var choices) && choices.GetArrayLength() > 0)
            {
                var first = choices[0];
                if (first.TryGetProperty("message", out var msg) && msg.TryGetProperty("content", out var content))
                    return content.GetString() ?? "(空响应)";
            }
            // 飞书 webhook 可能直接返回 text
            if (doc.RootElement.TryGetProperty("text", out var text))
                return text.GetString() ?? "(空响应)";
            // 兜底:返回原始截断
            return Truncate(body, 500);
        }
        catch
        {
            return Truncate(body, 500);
        }
    }

    private static string Truncate(string s, int n) =>
        string.IsNullOrEmpty(s) ? "" : (s.Length <= n ? s : s[..n] + "…");

    private sealed record ChatMsg(string content, string role);

    /// <summary>公开的聊天消息记录(供 ViewModel 构建多轮历史)</summary>
    public sealed record ChatMessage(string Content, string Role);

    public void Dispose()
    {
        _store.Changed -= OnSettingsChanged;
        _http?.Dispose();
    }
}

/// <summary>用户统计(错题本、排行榜等)。</summary>
public sealed class UserStatsService
{
    private readonly ApiClient _api;
    public UserStatsService(ApiClient api) => _api = api;

    /// <summary>仪表盘统计。days 参数控制趋势窗口(7/30/90);后端如未实现则忽略并回落到默认 7 天,客户端不报错。</summary>
    public Task<DashboardStatsDto?> GetDashboardAsync(int? days = null, CancellationToken ct = default)
        => _api.GetAsync<DashboardStatsDto>(
            days is null ? "/api/v1/dashboard/stats" : $"/api/v1/dashboard/stats?days={days}", ct);

    /// <summary>多维排行榜(scope=all/week/month,language 可选筛选)。后端如未实现(404)抛 ApiException,调用方应 try/catch 回落到 all。</summary>
    public Task<PagedResult<TopUserDto>?> GetLeaderboardAsync(string scope = "all", string? language = null, int pageSize = 20, CancellationToken ct = default)
    {
        var q = new List<string> { $"scope={Uri.EscapeDataString(scope)}", $"pageSize={pageSize}" };
        if (!string.IsNullOrWhiteSpace(language)) q.Add($"language={Uri.EscapeDataString(language)}");
        return _api.GetAsync<PagedResult<TopUserDto>>($"/api/v1/dashboard/leaderboard?{string.Join('&', q)}", ct);
    }
}

/// <summary>社区功能 API(收藏 / 每日打卡 / 讨论区)。</summary>
public sealed class CommunityService
{
    private readonly ApiClient _api;
    public CommunityService(ApiClient api) => _api = api;

    // ── 收藏 ──

    /// <summary>切换收藏(幂等 toggle),返回当前是否已收藏。</summary>
    public Task<bool> ToggleFavoriteAsync(Guid problemId, CancellationToken ct = default)
        => _api.PostAsync<object, bool>($"/api/v1/favorites/{problemId}", new { }, ct);

    /// <summary>我的收藏列表(分页)。</summary>
    public Task<PagedResult<ProblemListItemDto>?> ListFavoritesAsync(int page = 1, int pageSize = 50, CancellationToken ct = default)
        => _api.GetAsync<PagedResult<ProblemListItemDto>>($"/api/v1/favorites?page={page}&pageSize={pageSize}", ct);

    // ── 每日打卡 ──

    /// <summary>每日打卡(幂等),返回连续天数等结果。</summary>
    public Task<CheckInResultDto?> CheckInAsync(CancellationToken ct = default)
        => _api.PostAsync<object, CheckInResultDto>("/api/v1/checkins", new { }, ct);

    /// <summary>查询打卡状态(连续天数 / 今日是否已打卡 / 累计次数)。</summary>
    public Task<CheckInResultDto?> GetCheckInStatusAsync(CancellationToken ct = default)
        => _api.GetAsync<CheckInResultDto>("/api/v1/checkins/status", ct);

    // ── 讨论区 ──

    /// <summary>某题的讨论列表(分页)。</summary>
    public Task<PagedResult<DiscussionListItemDto>?> ListDiscussionsAsync(Guid problemId, int page = 1, int pageSize = 20, CancellationToken ct = default)
        => _api.GetAsync<PagedResult<DiscussionListItemDto>>($"/api/v1/problems/{problemId}/discussions?page={page}&pageSize={pageSize}", ct);

    /// <summary>在某题下发起新讨论。</summary>
    public Task<DiscussionDto?> CreateDiscussionAsync(Guid problemId, CreateDiscussionDto dto, CancellationToken ct = default)
        => _api.PostAsync<CreateDiscussionDto, DiscussionDto>($"/api/v1/problems/{problemId}/discussions", dto, ct);

    /// <summary>某讨论的回复列表(分页)。</summary>
    public Task<PagedResult<DiscussionReplyDto>?> ListRepliesAsync(Guid discussionId, int page = 1, int pageSize = 50, CancellationToken ct = default)
        => _api.GetAsync<PagedResult<DiscussionReplyDto>>($"/api/v1/discussions/{discussionId}/replies?page={page}&pageSize={pageSize}", ct);

    /// <summary>在某讨论下发表回复。</summary>
    public Task<DiscussionReplyDto?> CreateReplyAsync(Guid discussionId, CreateReplyDto dto, CancellationToken ct = default)
        => _api.PostAsync<CreateReplyDto, DiscussionReplyDto>($"/api/v1/discussions/{discussionId}/replies", dto, ct);
}

/// <summary>通用 AI 请求(对齐 H# 服务 /api/ai/* body)。
/// Language 字段:让 H# AI 后端按当前教学语言切换 prompt 模板。</summary>
public record AiRequest(
    string? ProblemId = null,
    string? Code = null,
    string? Error = null,
    string? SubmissionId = null,
    string? Language = null,
    object? History = null);

public record AiChatRequest(string Message, object? History = null);

public record AiReply(string Answer);
