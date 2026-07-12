using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Markup.Xaml;
using Avalonia.Threading;
using System;
using System.Diagnostics;
using System.Threading.Tasks;
using System.IO.Compression;

namespace IDE.UI
{
    public partial class LauncherWindow : Window
    {
        private bool _advancedOpen;

        public LauncherWindow()
        {
            InitializeComponent();
            this.Opened += LauncherWindow_Opened;
        }

        private void OnMinimize(object? sender, RoutedEventArgs e)
        {
            WindowState = WindowState.Minimized;
        }

        private void OnClose(object? sender, RoutedEventArgs e)
        {
            Close();
        }

        private void OnTitleBarPressed(object? sender, PointerPressedEventArgs e)
        {
            if (e.GetCurrentPoint(this).Properties.IsLeftButtonPressed)
            {
                BeginMoveDrag(e);
            }
        }

        private void InitializeComponent()
        {
            AvaloniaXamlLoader.Load(this);
        }

        private async void LauncherWindow_Opened(object? sender, EventArgs e)
        {
            await UpdateStatusAsync();
        }

        private async Task UpdateStatusAsync()
        {
            var res = await EnvironmentChecker.CheckAsync();

            SetStatusIcon("PythonIcon", "PythonStatus", res.HasPython,
                res.HasPython
                    ? $"Python  ✓   {res.PythonExecutable}"
                    : "Python  ✗   not found");

            SetStatusIcon("PipIcon", "PipStatus", res.HasPip,
                res.HasPip ? "pip  ✓   available" : "pip  ✗   unavailable");

            SetStatusIcon("PyQtIcon", "PyQtStatus", res.PyQt5Installed,
                res.PyQt5Installed ? "PyQt5  ✓   installed" : "PyQt5  ✗   not installed");

            SetStatusIcon("HSharpIcon", "HSharpStatus", res.HSharpPyFound,
                res.HSharpPyFound ? "H# Runtime  ✓   found" : "H# Runtime  ✗   not found");

            var hasQoder = await EnvironmentChecker.HasQoderAsync();
            SetStatusIcon("QoderIcon", "QoderStatus", hasQoder,
                hasQoder ? "qoder CN  ✓   available" : "qoder CN  ✗   not configured");

            var selectedCompiler = LauncherConfig.GetSelectedCompilerPath();
            var hasCompiler = !string.IsNullOrEmpty(selectedCompiler);
            SetStatusIcon("CompilerIcon", "CompilerStatus", hasCompiler,
                hasCompiler ? $"Compiler  ◎   {selectedCompiler}" : "Compiler  ◎   not selected");

            var checkingLabel = this.FindControl<TextBlock>("CheckingLabel");
            var readyLabel = this.FindControl<TextBlock>("ReadyLabel");
            if (checkingLabel != null) checkingLabel.IsVisible = false;
            if (readyLabel != null) readyLabel.IsVisible = true;

            var launchPyQt = this.FindControl<Button>("LaunchPyQtButton");
            if (launchPyQt != null)
                launchPyQt.IsEnabled = res.HasPython && res.PyQt5Installed && res.HSharpPyFound;

            var installBtn = this.FindControl<Button>("InstallMissingBtn");
            if (installBtn != null)
                installBtn.IsEnabled = !res.HasPython || !res.HasPip || !res.PyQt5Installed;

            var compilerPath = this.FindControl<TextBlock>("AdvancedCompilerPath");
            if (compilerPath != null)
                compilerPath.Text = hasCompiler ? selectedCompiler : "not set";

            var pythonPath = this.FindControl<TextBlock>("AdvancedPythonPath");
            if (pythonPath != null)
                pythonPath.Text = res.HasPython ? res.PythonExecutable : "not installed";

            AppendOutput($"Environment check complete. Python:{res.HasPython} pip:{res.HasPip} PyQt5:{res.PyQt5Installed} H#:{res.HSharpPyFound} qoder:{hasQoder}");
        }

        private void SetStatusIcon(string iconName, string statusName, bool ok, string statusText)
        {
            var icon = this.FindControl<TextBlock>(iconName);
            var status = this.FindControl<TextBlock>(statusName);
            if (icon != null)
            {
                icon.Text = ok ? "●" : "○";
                icon.Foreground = ok
                    ? Avalonia.Media.SolidColorBrush.Parse("#4a90d9")
                    : Avalonia.Media.SolidColorBrush.Parse("#cc4444");
            }
            if (status != null)
            {
                status.Text = statusText;
                status.Foreground = ok
                    ? Avalonia.Media.SolidColorBrush.Parse("#333333")
                    : Avalonia.Media.SolidColorBrush.Parse("#cc4444");
            }
        }

