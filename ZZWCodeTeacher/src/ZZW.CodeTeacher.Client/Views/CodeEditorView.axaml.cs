using System.ComponentModel;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using AvaloniaEdit;
using AvaloniaEdit.Highlighting;
using AvaloniaEdit.Search;
using ZZW.CodeTeacher.Client.ViewModels;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.Views;

/// <summary>
/// 代码编辑器视图:基于 AvaloniaEdit,提供语法高亮、括号匹配、查找替换、行号。
/// TextEditor 不支持直接 MVVM 绑定 Document.Text,故在 code-behind 双向同步。
/// </summary>
public partial class CodeEditorView : UserControl
{
    private CodeEditorViewModel? _vm;
    private SearchPanel? _searchPanel;
    private bool _isSyncing;
    private bool _searchInstalled;

    public CodeEditorView()
    {
        InitializeComponent();

        // Tab 转空格(OJ 场景:避免不同语言 Tab 宽度不一致),替代旧的手工 OnKeyDown Tab 处理
        Editor.Options.ConvertTabsToSpaces = true;
        Editor.Options.IndentationSize = 4;

        // 编辑器文本变化 → 同步回 ViewModel(防循环)
        Editor.TextChanged += OnEditorTextChanged;

        // TextArea 在模板应用后才存在,延迟安装查找面板与快捷键
        Editor.Loaded += OnEditorLoaded;
    }

    private void OnEditorLoaded(object? sender, RoutedEventArgs e)
    {
        if (_searchInstalled) return;
        _searchInstalled = true;
        // 查找/替换面板:Install 自带匹配高亮,并注册 Ctrl+F / Ctrl+H
        _searchPanel = SearchPanel.Install(Editor);
        Editor.TextArea.KeyDown += OnEditorKeyDown;
    }

    protected override void OnDataContextChanged(EventArgs e)
    {
        base.OnDataContextChanged(e);

        if (_vm is not null)
            _vm.PropertyChanged -= OnVmPropertyChanged;

        _vm = DataContext as CodeEditorViewModel;

        if (_vm is not null)
        {
            _vm.PropertyChanged += OnVmPropertyChanged;
            // 初始化:Code / FontSize / TabWidth / 语法高亮
            PushCodeToEditor(_vm.Code);
            Editor.FontSize = _vm.FontSize;
            Editor.Options.IndentationSize = _vm.TabWidth;
            ApplyHighlighting(_vm.Language);
        }
    }

    private void OnVmPropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (_vm is null) return;
        switch (e.PropertyName)
        {
            case nameof(CodeEditorViewModel.Code):
                PushCodeToEditor(_vm.Code);
                break;
            case nameof(CodeEditorViewModel.FontSize):
                Editor.FontSize = _vm.FontSize;
                break;
            case nameof(CodeEditorViewModel.TabWidth):
                Editor.Options.IndentationSize = _vm.TabWidth;
                break;
            case nameof(CodeEditorViewModel.Language):
                ApplyHighlighting(_vm.Language);
                break;
        }
    }

    /// <summary>编辑器文本变化 → ViewModel.Code(用标志位防止双向循环)</summary>
    private void OnEditorTextChanged(object? sender, EventArgs e)
    {
        if (_isSyncing || _vm is null) return;
        _isSyncing = true;
        try { _vm.Code = Editor.Document.Text; }
        finally { _isSyncing = false; }
    }

    /// <summary>ViewModel.Code → 编辑器(仅在差异时写入,防循环)</summary>
    private void PushCodeToEditor(string code)
    {
        if (_isSyncing) return;
        var text = code ?? "";
        if (Editor.Document.Text != text)
        {
            _isSyncing = true;
            try { Editor.Document.Text = text; }
            finally { _isSyncing = false; }
        }
    }

    /// <summary>Ctrl+F 查找 / Ctrl+H 替换:打开 SearchPanel</summary>
    private void OnEditorKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.KeyModifiers != KeyModifiers.Control) return;
        if (e.Key == Key.F)
        {
            OpenSearchPanel(replace: false);
            e.Handled = true;
        }
        else if (e.Key == Key.H)
        {
            OpenSearchPanel(replace: true);
            e.Handled = true;
        }
    }

    /// <summary>
    /// 打开查找/替换面板。SearchPanel 无 public Open(),通过置 IsClosed=false 显示,
    /// 再设 IsReplaceMode 与 Reactivate 聚焦搜索框;反射失败则回落到内置 Ctrl+F 绑定。
    /// </summary>
    private void OpenSearchPanel(bool replace)
    {
        if (_searchPanel is null) return;
        _searchPanel.IsReplaceMode = replace;
        try
        {
            var prop = typeof(SearchPanel).GetProperty("IsClosed");
            if (prop?.CanWrite == true)
                prop.SetValue(_searchPanel, false);
        }
        catch { /* 忽略:回落到 SearchPanel.Install 内置的 Ctrl+F 绑定 */ }
        _searchPanel.Reactivate();
    }

    /// <summary>按 SupportedLanguage 切换语法高亮;无内置定义则回落无高亮(不崩溃)</summary>
    private void ApplyHighlighting(SupportedLanguage lang)
    {
        try
        {
            var name = HighlightName(lang);
            Editor.SyntaxHighlighting = string.IsNullOrEmpty(name)
                ? null
                : HighlightingManager.Instance.GetDefinition(name);
        }
        catch
        {
            Editor.SyntaxHighlighting = null;
        }
    }

    /// <summary>SupportedLanguage → AvaloniaEdit 内置高亮定义名(无内置则 null)</summary>
    private static string? HighlightName(SupportedLanguage lang) => lang switch
    {
        SupportedLanguage.Python => "Python",
        SupportedLanguage.JavaScript => "JavaScript",
        SupportedLanguage.TypeScript => "TypeScript",
        SupportedLanguage.Java => "Java",
        SupportedLanguage.C => "C",
        SupportedLanguage.Cpp => "C++",
        SupportedLanguage.CSharp => "C#",
        SupportedLanguage.Go => "Go",
        SupportedLanguage.Rust => "Rust",
        SupportedLanguage.Ruby => "Ruby",
        SupportedLanguage.PHP => "PHP",
        SupportedLanguage.Swift => "Swift",
        SupportedLanguage.Kotlin => "Kotlin",
        SupportedLanguage.Scala => "Scala",
        SupportedLanguage.HSharp => null,
        _ => null
    };
}
