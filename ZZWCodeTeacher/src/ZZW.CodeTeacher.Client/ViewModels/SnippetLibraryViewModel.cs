using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Client.Services;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 代码片段库 ViewModel。维护本地片段列表,提供 增/删/插入 操作。
/// Insert 触发 <see cref="InsertRequested"/> 事件,由 MainIdeViewModel 把 Content 追加到编辑器。
/// </summary>
public partial class SnippetLibraryViewModel : ViewModelBase
{
    private readonly SnippetStore _store;

    /// <summary>片段列表(供 UI 绑定)</summary>
    public ObservableCollection<SnippetDto> Items { get; } = new();

    [ObservableProperty]
    private SnippetDto? _selectedSnippet;

    [ObservableProperty]
    private string _newSnippetName = "";

    [ObservableProperty]
    private string _newSnippetLanguage = "";

    [ObservableProperty]
    private string _newSnippetContent = "";

    /// <summary>请求把指定片段内容插入到当前编辑器。</summary>
    public event EventHandler<string>? InsertRequested;

    public SnippetLibraryViewModel(SnippetStore store)
    {
        _store = store;
        Reload();
    }

    /// <summary>从存储重新加载到内存集合(UI 刷新时调用)。</summary>
    public void Reload()
    {
        Items.Clear();
        foreach (var s in _store.GetAll()) Items.Add(s);
    }

    /// <summary>添加新片段(名称/内容非空才入库)。</summary>
    [RelayCommand]
    private void Add()
    {
        if (string.IsNullOrWhiteSpace(NewSnippetName) || string.IsNullOrWhiteSpace(NewSnippetContent)) return;
        var snippet = new SnippetDto(
            Guid.NewGuid(),
            NewSnippetName.Trim(),
            NewSnippetLanguage.Trim(),
            NewSnippetContent,
            DateTime.UtcNow);
        _store.Add(snippet);
        Items.Add(snippet);
        NewSnippetName = "";
        NewSnippetLanguage = "";
        NewSnippetContent = "";
    }

    /// <summary>删除指定片段。</summary>
    [RelayCommand]
    private void Delete(SnippetDto? snippet)
    {
        if (snippet is null) return;
        _store.Delete(snippet.Id);
        Items.Remove(snippet);
    }

    /// <summary>把指定片段内容插入到编辑器(触发事件由父 VM 处理)。</summary>
    [RelayCommand]
    private void Insert(SnippetDto? snippet)
    {
        if (snippet is null) return;
        InsertRequested?.Invoke(this, snippet.Content);
    }
}