        private void OnToggleAdvanced(object? sender, RoutedEventArgs e)
        {
            _advancedOpen = !_advancedOpen;
            var panel = this.FindControl<StackPanel>("AdvancedPanel");
            var toggle = this.FindControl<Button>("AdvancedToggle");
            if (panel != null) panel.IsVisible = _advancedOpen;
            if (toggle != null)
                toggle.Content = _advancedOpen ? "▾  Advanced Options" : "▸  Advanced Options";
        }

        private void AppendOutput(string s)
        {
            Dispatcher.UIThread.Post(() =>
            {
                var outBox = this.FindControl<TextBox>("OutputBox");
                if (outBox != null)
                    outBox.Text += s + "\n";
            });
        }

        private async void OnRefreshStatus(object? sender, RoutedEventArgs e)
        {
            AppendOutput("Re-checking environment...");
            var checkingLabel = this.FindControl<TextBlock>("CheckingLabel");
            var readyLabel = this.FindControl<TextBlock>("ReadyLabel");
            if (checkingLabel != null) checkingLabel.IsVisible = true;
            if (readyLabel != null) readyLabel.IsVisible = false;
            await UpdateStatusAsync();
        }

        private void OnClearOutput(object? sender, RoutedEventArgs e)
        {
            var outBox = this.FindControl<TextBox>("OutputBox");
            if (outBox != null) outBox.Text = "";
        }

        private async void OnInstallMissing(object? sender, RoutedEventArgs e)
        {
            AppendOutput("Installing missing dependencies...");
            var res = await EnvironmentChecker.CheckAsync();

            if (!res.HasPython)
            {
                AppendOutput("Python not found — trying Homebrew...");
                var ok = await EnvironmentChecker.TryInstallPythonWithBrewAsync();
                AppendOutput(ok ? "brew install done." : "brew unavailable. Install manually: https://www.python.org/downloads/");
            }

            res = await EnvironmentChecker.CheckAsync();
            if (res.HasPython && !res.HasPip)
            {
                AppendOutput("Installing pip...");
                var ok = await EnvironmentChecker.TryEnsurePipAsync(res.PythonExecutable);
                AppendOutput(ok ? "pip ready." : "pip install failed.");
            }

            res = await EnvironmentChecker.CheckAsync();
            if (res.HasPython && !res.PyQt5Installed)
            {
                AppendOutput("Installing PyQt5...");
                var ok = await EnvironmentChecker.TryInstallPipPackageAsync(res.PythonExecutable, "PyQt5");
                AppendOutput(ok ? "PyQt5 installed." : "PyQt5 install failed.");
            }

            await UpdateStatusAsync();
        }

