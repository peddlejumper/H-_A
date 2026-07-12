using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Microsoft.Extensions.DependencyInjection;
using ZZW.CodeTeacher.Client.ViewModels;
using ZZW.CodeTeacher.Client.Views;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>统一管理设置窗口,避免重复打开多个实例。</summary>
public sealed class SettingsWindowService
{
    private readonly IServiceProvider _services;
    private SettingsWindow? _window;

    public SettingsWindowService(IServiceProvider services)
    {
        _services = services;
    }

    public void OpenAiSettings()
    {
        if (_window is not null)
        {
            _window.Activate();
            return;
        }

        var vm = _services.GetRequiredService<SettingsViewModel>();
        var window = new SettingsWindow { DataContext = vm };
        window.Closed += (_, _) => _window = null;
        _window = window;

        if (global::Avalonia.Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime
            {
                MainWindow: Window owner
            })
        {
            window.Show(owner);
        }
        else
        {
            window.Show();
        }
    }
}
