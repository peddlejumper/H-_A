using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using ZZW.CodeTeacher.Client.ViewModels;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.Views;

public partial class MainIdeView : UserControl
{
    private static readonly string[] s_imageFilePatterns = { "*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp" };
    private static readonly string[] s_allFilesPattern = { "*.*" };
    private static readonly string[] s_markdownFilePattern = { "*.md" };

    public MainIdeView() => InitializeComponent();

    /// <summary>选择自定义窗口背景图片。</summary>
    private async void OnChooseBackgroundClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is not MainIdeViewModel vm) return;
        var topLevel = TopLevel.GetTopLevel(this);
        if (topLevel?.StorageProvider is not { } sp) return;

        var files = await sp.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "选择背景图片",
            AllowMultiple = false,
            FileTypeFilter = new[]
            {
                new FilePickerFileType("图片文件") { Patterns = s_imageFilePatterns },
                new FilePickerFileType("所有文件") { Patterns = s_allFilesPattern }
            }
        });

        var file = files.Count > 0 ? files[0] : null;
        var path = file?.Path.LocalPath;
        if (!string.IsNullOrWhiteSpace(path))
            vm.SetCustomBackground(path);
    }

    /// <summary>清除自定义窗口背景图片。</summary>
    private void OnClearBackgroundClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is MainIdeViewModel vm)
            vm.ClearCustomBackground();
    }

    /// <summary>导出当前编辑器代码为本地文件(根据语言决定后缀)。</summary>
    private async void OnExportCodeClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is not MainIdeViewModel vm) return;
        var code = vm.Editor.Code ?? "";
        var lang = vm.Editor.Language;
        var problemCode = string.IsNullOrWhiteSpace(vm.Editor.CurrentProblemCode) ? "untitled" : vm.Editor.CurrentProblemCode;
        var ext = lang.FileExtension();
        var defaultName = $"{problemCode}{ext}";

        var topLevel = TopLevel.GetTopLevel(this);
        if (topLevel?.StorageProvider is not { } sp) return;

        var file = await sp.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = "导出代码",
            DefaultExtension = ext.TrimStart('.'),
            SuggestedFileName = defaultName,
            FileTypeChoices = new[]
            {
                new FilePickerFileType($"{lang.DisplayName()} 源文件") { Patterns = new[] { $"*{ext}" } },
                new FilePickerFileType("所有文件") { Patterns = s_allFilesPattern }
            }
        });
        if (file is null) return;

        await using var stream = await file.OpenWriteAsync();
        using var writer = new System.IO.StreamWriter(stream);
        await writer.WriteAsync(code);
    }

    /// <summary>导出当前题目 AI 对话为 Markdown 文件。</summary>
    private async void OnExportChatClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is not MainIdeViewModel vm) return;
        var content = vm.AiChat.ExportMarkdown();
        var pid = string.IsNullOrWhiteSpace(vm.AiChat.CurrentProblemId) ? "对话" : vm.AiChat.CurrentProblemId;
        var defaultName = $"ai-chat-{pid}-{DateTime.Now:yyyyMMdd-HHmm}.md";

        var topLevel = TopLevel.GetTopLevel(this);
        if (topLevel?.StorageProvider is not { } sp) return;

        var file = await sp.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = "导出 AI 对话",
            DefaultExtension = "md",
            SuggestedFileName = defaultName,
            FileTypeChoices = new[]
            {
                new FilePickerFileType("Markdown 文件") { Patterns = s_markdownFilePattern },
                new FilePickerFileType("所有文件") { Patterns = s_allFilesPattern }
            }
        });
        if (file is null) return;

        await using var stream = await file.OpenWriteAsync();
        using var writer = new System.IO.StreamWriter(stream);
        await writer.WriteAsync(content);
    }

    /// <summary>全局快捷键:Ctrl+Enter 提交、Ctrl+R 运行样例、Ctrl+S 保存草稿(实际已自动保存)。</summary>
    protected override void OnKeyDown(KeyEventArgs e)
    {
        if (DataContext is MainIdeViewModel vm)
        {
            var ctrl = e.KeyModifiers.HasFlag(KeyModifiers.Control);
            if (ctrl && e.Key == Key.Enter)
            {
                e.Handled = true;
                vm.SubmitCommand.Execute(null);
                return;
            }
            if (ctrl && e.Key == Key.R)
            {
                e.Handled = true;
                vm.RunSampleCommand.Execute(null);
                return;
            }
            if (ctrl && e.Key == Key.S)
            {
                // 草稿已自动保存,此处仅吞掉系统默认行为
                e.Handled = true;
                return;
            }
        }
        base.OnKeyDown(e);
    }
}
