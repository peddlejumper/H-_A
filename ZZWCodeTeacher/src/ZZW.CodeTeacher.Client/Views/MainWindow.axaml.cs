using Avalonia.Controls;
using Avalonia.Input;
using ZZW.CodeTeacher.Client.ViewModels;

namespace ZZW.CodeTeacher.Client.Views;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        var searchBox = this.FindControl<TextBox>("PaletteSearchBox");
        if (searchBox is not null)
            searchBox.KeyDown += OnPaletteKeyDown;
    }

    /// <summary>
    /// 全局快捷键:
    /// Alt+1 → IDE,Alt+2 → 学习画像,Alt+3 → 教师后台(仅教师),Alt+4 → AI 设置,
    /// Ctrl+, → 打开 AI 设置,Ctrl+K/Cmd+K → 命令面板,Esc → 关闭命令面板。
    /// </summary>
    protected override void OnKeyDown(KeyEventArgs e)
    {
        if (DataContext is MainWindowViewModel vm)
        {
            var ctrl = e.KeyModifiers.HasFlag(KeyModifiers.Control);
            var meta = e.KeyModifiers.HasFlag(KeyModifiers.Meta);

            // 命令面板 Ctrl+K / Cmd+K
            if ((ctrl || meta) && e.Key == Key.K)
            {
                e.Handled = true;
                vm.ToggleCommandPaletteCommand.Execute(null);
                if (vm.IsCommandPaletteOpen)
                {
                    var box = this.FindControl<TextBox>("PaletteSearchBox");
                    box?.Focus();
                }
                return;
            }

            // Esc 关闭命令面板
            if (e.Key == Key.Escape && vm.IsCommandPaletteOpen)
            {
                e.Handled = true;
                vm.IsCommandPaletteOpen = false;
                return;
            }

            // Alt+1/2/3/4 切页签
            if (e.KeyModifiers.HasFlag(KeyModifiers.Alt))
            {
                switch (e.Key)
                {
                    case Key.D1:
                    case Key.NumPad1:
                        e.Handled = true; vm.NavigateToView("ide"); return;
                    case Key.D2:
                    case Key.NumPad2:
                        e.Handled = true; vm.NavigateToView("profile"); return;
                    case Key.D3:
                    case Key.NumPad3:
                        e.Handled = true; vm.NavigateToView("teacher"); return;
                    case Key.D4:
                    case Key.NumPad4:
                        e.Handled = true; vm.NavigateToView("aisettings"); return;
                }
            }

            // Ctrl+, 打开设置(AI 设置)
            if (ctrl && e.Key == Key.OemComma)
            {
                e.Handled = true;
                vm.NavigateToView("aisettings");
                return;
            }
        }
        base.OnKeyDown(e);
    }

    /// <summary>命令面板内按键:Enter 执行选中、Esc 关闭、Up/Down 导航。</summary>
    private void OnPaletteKeyDown(object? sender, KeyEventArgs e)
    {
        if (DataContext is not MainWindowViewModel vm || !vm.IsCommandPaletteOpen) return;
        switch (e.Key)
        {
            case Key.Enter:
                e.Handled = true;
                if (vm.CommandPalette.SelectedCommand is not null)
                    vm.CommandPalette.ExecuteCommand.Execute(vm.CommandPalette.SelectedCommand);
                break;
            case Key.Escape:
                e.Handled = true;
                vm.IsCommandPaletteOpen = false;
                break;
            case Key.Up:
                e.Handled = true;
                MovePaletteSelection(-1);
                break;
            case Key.Down:
                e.Handled = true;
                MovePaletteSelection(1);
                break;
        }
    }

    private void MovePaletteSelection(int delta)
    {
        if (DataContext is not MainWindowViewModel vm) return;
        var list = vm.CommandPalette.FilteredCommands;
        if (list.Count == 0) return;
        var idx = vm.CommandPalette.SelectedCommand is null
            ? -1
            : list.IndexOf(vm.CommandPalette.SelectedCommand);
        idx = Math.Clamp(idx + delta, 0, list.Count - 1);
        vm.CommandPalette.SelectedCommand = list[idx];
    }

    private void OnTitleBarPointerPressed(object? sender, PointerPressedEventArgs e)
    {
        var point = e.GetCurrentPoint(this);
        if (!point.Properties.IsLeftButtonPressed)
            return;

        if (e.ClickCount == 2)
        {
            ToggleMaximize();
            e.Handled = true;
            return;
        }

        BeginMoveDrag(e);
    }

    private void OnMinimizeClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
    {
        WindowState = WindowState.Minimized;
    }

    private void OnToggleMaximizeClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
    {
        ToggleMaximize();
    }

    private void OnCloseClick(object? sender, Avalonia.Interactivity.RoutedEventArgs e)
    {
        Close();
    }

    private void ToggleMaximize()
    {
        WindowState = WindowState == WindowState.Maximized
            ? WindowState.Normal
            : WindowState.Maximized;
    }
}
