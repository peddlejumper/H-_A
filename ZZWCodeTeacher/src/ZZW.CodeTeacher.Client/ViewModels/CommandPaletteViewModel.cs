using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>命令面板的单条命令项(标题 + 执行 Key,Icon 可选)。</summary>
public sealed record CommandItem(string Title, string Key, string? Icon = null);

/// <summary>
/// 命令面板 ViewModel(Ctrl+K / Cmd+K 触发)。
/// FilterText 过滤预置命令列表,ExecuteCommand 触发 <see cref="RequestExecute"/> 事件,
/// 由 MainWindowViewModel 实际执行各命令(导航/主题/登出/运行/提交 …)。
/// </summary>
public partial class CommandPaletteViewModel : ViewModelBase
{
    [ObservableProperty]
    private string _filterText = "";

    [ObservableProperty]
    private CommandItem? _selectedCommand;

    /// <summary>过滤后的命令列表(供 UI 绑定)。</summary>
    public ObservableCollection<CommandItem> FilteredCommands { get; } = new();

    private IReadOnlyList<CommandItem> _all = Array.Empty<CommandItem>();

    /// <summary>请求执行指定 Key 的命令(由 MainWindowViewModel 订阅处理)。</summary>
    public event EventHandler<string>? RequestExecute;

    /// <summary>设置可用命令全集(打开面板前由父 VM 根据当前状态刷新)。</summary>
    public void SetCommands(IEnumerable<CommandItem> commands)
    {
        _all = commands.ToList();
        ApplyFilter();
    }

    partial void OnFilterTextChanged(string value) => ApplyFilter();

    private void ApplyFilter()
    {
        var keyword = (FilterText ?? "").Trim();
        FilteredCommands.Clear();
        foreach (var c in _all)
        {
            if (string.IsNullOrEmpty(keyword) ||
                c.Title.Contains(keyword, StringComparison.OrdinalIgnoreCase))
            {
                FilteredCommands.Add(c);
            }
        }
        SelectedCommand = FilteredCommands.FirstOrDefault();
    }

    /// <summary>执行选中的命令项(由 UI 的 Enter 按键调用)。</summary>
    [RelayCommand]
    private void Execute(CommandItem? item)
    {
        if (item is null) return;
        RequestExecute?.Invoke(this, item.Key);
    }
}