        private void OnOpenPythonOrg(object? sender, RoutedEventArgs e)
        {
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = "https://www.python.org/downloads/",
                    UseShellExecute = true
                });
                AppendOutput("Opening python.org...");
            }
            catch (Exception ex)
            {
                AppendOutput("Browser error: " + ex.Message);
            }
        }

        private async void OnLaunchPyQt(object? sender, RoutedEventArgs e)
        {
            AppendOutput("Launching PyQt IDE...");
            var res = await EnvironmentChecker.CheckAsync();
            var python = res.PythonExecutable ?? "python3";
            var script = EnvironmentChecker.FindScript("idle_pyqt.py");
            if (script == null)
            {
                AppendOutput("Script idle_pyqt.py not found.");
                return;
            }
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = python,
                    Arguments = $"\"{script}\"",
                    UseShellExecute = true
                });
                AppendOutput("PyQt IDE launched.");
            }
            catch (Exception ex)
            {
                AppendOutput("Launch failed: " + ex.Message);
            }
        }

        private async void OnUseQoder(object? sender, RoutedEventArgs e)
        {
            AppendOutput("Select .hto file for qoder...");
            var dlg = new OpenFileDialog
            {
                AllowMultiple = false,
                Filters = new System.Collections.Generic.List<FileDialogFilter>
                {
                    new FileDialogFilter { Name = "H# Source", Extensions = { "hto" } },
                    new FileDialogFilter { Name = "All Files", Extensions = { "*" } }
                }
            };
            var result = await dlg.ShowAsync(this);
            if (result == null || result.Length == 0) return;
            var file = result[0];
            AppendOutput($"Compiling: {file}");
            try
            {
                var (ok, outp) = await EnvironmentChecker.CompileWithQoderAsync(file);
                AppendOutput(ok ? $"qoder OK:\n{outp}" : $"qoder FAILED:\n{outp}");
            }
            catch (Exception ex)
            {
                AppendOutput("qoder error: " + ex.Message);
            }
        }

        private async void OnSelectCompiler(object? sender, RoutedEventArgs e)
        {
            AppendOutput("Select H# compiler (.py)...");
            var dlg = new OpenFileDialog
            {
                AllowMultiple = false,
                Filters = new System.Collections.Generic.List<FileDialogFilter>
                {
                    new FileDialogFilter { Name = "Python", Extensions = { "py" } },
                    new FileDialogFilter { Name = "All", Extensions = { "*" } }
                }
            };
            var result = await dlg.ShowAsync(this);
            if (result == null || result.Length == 0) return;
            var path = result[0];
            AppendOutput($"Compiler: {path}");
            LauncherConfig.SetSelectedCompilerPath(path);
            Environment.SetEnvironmentVariable("HSHARP_COMPILER", path);
            await UpdateStatusAsync();
        }

        private void OnLaunchCSharp(object? sender, RoutedEventArgs e)
        {
            AppendOutput("Opening C# IDE...");
            if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
            {
                var main = new MainWindow();
                desktop.MainWindow = main;
                main.Show();
                this.Close();
            }
        }

        private async void OnLoadHps(object? sender, RoutedEventArgs e)
        {
            AppendOutput("Select .hps package...");
            var dlg = new OpenFileDialog
            {
                AllowMultiple = false,
                Filters = new System.Collections.Generic.List<FileDialogFilter>
                {
                    new FileDialogFilter { Name = "H# Package", Extensions = { "hps", "zip" } },
                    new FileDialogFilter { Name = "All", Extensions = { "*" } }
                }
            };
            var result = await dlg.ShowAsync(this);
            if (result == null || result.Length == 0) return;
            var hps = result[0];
            AppendOutput($"Package: {hps}");

            try
            {
                var tmp = Path.Combine(Path.GetTempPath(), "hsharp_pkg_" + Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(tmp);
                ZipFile.ExtractToDirectory(hps, tmp);
                AppendOutput("Extracted to temp directory.");

                // ── 使用 H# 解释器检查包 ──
                var res = await EnvironmentChecker.CheckAsync();
                string? python = res.HasPython ? res.PythonExecutable : null;
                if (python == null)
                {
                    AppendOutput("Warning: Python not found. Skipping H# package inspection.");
                    AppendOutput("Package extracted to: " + tmp);
                    Environment.SetEnvironmentVariable("HSHARP_PKG_DIR", tmp);
                    return;
                }

                // 优先使用包内自带的 hsharp.py，否则用系统安装的
                string? hsharpPy = null;
                var pkgHsharpPy = Path.Combine(tmp, "hsharp.py");
                if (File.Exists(pkgHsharpPy))
                {
                    hsharpPy = pkgHsharpPy;
                }
                else
                {
                    hsharpPy = EnvironmentChecker.FindScript("hsharp.py");
                }

                // pkg_inspect.hto — 优先用包内的，否则用系统安装的
                string? inspectorScript = null;
                var pkgInspector = Path.Combine(tmp, "bootstrap", "pkg_inspect.hto");
                if (File.Exists(pkgInspector))
                {
                    inspectorScript = pkgInspector;
                }
                else
                {
                    // 查找系统安装的 pkg_inspect.hto
                    var sysInspector = EnvironmentChecker.FindScript("pkg_inspect.hto");
                    if (sysInspector != null)
                        inspectorScript = sysInspector;
                }

                if (hsharpPy == null && inspectorScript == null)
                {
                    AppendOutput("H# inspector not found. Loading package directly...");
                    Environment.SetEnvironmentVariable("HSHARP_PKG_DIR", tmp);
                    AppendOutput("Package loaded. Use 'Open C# IDE' to explore.");
                    return;
                }

                // 运行 H# 包检查
                if (hsharpPy != null && inspectorScript != null)
                {
                    AppendOutput("Running H# package inspector...");
                    var psi = new ProcessStartInfo
                    {
                        FileName = python,
                        Arguments = $"\"{hsharpPy}\" \"{inspectorScript}\"",
                        WorkingDirectory = tmp,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    };

                    using var p = new Process { StartInfo = psi };
                    var sbOut = new System.Text.StringBuilder();
                    var sbErr = new System.Text.StringBuilder();
                    p.OutputDataReceived += (s, ev) => { if (ev.Data != null) sbOut.AppendLine(ev.Data); };
                    p.ErrorDataReceived += (s, ev) => { if (ev.Data != null) sbErr.AppendLine(ev.Data); };

                    p.Start();
                    p.BeginOutputReadLine();
                    p.BeginErrorReadLine();
                    await p.WaitForExitAsync();

                    var stdout = sbOut.ToString();
                    var stderr = sbErr.ToString();

                    if (!string.IsNullOrWhiteSpace(stderr))
                        AppendOutput("[H# stderr]: " + stderr.Trim());

                    if (!string.IsNullOrWhiteSpace(stdout))
                    {
                        foreach (var line in stdout.Split('\n'))
                        {
                            var trimmed = line.Trim();
                            if (!string.IsNullOrEmpty(trimmed))
                                AppendOutput("  " + trimmed);
                        }
                    }

                    if (p.ExitCode == 0)
                    {
                        AppendOutput("Package validation: PASSED");
                        Environment.SetEnvironmentVariable("HSHARP_PKG_DIR", tmp);

                        var confirmed = await ShowConfirmDialog(
                            "H# Package Loaded",
                            "Package validated successfully.\n\n" +
                            "Set as current H# environment and open C# IDE?");
                        if (confirmed)
                        {
                            OnLaunchCSharp(null!, null!);
                        }
                        else
                        {
                            AppendOutput("Package extracted. Use 'Open C# IDE' when ready.");
                        }
                    }
                    else
                    {
                        AppendOutput("Package validation: WARNINGS (see above)");
                        Environment.SetEnvironmentVariable("HSHARP_PKG_DIR", tmp);
                        AppendOutput("Package extracted anyway: " + tmp);
                    }
                }
                else
                {
                    Environment.SetEnvironmentVariable("HSHARP_PKG_DIR", tmp);
                    AppendOutput("Package extracted. Use 'Open C# IDE' to explore.");
                }
            }
            catch (Exception ex)
            {
                AppendOutput("Load .hps failed: " + ex.Message);
            }
        }

        private async Task<bool> ShowConfirmDialog(string title, string message)
        {
            var dialog = new Window
            {
                Title = title,
                Width = 420,
                Height = 200,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                ShowInTaskbar = false,
                CanResize = false,
                Background = Avalonia.Media.SolidColorBrush.Parse("#f0f0f0"),
                FontFamily = this.FontFamily,
                FontSize = 13
            };

            var panel = new StackPanel { Margin = new Thickness(20, 16) };

            panel.Children.Add(new TextBlock
            {
                Text = message,
                TextWrapping = Avalonia.Media.TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 16),
                Foreground = Avalonia.Media.SolidColorBrush.Parse("#333333")
            });

            var buttons = new StackPanel { Orientation = Avalonia.Layout.Orientation.Horizontal, HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Right };
            var tcs = new TaskCompletionSource<bool>();

            var cancelBtn = new Button
            {
                Content = "Cancel",
                Padding = new Thickness(16, 6),
                Margin = new Thickness(0, 0, 8, 0),
                Background = Avalonia.Media.SolidColorBrush.Parse("#e0e0e0"),
                Foreground = Avalonia.Media.SolidColorBrush.Parse("#333333"),
                CornerRadius = new CornerRadius(4),
                Cursor = new Avalonia.Input.Cursor(Avalonia.Input.StandardCursorType.Hand)
            };
            cancelBtn.Click += (_, _) => { tcs.TrySetResult(false); dialog.Close(); };

            var okBtn = new Button
            {
                Content = "Open IDE",
                Padding = new Thickness(16, 6),
                Background = Avalonia.Media.SolidColorBrush.Parse("#4a90d9"),
                Foreground = Avalonia.Media.SolidColorBrush.Parse("#ffffff"),
                FontWeight = Avalonia.Media.FontWeight.SemiBold,
                CornerRadius = new CornerRadius(4),
                Cursor = new Avalonia.Input.Cursor(Avalonia.Input.StandardCursorType.Hand)
            };
            okBtn.Click += (_, _) => { tcs.TrySetResult(true); dialog.Close(); };

            buttons.Children.Add(cancelBtn);
            buttons.Children.Add(okBtn);
            panel.Children.Add(buttons);
            dialog.Content = panel;

            dialog.Closed += (_, _) => tcs.TrySetResult(false);
            await dialog.ShowDialog(this);
            return await tcs.Task;
        }
    }
}