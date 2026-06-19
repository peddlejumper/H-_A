using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Shapes;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Threading;

namespace IDE.UI
{
    public class D3ViewerWindow : Window
    {
        private readonly Canvas _canvas;
        private readonly TextBlock _infoText;
        private readonly TextBlock _statusText;
        private readonly TextBlock _zoomLabel;
        private readonly MainWindow _owner;

        public D3ViewerWindow(MainWindow owner)
        {
            _owner = owner;
            Title = "H# D3 Viewer — 独立窗口";
            Width = 900;
            Height = 700;

            var grid = new Grid();
            grid.RowDefinitions.Add(new RowDefinition(GridLength.Auto));
            grid.RowDefinitions.Add(new RowDefinition(GridLength.Auto));
            grid.RowDefinitions.Add(new RowDefinition(new GridLength(1, GridUnitType.Star)));
            grid.RowDefinitions.Add(new RowDefinition(GridLength.Auto));

            // Row 0: Camera presets
            var presetBar = new WrapPanel { Margin = new Thickness(4, 4, 4, 2) };
            presetBar.Children.Add(MakeBtn("↻ 刷新", "#223344", "#88aacc", (s, e) => _owner.OnD3RefreshExternal()));
            presetBar.Children.Add(MakeBtn("⬆ 俯视", "#1a2a3a", "#88aacc", (s, e) => { _owner.SetCamPreset(0, 5, _owner.CamDist); _owner.OnD3RefreshExternal(); }));
            presetBar.Children.Add(MakeBtn("⏍ 正视", "#1a2a3a", "#88aacc", (s, e) => { _owner.SetCamPreset(270, 25, _owner.CamDist); _owner.OnD3RefreshExternal(); }));
            presetBar.Children.Add(MakeBtn("◫ 侧视", "#1a2a3a", "#88aacc", (s, e) => { _owner.SetCamPreset(0, 25, _owner.CamDist); _owner.OnD3RefreshExternal(); }));
            presetBar.Children.Add(MakeBtn("⟳ 重置", "#1a2a3a", "#ccaa44", (s, e) => { _owner.SetCamPreset(225, 35, 1.0); _owner.OnD3RefreshExternal(); }));
            presetBar.Children.Add(MakeBtn("停靠", "#2a1a1a", "#ccaa88", (s, e) => _owner.DockD3Viewer()));
            grid.Children.Add(presetBar);
            Grid.SetRow(presetBar, 0);

            // Row 1: Zoom controls
            var zoomBar = new WrapPanel { Margin = new Thickness(4, 0, 4, 3) };
            zoomBar.Children.Add(MakeBtn("◉ 适应", "#1a2a3a", "#88cc88", (s, e) => _owner.D3ZoomFitExternal()));
            zoomBar.Children.Add(MakeBtn("− 缩小", "#1a2a3a", "#88aacc", (s, e) => _owner.D3ZoomOutExternal()));
            zoomBar.Children.Add(MakeBtn("+ 放大", "#1a2a3a", "#88aacc", (s, e) => _owner.D3ZoomInExternal()));
            _zoomLabel = new TextBlock { Foreground = new SolidColorBrush(Color.Parse("#88aacc")), FontSize = 10, VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center, Margin = new Thickness(6, 0, 0, 0), Text = $"{_owner.CamDist:F1}×" };
            zoomBar.Children.Add(_zoomLabel);
            grid.Children.Add(zoomBar);
            Grid.SetRow(zoomBar, 1);

            // Row 2: Canvas
            _canvas = new Canvas { Background = new SolidColorBrush(Color.Parse("#0a0a14")) };
            _canvas.PointerPressed += (s, e) => _owner.OnD3CanvasMouseDownExternal(_canvas, e);
            _canvas.PointerMoved += (s, e) => _owner.OnD3CanvasMouseMoveExternal(_canvas, e);
            _canvas.PointerReleased += (s, e) => _owner.OnD3CanvasMouseUpExternal();
            _canvas.PointerWheelChanged += (s, e) => _owner.OnD3CanvasMouseWheelExternal(e);
            grid.Children.Add(_canvas);
            Grid.SetRow(_canvas, 2);

            // Row 3: Status bar
            var statusBar = new Border { Background = new SolidColorBrush(Color.Parse("#0c141e")), Padding = new Thickness(4, 3), Margin = new Thickness(0, 4, 0, 0), CornerRadius = new CornerRadius(2) };
            var dock = new DockPanel();
            _infoText = new TextBlock { Foreground = new SolidColorBrush(Color.Parse("#88aacc")), FontSize = 9, VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center };
            DockPanel.SetDock(_infoText, Dock.Right);
            _statusText = new TextBlock { Foreground = new SolidColorBrush(Color.Parse("#5588aa")), FontSize = 9 };
            dock.Children.Add(_infoText);
            dock.Children.Add(_statusText);
            statusBar.Child = dock;
            grid.Children.Add(statusBar);
            Grid.SetRow(statusBar, 3);

            Content = grid;
        }

        public Canvas D3Canvas => _canvas;
        public TextBlock InfoText => _infoText;
        public TextBlock StatusText => _statusText;
        public TextBlock ZoomLabel => _zoomLabel;

        public void UpdateZoomLabel(double zoom) => _zoomLabel.Text = $"{zoom:F1}×";

        private static Button MakeBtn(string text, string bg, string fg, EventHandler<RoutedEventArgs> click)
        {
            var btn = new Button
            {
                Content = text,
                Padding = new Thickness(6, 3),
                Background = new SolidColorBrush(Color.Parse(bg)),
                Foreground = new SolidColorBrush(Color.Parse(fg)),
                FontSize = 10
            };
            btn.Click += click;
            return btn;
        }

        protected override void OnClosing(WindowClosingEventArgs e)
        {
            _owner.Window_D3ViewerClosed();
            base.OnClosing(e);
        }
    }
}