using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>代码片段实体(本地持久化)。</summary>
public sealed record SnippetDto(Guid Id, string Name, string Language, string Content, DateTime CreatedAt)
{
    /// <summary>列表显示名(带语言后缀)</summary>
    public string DisplayName => string.IsNullOrWhiteSpace(Language) ? Name : $"{Name} [{Language}]";
}

/// <summary>
/// 代码片段库本地存储。%AppData%/ZZWCodeTeacher/snippets.json,内容 List{SnippetDto}。
/// CRUD:GetAll/Add/Update/Delete。持久化模式参考 DraftStore / AiSettingsStore。
/// </summary>
public sealed class SnippetStore
{
    private static readonly string Dir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ZZWCodeTeacher");
    private static readonly string FilePath = Path.Combine(Dir, "snippets.json");

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    private readonly object _lock = new();
    private List<SnippetDto> _cache = new();

    public SnippetStore() => Load();

    private void Load()
    {
        try
        {
            if (!File.Exists(FilePath)) return;
            var json = File.ReadAllText(FilePath);
            var list = JsonSerializer.Deserialize<List<SnippetDto>>(json, JsonOpts);
            if (list is not null) _cache = list;
        }
        catch
        {
            _cache = new List<SnippetDto>();
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
        catch { /* 磁盘写入失败不阻塞 UI */ }
    }

    public IReadOnlyList<SnippetDto> GetAll()
    {
        lock (_lock) return _cache.ToList();
    }

    public void Add(SnippetDto snippet)
    {
        lock (_lock) { _cache.Add(snippet); Persist(); }
    }

    public void Update(Guid id, SnippetDto updated)
    {
        lock (_lock)
        {
            var idx = _cache.FindIndex(x => x.Id == id);
            if (idx >= 0) { _cache[idx] = updated; Persist(); }
        }
    }

    public void Delete(Guid id)
    {
        lock (_lock)
        {
            var idx = _cache.FindIndex(x => x.Id == id);
            if (idx >= 0) { _cache.RemoveAt(idx); Persist(); }
        }
    }
}
