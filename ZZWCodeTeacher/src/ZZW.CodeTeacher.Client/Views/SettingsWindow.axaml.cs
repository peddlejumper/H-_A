using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using ZZW.CodeTeacher.Client.ViewModels;

namespace ZZW.CodeTeacher.Client.Views;

public partial class SettingsWindow : Window
{
    private ViewModelBase? _subscribedVm;
    private ViewModelBase? _subscribedChildVm;

    public SettingsWindow()
    {
        InitializeComponent();
    }

    protected override void OnDataContextChanged(EventArgs e)
    {
        if (_subscribedVm is not null)
            _subscribedVm.RequestViewChange -= OnRequestViewChange;
        if (_subscribedChildVm is not null)
            _subscribedChildVm.RequestViewChange -= OnRequestViewChange;

        _subscribedVm = DataContext as ViewModelBase;
        _subscribedChildVm = null;
        if (_subscribedVm is not null)
            _subscribedVm.RequestViewChange += OnRequestViewChange;

        if (DataContext is SettingsViewModel settings)
        {
            _subscribedChildVm = settings.AiSettings;
            _subscribedChildVm.RequestViewChange += OnRequestViewChange;
        }

        base.OnDataContextChanged(e);
    }

    protected override void OnClosed(EventArgs e)
    {
        if (_subscribedVm is not null)
            _subscribedVm.RequestViewChange -= OnRequestViewChange;
        if (_subscribedChildVm is not null)
            _subscribedChildVm.RequestViewChange -= OnRequestViewChange;
        _subscribedVm = null;
        _subscribedChildVm = null;
        base.OnClosed(e);
    }

    private void OnRequestViewChange(object? sender, ViewModelBase? next)
    {
        if (next is null)
            Close();
    }

    private void OnTitleBarPointerPressed(object? sender, PointerPressedEventArgs e)
    {
        var point = e.GetCurrentPoint(this);
        if (!point.Properties.IsLeftButtonPressed)
            return;

        BeginMoveDrag(e);
    }

    private void OnCloseClick(object? sender, RoutedEventArgs e)
    {
        Close();
    }

    private async void OnChooseBackgroundClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is not SettingsViewModel vm)
            return;

        var files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "选择背景图片",
            AllowMultiple = false,
            FileTypeFilter =
            [
                new FilePickerFileType("图片文件")
                {
                    Patterns = ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"]
                },
                FilePickerFileTypes.All
            ]
        });

        var path = files.Count > 0 ? files[0].TryGetLocalPath() : null;
        if (!string.IsNullOrWhiteSpace(path))
            vm.SetBackgroundImage(path);
    }

    /// <summary>
    /// 编程语言运行环境:每行「浏览...」按钮点击,弹文件对话框选择可执行文件,
    /// 选定后通过 <see cref="SettingsViewModel.SetRuntimePath"/> 回填到对应行。
    /// </summary>
    private async void OnBrowseRuntimeClick(object? sender, RoutedEventArgs e)
    {
        if (DataContext is not SettingsViewModel vm)
            return;
        if (sender is not Button btn)
            return;
        if (btn.DataContext is not RuntimePathItemViewModel item)
            return;

        var files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = $"选择 {item.DisplayName} 可执行文件",
            AllowMultiple = false,
            FileTypeFilter = [FilePickerFileTypes.All]
        });

        var path = files.Count > 0 ? files[0].TryGetLocalPath() : null;
        if (!string.IsNullOrWhiteSpace(path))
            vm.SetRuntimePath(item.Language, path);
    }
}
