using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>最近浏览的题目记录项。</summary>
public sealed record RecentProblemItem(Guid ProblemId, string Title, string Code, DateTime VisitedAt);

/// <summary>
/// 最近浏览历史(题目)本地存储。%AppData%/ZZWCodeTeacher/recent.json,
/// 存 List{RecentProblemItem},最多 20 条,去重(最新置顶)。
/// </summary>
public sealed class RecentProblemsStore
{
    private static readonly string Dir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ZZWCodeTeacher");
    private static readonly string FilePath = Path.Combine(Dir, "recent.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    private const int MaxItems = 20;

    private readonly object _lock = new();
    private List<RecentProblemItem> _cache = new();

    public RecentProblemsStore() => Load();

    private void Load()
    {
        try
        {
            if (!File.Exists(FilePath)) return;
            var json = File.ReadAllText(FilePath);
            var list = JsonSerializer.Deserialize<List<RecentProblemItem>>(json, JsonOpts);
            if (list is not null) _cache = list;
        }
        catch
        {
            _cache = new List<RecentProblemItem>();
        }
    }

    private void Persist()
    {
        try
        {
            Directory.CreateDirectory(Dir);
            var json = JsonSerializer.Serialize(_cache, JsonOpts);
            File.WriteAllText(FilePath, json);
        }
        catch { /* 持久化失败不阻塞 */ }
    }

    /// <summary>返回全部(最新在前)。</summary>
    public IReadOnlyList<RecentProblemItem> GetAll()
    {
        lock (_lock) return _cache.ToList();
    }

    /// <summary>记录一次浏览:去重后最新置顶,超出上限裁剪。</summary>
    public void Record(Guid problemId, string title, string code)
    {
        if (problemId == Guid.Empty) return;
        lock (_lock)
        {
            _cache.RemoveAll(x => x.ProblemId == problemId);
            _cache.Insert(0, new RecentProblemItem(problemId, title ?? "", code ?? "", DateTime.UtcNow));
            if (_cache.Count > MaxItems)
                _cache.RemoveRange(MaxItems, _cache.Count - MaxItems);
            Persist();
        }
    }
}
