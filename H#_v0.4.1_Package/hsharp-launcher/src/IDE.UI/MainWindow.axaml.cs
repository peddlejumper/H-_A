using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Primitives;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Markup.Xaml;
using Avalonia.Media;
using Avalonia.Threading;

namespace IDE.UI
{
    public partial class MainWindow : Window
    {
        #region ── Tab Data ──────────────────────────────────────────────────────
        private class OpenTabInfo
        {
            public string FilePath { get; set; } = "";
            public string DisplayName => string.IsNullOrEmpty(FilePath) ? "Untitled" : Path.GetFileName(FilePath);
            public string SavedText { get; set; } = "";
            public bool IsDirty
            {
                get
                {
                    var ctrl = _owner?.GetEditorControlForTab(this);
                    return ctrl != null && _owner!.GetEditorText(ctrl) != SavedText;
                }
            }
            public Border? TabButton { get; set; }
            private MainWindow? _owner;
            public void SetOwner(MainWindow owner) => _owner = owner;
        }

        private readonly List<OpenTabInfo> _openTabs = new();
        private int _activeTabIndex = -1;
        private OpenTabInfo? ActiveTab => _activeTabIndex >= 0 && _activeTabIndex < _openTabs.Count ? _openTabs[_activeTabIndex] : null;

        private string? _openFolderPath;

        // editor per tab
        private readonly Dictionary<string, Control> _tabEditors = new();
        #endregion

        #region ── File Tree Data ─────────────────────────────────────────────────
        private class FileTreeNode
        {
            public string Name { get; set; } = "";
            public string FullPath { get; set; } = "";
            public bool IsDirectory { get; set; }
            public List<FileTreeNode> Children { get; set; } = new();
        }
        #endregion

        #region ── Completion Data ────────────────────────────────────────────────
        public class CompletionItem
        {
            public string Label { get; set; } = "";
            public string Kind { get; set; } = "";
            public string Detail { get; set; } = "";
            public string InsertText { get; set; } = "";
        }

        private static readonly List<CompletionItem> _allCompletions = new()
        {
            // Keywords
            new() { Label = "fn",     Kind = "kw", Detail = "函数定义", InsertText = "fn ${1:name}(${2:params}) {\n    ${0}\n}" },
            new() { Label = "let",    Kind = "kw", Detail = "变量声明", InsertText = "let ${1:name} = ${0}" },
            new() { Label = "while",  Kind = "kw", Detail = "while循环", InsertText = "while (${1:cond}) {\n    ${0}\n}" },
            new() { Label = "if",     Kind = "kw", Detail = "条件判断", InsertText = "if (${1:cond}) {\n    ${0}\n}" },
            new() { Label = "for",    Kind = "kw", Detail = "for循环", InsertText = "for ${1:i} ${2:s} ${3:e} ${4:step} {\n    ${0}\n}" },
            new() { Label = "return", Kind = "kw", Detail = "返回值", InsertText = "return ${0}" },
            new() { Label = "print",  Kind = "kw", Detail = "打印输出", InsertText = "print(${0})" },
            new() { Label = "import", Kind = "kw", Detail = "模块导入", InsertText = "import \"${1:path}\";" },
            new() { Label = "class",  Kind = "kw", Detail = "类定义", InsertText = "class ${1:Name} {\n    ${0}\n}" },
            new() { Label = "true",   Kind = "kw", Detail = "布尔真值", InsertText = "true" },
            new() { Label = "false",  Kind = "kw", Detail = "布尔假值", InsertText = "false" },
            new() { Label = "null",   Kind = "kw", Detail = "空值", InsertText = "null" },
            new() { Label = "auto",   Kind = "kw", Detail = "自动类型", InsertText = "auto" },
            new() { Label = "try",    Kind = "kw", Detail = "异常捕获", InsertText = "try {\n    ${0}\n} catch (e) {\n\n}" },
            new() { Label = "throw",  Kind = "kw", Detail = "抛出异常", InsertText = "throw ${0}" },
            new() { Label = "break",  Kind = "kw", Detail = "跳出循环", InsertText = "break" },
            new() { Label = "continue",  Kind = "kw", Detail = "继续循环", InsertText = "continue" },
            new() { Label = "public", Kind = "kw", Detail = "公开属性", InsertText = "public " },

            // D3 System Keywords
            new() { Label = "3dsizepower", Kind = "d3", Detail = "三维坐标系", InsertText = "3dsizepower ${1:Name} {\n    ${0}\n}" },
            new() { Label = "em3d",    Kind = "d3", Detail = "扩展三维系统", InsertText = "em3d ${1:Name} extends ${2:Parent} {\n    ${0}\n}" },
            new() { Label = "region",  Kind = "d3", Detail = "区域定义", InsertText = "region ${1:Name}(${2:x},${3:y},${4:z},${5:x2},${6:y2},${7:z2}) {\n    ${0}\n}" },
            new() { Label = "region_interface", Kind = "d3", Detail = "区域接口", InsertText = "region_interface ${1:Name} {\n    ${0}\n}" },

            // D3 Operations
            new() { Label = "d3_find_region_by_point", Kind = "fn", Detail = "d3obj,x,y,z → region", InsertText = "d3_find_region_by_point(${1:d3Obj}, ${2:x}, ${3:y}, ${4:z})" },
            new() { Label = "d3_find_region_by_name",  Kind = "fn", Detail = "d3obj,name → region", InsertText = "d3_find_region_by_name(${1:d3Obj}, \"${2:name}\")" },
            new() { Label = "d3_get_regions_intersecting", Kind = "fn", Detail = "∩查询", InsertText = "d3_get_regions_intersecting(${1:d3Obj}, ${2:minX},${3:minY},${4:minZ},${5:maxX},${6:maxY},${7:maxZ})" },
            new() { Label = "d3_point_in_range", Kind = "fn", Detail = "点包含检测", InsertText = "d3_point_in_range(${1:pt}, ${2:minX},${3:minY},${4:minZ},${5:maxX},${6:maxY},${7:maxZ})" },
            new() { Label = "d3_system_summary", Kind = "fn", Detail = "系统摘要", InsertText = "d3_system_summary(${1:d3Obj})" },
            new() { Label = "d3_bbox_intersects", Kind = "fn", Detail = "包围盒相交检测", InsertText = "d3_bbox_intersects(${1:bboxA}, ${2:bboxB})" },
            new() { Label = "d3_size_power_get_info", Kind = "fn", Detail = "系统信息", InsertText = "d3_size_power_get_info(${1:d3Obj})" },
            new() { Label = "d3_export_region_data", Kind = "fn", Detail = "导出区域数据", InsertText = "d3_export_region_data(${1:d3Obj}, \"${2:regionName}\")" },

            // D3 Ops Library
            new() { Label = "d3_property_get", Kind = "fn", Detail = "获取属性", InsertText = "d3_property_get(${1:d3Obj}, \"${2:name}\")" },
            new() { Label = "d3_property_set", Kind = "fn", Detail = "设置属性", InsertText = "d3_property_set(${1:d3Obj}, \"${2:name}\", ${3:params})" },
            new() { Label = "d3_property_has", Kind = "fn", Detail = "属性是否存在", InsertText = "d3_property_has(${1:d3Obj}, \"${2:name}\")" },
            new() { Label = "d3_property_count", Kind = "fn", Detail = "属性计数", InsertText = "d3_property_count(${1:d3Obj})" },
            new() { Label = "d3_figure_get_name", Kind = "fn", Detail = "系统名称", InsertText = "d3_figure_get_name(${1:d3Obj})" },
            new() { Label = "d3_figure_get_bounds", Kind = "fn", Detail = "包围盒", InsertText = "d3_figure_get_bounds(${1:d3Obj})" },
            new() { Label = "d3_figure_get_center", Kind = "fn", Detail = "系统中心", InsertText = "d3_figure_get_center(${1:d3Obj})" },
            new() { Label = "d3_figure_get_region_count", Kind = "fn", Detail = "区域数量", InsertText = "d3_figure_get_region_count(${1:d3Obj})" },
            new() { Label = "d3_region_get_name", Kind = "fn", Detail = "区域名称", InsertText = "d3_region_get_name(${1:region})" },
            new() { Label = "d3_region_get_coords", Kind = "fn", Detail = "区域坐标", InsertText = "d3_region_get_coords(${1:region})" },
            new() { Label = "d3_region_get_volume", Kind = "fn", Detail = "区域体积", InsertText = "d3_region_get_volume(${1:region})" },
            new() { Label = "d3_region_get_center", Kind = "fn", Detail = "区域中心", InsertText = "d3_region_get_center(${1:region})" },
            new() { Label = "d3_region_get_dimensions", Kind = "fn", Detail = "区域尺寸(W,H,D)", InsertText = "d3_region_get_dimensions(${1:region})" },
            new() { Label = "d3_region_get_surface_area", Kind = "fn", Detail = "表面积", InsertText = "d3_region_get_surface_area(${1:region})" },
            new() { Label = "d3_region_contains_point", Kind = "fn", Detail = "是否包含点", InsertText = "d3_region_contains_point(${1:region}, ${2:x}, ${3:y}, ${4:z})" },
            new() { Label = "d3_region_overlaps", Kind = "fn", Detail = "区域重叠检测", InsertText = "d3_region_overlaps(${1:regionA}, ${2:regionB})" },
            new() { Label = "d3_region_container_add", Kind = "fn", Detail = "添加区域", InsertText = "d3_region_container_add(${1:d3Obj}, ${2:region})" },
            new() { Label = "d3_region_container_remove", Kind = "fn", Detail = "移除区域", InsertText = "d3_region_container_remove(${1:d3Obj}, \"${2:name}\")" },
            new() { Label = "d3_region_container_clone", Kind = "fn", Detail = "克隆区域", InsertText = "d3_region_container_clone(${1:d3Obj}, \"${2:name}\", \"${3:newName}\")" },
            new() { Label = "d3_region_container_move", Kind = "fn", Detail = "移动区域", InsertText = "d3_region_container_move(${1:d3Obj}, \"${2:name}\", ${3:dx}, ${4:dy}, ${5:dz})" },
            new() { Label = "d3_region_container_resize", Kind = "fn", Detail = "调整大小", InsertText = "d3_region_container_resize(${1:d3Obj}, \"${2:name}\", ${3:w}, ${4:h}, ${5:d})" },
            new() { Label = "d3_region_container_sort_by_volume", Kind = "fn", Detail = "按体积排序", InsertText = "d3_region_container_sort_by_volume(${1:d3Obj})" },
            new() { Label = "d3_region_container_sort_by_name", Kind = "fn", Detail = "按名称排序", InsertText = "d3_region_container_sort_by_name(${1:d3Obj})" },
            new() { Label = "d3_region_container_get_largest", Kind = "fn", Detail = "最大区域", InsertText = "d3_region_container_get_largest(${1:d3Obj})" },
            new() { Label = "d3_region_container_get_smallest", Kind = "fn", Detail = "最小区域", InsertText = "d3_region_container_get_smallest(${1:d3Obj})" },
            new() { Label = "d3_region_container_get_names", Kind = "fn", Detail = "区域名称列表", InsertText = "d3_region_container_get_names(${1:d3Obj})" },
            new() { Label = "d3_region_container_count", Kind = "fn", Detail = "区域计数", InsertText = "d3_region_container_count(${1:d3Obj})" },
            new() { Label = "d3_class_has", Kind = "fn", Detail = "类是否存在", InsertText = "d3_class_has(${1:d3Obj}, \"${2:region}\", \"${3:class}\")" },
            new() { Label = "d3_class_get", Kind = "fn", Detail = "获取类", InsertText = "d3_class_get(${1:d3Obj}, \"${2:region}\", \"${3:class}\")" },
            new() { Label = "d3_class_count", Kind = "fn", Detail = "区域中类计数", InsertText = "d3_class_count(${1:d3Obj}, \"${2:region}\")" },
            new() { Label = "d3_class_list_all", Kind = "fn", Detail = "所有类列表", InsertText = "d3_class_list_all(${1:d3Obj})" },
            new() { Label = "d3_data_serialize_system", Kind = "fn", Detail = "序列化系统", InsertText = "d3_data_serialize_system(${1:d3Obj})" },
            new() { Label = "d3_data_system_snapshot", Kind = "fn", Detail = "系统快照", InsertText = "d3_data_system_snapshot(${1:d3Obj})" },
            new() { Label = "d3_data_diff_regions", Kind = "fn", Detail = "区域差异比较", InsertText = "d3_data_diff_regions(${1:d3ObjA}, ${2:d3ObjB})" },
            new() { Label = "d3_data_pack_region", Kind = "fn", Detail = "打包区域", InsertText = "d3_data_pack_region(${1:region})" },
            new() { Label = "d3_system_init", Kind = "fn", Detail = "初始化系统元数据", InsertText = "d3_system_init(${1:d3Obj}, [], [])" },
            new() { Label = "d3_class_register_names", Kind = "fn", Detail = "注册类名", InsertText = "d3_class_register_names(${1:d3Obj}, \"${2:region}\", [\"${3:class}\"])" },

            // Builtins
            new() { Label = "len",  Kind = "fn", Detail = "长度/元素数", InsertText = "len(${1})" },
            new() { Label = "push", Kind = "fn", Detail = "追加元素到数组", InsertText = "push(${1:array}, ${2:value})" },
            new() { Label = "pop",  Kind = "fn", Detail = "数组出栈", InsertText = "pop(${1:array})" },

            // Snippets
            new() { Label = "// comment",  Kind = "snip", Detail = "单行注释", InsertText = "// ${0}" },
            new() { Label = "/* block */", Kind = "snip", Detail = "多行注释", InsertText = "/*\n ${0}\n*/" },
        };

        private List<CompletionItem> _filteredCompletions = new();
        private int _selectedCompletionIndex = -1;
        #endregion

        #region ── Existing State ─────────────────────────────────────────────────
        private string currentFile => ActiveTab?.FilePath ?? string.Empty;
        private Process? currentProcess;

        private string _lastEditorText = string.Empty;
        private DispatcherTimer? _editorPollTimer;

        private readonly HashSet<string> _keywords = new(StringComparer.Ordinal)
        {
            "let","fn","while","if","for","print","return","import","true","false","null",
            "class","try","catch","throw","break","continue","auto","public",
            "3dsizepower","em3d","region","region_interface"
        };

        // splitter drag
        private bool _splitterDragging;
        private double _splitterStartX;
        private double _splitterStartWidth;
        #endregion

        public MainWindow()
        {
            InitializeComponent();

            TryLoadAvaloniaEdit();
            StartEditorPolling();
            this.KeyDown += OnWindowKeyDown;
        }

        private void InitializeComponent() => AvaloniaXamlLoader.Load(this);

        #region ── Editor Helpers ─────────────────────────────────────────────────
        private Control? GetEditorControlForTab(OpenTabInfo tab)
        {
            if (_tabEditors.TryGetValue(tab.FilePath, out var ctrl))
                return ctrl;
            return null;
        }

        private Control? GetActiveEditorControl()
        {
            var tab = ActiveTab;
            if (tab != null)
                return GetEditorControlForTab(tab);
            var host = this.FindControl<ContentControl>("TabEditorHost");
            var fb = this.FindControl<TextBox>("Editor");
            return host?.Content as Control ?? fb;
        }

        private string GetEditorText(Control? editor)
        {
            if (editor == null) return string.Empty;
            var textProp = editor.GetType().GetProperty("Text");
            if (textProp != null)
                return textProp.GetValue(editor) as string ?? string.Empty;
            var docProp = editor.GetType().GetProperty("Document");
            if (docProp != null)
            {
                var doc = docProp.GetValue(editor);
                if (doc != null)
                {
                    var txtProp = doc.GetType().GetProperty("Text");
                    if (txtProp != null)
                        return txtProp.GetValue(doc) as string ?? string.Empty;
                }
            }
            return string.Empty;
        }

        private void SetEditorText(Control? editor, string text)
        {
            if (editor == null) return;
            var textProp = editor.GetType().GetProperty("Text");
            if (textProp != null && textProp.CanWrite)
            {
                textProp.SetValue(editor, text);
                return;
            }
            var docProp = editor.GetType().GetProperty("Document");
            if (docProp != null)
            {
                var doc = docProp.GetValue(editor);
                if (doc != null)
                {
                    var txtProp = doc.GetType().GetProperty("Text");
                    if (txtProp != null && txtProp.CanWrite)
                        txtProp.SetValue(doc, text);
                }
            }
        }

        private Control CreateNewEditor()
        {
            try
            {
                var editorType = Type.GetType("AvaloniaEdit.TextEditor, AvaloniaEdit");
                if (editorType != null)
                {
                    var editorObj = Activator.CreateInstance(editorType) as Control;
                    if (editorObj != null)
                    {
                        var showLn = editorType.GetProperty("ShowLineNumbers");
                        if (showLn != null && showLn.CanWrite) showLn.SetValue(editorObj, true);
                        var ff = editorType.GetProperty("FontFamily");
                        if (ff != null && ff.CanWrite) ff.SetValue(editorObj, new FontFamily("Consolas, 'Courier New', monospace"));
                        var fs = editorType.GetProperty("FontSize");
                        if (fs != null && fs.CanWrite) fs.SetValue(editorObj, 14.0);
                        return editorObj;
                    }
                }
            }
            catch { }
            return new TextBox
            {
                AcceptsReturn = true,
                AcceptsTab = false,
                FontFamily = new FontFamily("Consolas, 'Courier New', monospace"),
                FontSize = 14,
                TextWrapping = TextWrapping.NoWrap
            };
        }
        #endregion

        #region ── Tab System ─────────────────────────────────────────────────────
        private void OpenFileInTab(string filePath)
        {
            // check if already open
            var existing = _openTabs.FirstOrDefault(t => t.FilePath == filePath);
            if (existing != null)
            {
                SwitchToTab(_openTabs.IndexOf(existing));
                return;
            }

            var text = File.Exists(filePath) ? File.ReadAllText(filePath) : "";
            var tab = new OpenTabInfo { FilePath = filePath, SavedText = text };
            tab.SetOwner(this);
            var editor = CreateNewEditor();
            SetEditorText(editor, text);

            // hook editor events
            var textBox = editor as TextBox;
            if (textBox != null)
            {
                textBox.KeyDown += OnEditorKeyDown;
                textBox.TextChanged += OnEditorTextChanged;
            }

            _tabEditors[filePath] = editor;
            _openTabs.Add(tab);
            SwitchToTab(_openTabs.Count - 1);
            _lastEditorText = text;
            UpdateHighlightPreview();
            AppendOutput($"已打开: {filePath}");
        }

        private void SwitchToTab(int index)
        {
            if (index < 0 || index >= _openTabs.Count) return;
            _activeTabIndex = index;
            var tab = ActiveTab!;
            var editor = GetEditorControlForTab(tab);
            if (editor == null)
            {
                editor = CreateNewEditor();
                SetEditorText(editor, tab.SavedText);
                var textBox = editor as TextBox;
                if (textBox != null)
                {
                    textBox.KeyDown += OnEditorKeyDown;
                    textBox.TextChanged += OnEditorTextChanged;
                }
                _tabEditors[tab.FilePath] = editor;
            }

            var host = this.FindControl<ContentControl>("TabEditorHost");
            if (host != null) host.Content = editor;

            _lastEditorText = GetEditorText(editor);
            RefreshTabStrip();
            UpdateHighlightPreview();
            Title = $"H# IDE - {tab.DisplayName}" + (tab.IsDirty ? " *" : "");
        }

        private void CloseTab(int index, bool force = false)
        {
            if (index < 0 || index >= _openTabs.Count) return;
            var tab = _openTabs[index];
            if (!force && tab.IsDirty)
            {
                AppendOutput($"文件 '{tab.DisplayName}' 有未保存的更改。请先保存。");
                return;
            }
            _openTabs.RemoveAt(index);
            _tabEditors.Remove(tab.FilePath);
            if (_activeTabIndex >= _openTabs.Count)
                _activeTabIndex = _openTabs.Count - 1;
            else if (_activeTabIndex > index)
                _activeTabIndex--;
            if (_activeTabIndex < 0)
            {
                var host = this.FindControl<ContentControl>("TabEditorHost");
                if (host != null) host.Content = this.FindControl<TextBox>("Editor");
                Title = "H# IDE";
            }
            if (_activeTabIndex >= 0)
                SwitchToTab(_activeTabIndex);
            RefreshTabStrip();
        }

        private void RefreshTabStrip()
        {
            var strip = this.FindControl<StackPanel>("TabStrip");
            if (strip == null) return;
            strip.Children.Clear();
            for (int i = 0; i < _openTabs.Count; i++)
            {
                int idx = i;
                var tab = _openTabs[i];
                var isActive = (i == _activeTabIndex);

                var btn = new Border
                {
                    Background = isActive ? new SolidColorBrush(Color.Parse("#2a2a4a")) : new SolidColorBrush(Color.Parse("#1a1a2a")),
                    BorderBrush = new SolidColorBrush(Color.Parse("#3a3a5a")),
                    BorderThickness = new Thickness(0.5),
                    CornerRadius = new CornerRadius(4, 4, 0, 0),
                    Padding = new Thickness(8, 4),
                    Cursor = new Cursor(StandardCursorType.Hand),
                    Tag = idx
                };
                var sp = new StackPanel { Orientation = Avalonia.Layout.Orientation.Horizontal, Spacing = 6 };
                var fnBlock = new TextBlock
                {
                    Text = tab.DisplayName + (tab.IsDirty ? " ●" : ""),
                    FontSize = 12,
                    Foreground = isActive ? Brushes.White : new SolidColorBrush(Color.Parse("#aaaacc"))
                };
                var closeBtn = new Button
                {
                    Content = "×",
                    Width = 16, Height = 16,
                    FontSize = 11,
                    Background = Brushes.Transparent,
                    Foreground = new SolidColorBrush(Color.Parse("#666688")),
                    Padding = new Thickness(0),
                    Tag = idx
                };
                closeBtn.Click += (s, e) =>
                {
                    if (s is Button b && b.Tag is int ti) CloseTab(ti);
                };
                btn.PointerPressed += (s, e) =>
                {
                    if (s is Border bd && bd.Tag is int ti) SwitchToTab(ti);
                };
                sp.Children.Add(fnBlock);
                sp.Children.Add(closeBtn);
                btn.Child = sp;
                strip.Children.Add(btn);
            }
        }

        private async void NewFile(object? sender, RoutedEventArgs e)
        {
            var tab = new OpenTabInfo { FilePath = "", SavedText = "" };
            tab.SetOwner(this);
            var editor = CreateNewEditor();
            SetEditorText(editor, "");
            var textBox = editor as TextBox;
            if (textBox != null)
            {
                textBox.KeyDown += OnEditorKeyDown;
                textBox.TextChanged += OnEditorTextChanged;
            }
            _tabEditors[""] = editor;
            _openTabs.Add(tab);
            SwitchToTab(_openTabs.Count - 1);
            AppendOutput("新建未命名文件");
        }

        private void CloseCurrentTab(object? sender, RoutedEventArgs e)
        {
            if (_activeTabIndex >= 0) CloseTab(_activeTabIndex);
        }
        #endregion

        #region ── File System (TreeView) ─────────────────────────────────────────
        private async void OpenFolder(object? sender, RoutedEventArgs e)
        {
            var dlg = new OpenFolderDialog { Title = "打开项目文件夹" };
            var result = await dlg.ShowAsync(this);
            if (!string.IsNullOrEmpty(result))
            {
                _openFolderPath = result;
                PopulateFileTree(_openFolderPath);
                AppendOutput($"已打开文件夹: {_openFolderPath}");
            }
        }

        private void RefreshFileTree(object? sender, RoutedEventArgs e)
        {
            if (!string.IsNullOrEmpty(_openFolderPath))
                PopulateFileTree(_openFolderPath);
            else
                AppendOutput("请先打开一个文件夹 (File > Open Folder...)");
        }

        private void PopulateFileTree(string rootPath)
        {
            var tree = this.FindControl<TreeView>("FileTree");
            if (tree == null) return;
            tree.Items.Clear();
            if (!Directory.Exists(rootPath)) return;

            var root = BuildFileTreeNode(rootPath, true);
            var rootItem = CreateTreeViewItem(root);
            rootItem.IsExpanded = true;
            tree.Items.Add(rootItem);
        }

        private FileTreeNode BuildFileTreeNode(string path, bool isRoot = false)
        {
            var node = new FileTreeNode
            {
                Name = isRoot ? Path.GetFileName(path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)) : Path.GetFileName(path),
                FullPath = path,
                IsDirectory = Directory.Exists(path)
            };
            if (node.IsDirectory)
            {
                try
                {
                    foreach (var dir in Directory.GetDirectories(path).OrderBy(d => d))
                        node.Children.Add(BuildFileTreeNode(dir));
                    foreach (var file in Directory.GetFiles(path).OrderBy(f => f))
                    {
                        var ext = Path.GetExtension(file).ToLowerInvariant();
                        if (ext is ".hto" or ".hbc" or ".py" or ".json" or ".txt" or ".md" or ".cs")
                            node.Children.Add(BuildFileTreeNode(file));
                    }
                }
                catch { }
            }
            return node;
        }

        private TreeViewItem CreateTreeViewItem(FileTreeNode node)
        {
            var sp = new StackPanel { Orientation = Avalonia.Layout.Orientation.Horizontal, Spacing = 4 };
            sp.Children.Add(new TextBlock
            {
                Text = node.IsDirectory ? "📁" : (Path.GetExtension(node.Name) == ".hto" ? "📄" : "📋"),
                FontSize = 12
            });
            sp.Children.Add(new TextBlock
            {
                Text = node.Name,
                FontSize = 12,
                Foreground = node.IsDirectory ? new SolidColorBrush(Color.Parse("#ccddff")) : new SolidColorBrush(Color.Parse("#cccccc"))
            });

            var item = new TreeViewItem
            {
                Header = sp,
                Tag = node.FullPath,
                IsExpanded = node.IsDirectory && node.Name != "bin" && node.Name != "obj" && node.Name != ".git"
            };

            foreach (var child in node.Children)
                item.Items.Add(CreateTreeViewItem(child));

            return item;
        }

        private void OnFileTreeSelectionChanged(object? sender, SelectionChangedEventArgs e)
        {
            if (e.AddedItems.Count == 0) return;
            var item = e.AddedItems[0] as TreeViewItem;
            if (item?.Tag is string path && File.Exists(path))
            {
                var ext = Path.GetExtension(path).ToLowerInvariant();
                if (ext == ".hto" || ext == ".txt" || ext == ".md" || ext == ".json")
                {
                    OpenFileInTab(path);
                }
            }
        }

        private async void NewFolder(object? sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_openFolderPath))
            {
                AppendOutput("请先打开一个文件夹。");
                return;
            }
            // simple input for folder name
            var name = $"new_folder_{DateTime.Now:yyyyMMdd_HHmmss}";
            try
            {
                var newPath = Path.Combine(_openFolderPath, name);
                if (Directory.Exists(newPath))
                {
                    AppendOutput($"文件夹已存在: {name}");
                    return;
                }
                Directory.CreateDirectory(newPath);
                PopulateFileTree(_openFolderPath);
                AppendOutput($"已创建文件夹: {name}");
            }
            catch (Exception ex) { AppendOutput($"创建文件夹失败: {ex.Message}"); }
        }

        private async void NewFileInTree(object? sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_openFolderPath))
            {
                AppendOutput("请先打开一个文件夹。");
                return;
            }
            try
            {
                var name = $"new_{DateTime.Now:yyyyMMdd_HHmmss}.hto";
                var newPath = Path.Combine(_openFolderPath, name);
                int counter = 1;
                while (File.Exists(newPath))
                {
                    name = $"new_{DateTime.Now:yyyyMMdd_HHmmss}_{counter}.hto";
                    newPath = Path.Combine(_openFolderPath, name);
                    counter++;
                }
                File.WriteAllText(newPath, "// New H# file\n");
                PopulateFileTree(_openFolderPath);
                OpenFileInTab(newPath);
                AppendOutput($"已创建文件: {name}");
            }
            catch (Exception ex) { AppendOutput($"创建文件失败: {ex.Message}"); }
        }

        private ColumnDefinition? GetFileTreeColumnDef()
        {
            var grid = this.FindControl<Grid>("MainGrid");
            if (grid != null && grid.ColumnDefinitions.Count > 0)
                return grid.ColumnDefinitions[0];
            return null;
        }

        private void OnFileTreeSplitterDrag(object? sender, PointerPressedEventArgs e)
        {
            _splitterDragging = true;
            _splitterStartX = e.GetPosition(this).X;
            var col = GetFileTreeColumnDef();
            if (col != null) _splitterStartWidth = col.Width.Value;

            var border = sender as Border;
            if (border != null)
            {
                border.PointerMoved += OnSplitterMoved;
                border.PointerReleased += OnSplitterReleased;
            }
        }

        private void OnSplitterMoved(object? sender, PointerEventArgs e)
        {
            if (!_splitterDragging) return;
            var dx = e.GetPosition(this).X - _splitterStartX;
            var col = GetFileTreeColumnDef();
            if (col != null)
            {
                var newWidth = Math.Clamp(_splitterStartWidth + dx, 100, 500);
                col.Width = new GridLength(newWidth);
            }
        }

        private void OnSplitterReleased(object? sender, PointerReleasedEventArgs e)
        {
            _splitterDragging = false;
            var border = sender as Border;
            if (border != null)
            {
                border.PointerMoved -= OnSplitterMoved;
                border.PointerReleased -= OnSplitterReleased;
            }
        }
        #endregion

        #region ── Code Completion ────────────────────────────────────────────────
        private void ShowCompletion(string triggerText)
        {
            _filteredCompletions = _allCompletions
                .Where(c => c.Label.StartsWith(triggerText, StringComparison.OrdinalIgnoreCase))
                .Take(20)
                .ToList();
            if (_filteredCompletions.Count == 0)
            {
                HideCompletion();
                return;
            }

            var popup = this.FindControl<Border>("CompletionPopup");
            var list = this.FindControl<ListBox>("CompletionList");
            if (popup == null || list == null) return;

            list.ItemsSource = _filteredCompletions;
            list.SelectedIndex = 0;
            _selectedCompletionIndex = 0;

            // position near cursor
            var editor = GetActiveEditorControl();
            if (editor != null)
            {
                var text = GetEditorText(editor);
                int cursorPos = GetCursorPosition(editor);
                int lineStart = text.LastIndexOf('\n', Math.Max(cursorPos - 1, 0));
                if (lineStart < 0) lineStart = 0;
                else lineStart++;
                var lineText = text.Substring(lineStart, Math.Min(cursorPos - lineStart, text.Length - lineStart));

                double charWidth = 8.4;
                double lineHeight = 20;
                int lineCount = text.Substring(0, cursorPos).Count(c => c == '\n');
                popup.Margin = new Thickness(lineText.Length * charWidth + 20, (lineCount + 1) * lineHeight + 35, 0, 0);
            }

            popup.IsVisible = true;
        }

        private void HideCompletion()
        {
            var popup = this.FindControl<Border>("CompletionPopup");
            if (popup != null) popup.IsVisible = false;
            _filteredCompletions.Clear();
            _selectedCompletionIndex = -1;
        }

        private void AcceptCompletion()
        {
            if (_selectedCompletionIndex < 0 || _selectedCompletionIndex >= _filteredCompletions.Count) return;
            var item = _filteredCompletions[_selectedCompletionIndex];
            var editor = GetActiveEditorControl();
            if (editor == null) return;

            var text = GetEditorText(editor);
            int cursorPos = GetCursorPosition(editor);

            // find the word being typed
            int wordStart = cursorPos;
            while (wordStart > 0 && IsIdentifierChar(text[wordStart - 1]))
                wordStart--;
            string currentWord = text.Substring(wordStart, cursorPos - wordStart);

            string insertText = item.InsertText;
            // remove snippet markers ${N:text} -> just text for simplicity
            insertText = Regex.Replace(insertText, @"\$\{\d+(?::([^}]*))?\}", m => m.Groups[1].Success ? m.Groups[1].Value : "");
            insertText = Regex.Replace(insertText, @"\$\{0\}", "");

            string before = text.Substring(0, wordStart);
            string after = text.Substring(cursorPos);
            string newText = before + insertText + after;
            SetEditorText(editor, newText);

            // set cursor after inserted text
            int newPos = wordStart + insertText.Length;
            SetCursorPosition(editor, newPos);

            HideCompletion();
        }

        private int GetCursorPosition(Control? editor)
        {
            if (editor == null) return 0;
            var caretProp = editor.GetType().GetProperty("CaretIndex");
            if (caretProp != null)
                return (int)(caretProp.GetValue(editor) ?? 0);
            var caretOffsetProp = editor.GetType().GetProperty("CaretOffset");
            if (caretOffsetProp != null)
                return (int)(caretOffsetProp.GetValue(editor) ?? 0);
            // TextBox fallback
            var tb = editor as TextBox;
            if (tb != null) return tb.CaretIndex;
            return 0;
        }

        private void SetCursorPosition(Control? editor, int pos)
        {
            if (editor == null) return;
            var caretProp = editor.GetType().GetProperty("CaretIndex");
            if (caretProp != null && caretProp.CanWrite) { caretProp.SetValue(editor, pos); return; }
            var caretOffsetProp = editor.GetType().GetProperty("CaretOffset");
            if (caretOffsetProp != null && caretOffsetProp.CanWrite) { caretOffsetProp.SetValue(editor, pos); return; }
            var tb = editor as TextBox;
            if (tb != null) tb.CaretIndex = pos;
        }

        private bool IsIdentifierChar(char c)
            => char.IsLetterOrDigit(c) || c == '_';

        private void NavigateCompletion(int dir)
        {
            if (_filteredCompletions.Count == 0) return;
            _selectedCompletionIndex = (_selectedCompletionIndex + dir + _filteredCompletions.Count) % _filteredCompletions.Count;
            var list = this.FindControl<ListBox>("CompletionList");
            if (list != null) list.SelectedIndex = _selectedCompletionIndex;
        }

        private void OnCompletionSelectionChanged(object? sender, SelectionChangedEventArgs e)
        {
            if (e.AddedItems.Count > 0 && sender is ListBox lb)
                _selectedCompletionIndex = lb.SelectedIndex;
        }
        #endregion

        #region ── Editor Events ──────────────────────────────────────────────────
        private void OnEditorKeyDown(object? sender, KeyEventArgs e)
        {
            var popup = this.FindControl<Border>("CompletionPopup");

            // Completion popup keys
            if (popup != null && popup.IsVisible)
            {
                if (e.Key == Key.Enter || e.Key == Key.Tab)
                {
                    e.Handled = true;
                    AcceptCompletion();
                    return;
                }
                if (e.Key == Key.Escape)
                {
                    e.Handled = true;
                    HideCompletion();
                    return;
                }
                if (e.Key == Key.Down)
                {
                    e.Handled = true;
                    NavigateCompletion(1);
                    return;
                }
                if (e.Key == Key.Up)
                {
                    e.Handled = true;
                    NavigateCompletion(-1);
                    return;
                }
            }

            // Ctrl+S – save
            if (e.Key == Key.S && e.KeyModifiers == KeyModifiers.Control)
            {
                e.Handled = true;
                SaveFile(null, null!);
                return;
            }
            // Ctrl+W – close tab
            if (e.Key == Key.W && e.KeyModifiers == KeyModifiers.Control)
            {
                e.Handled = true;
                if (_activeTabIndex >= 0) CloseTab(_activeTabIndex);
                return;
            }

            // Tab for indent
            if (e.Key == Key.Tab)
            {
                // handled by completion popup above
            }
        }

        private void OnWindowKeyDown(object? sender, KeyEventArgs e)
        {
            // Ctrl+Space – force completion
            if (e.Key == Key.Space && e.KeyModifiers == KeyModifiers.Control)
            {
                e.Handled = true;
                var editor = GetActiveEditorControl();
                if (editor != null)
                {
                    var text = GetEditorText(editor);
                    int cursorPos = GetCursorPosition(editor);
                    int wordStart = cursorPos;
                    while (wordStart > 0 && IsIdentifierChar(text[wordStart - 1]))
                        wordStart--;
                    string word = wordStart < cursorPos ? text.Substring(wordStart, cursorPos - wordStart) : "";
                    ShowCompletion(string.IsNullOrEmpty(word) ? "" : word);
                }
            }

            // Ctrl+Tab – switch tab
            if (e.Key == Key.Tab && e.KeyModifiers == KeyModifiers.Control)
            {
                e.Handled = true;
                if (_openTabs.Count > 1)
                {
                    int next = (_activeTabIndex + 1) % _openTabs.Count;
                    SwitchToTab(next);
                }
            }
        }

        private void OnEditorTextChanged(object? sender, TextChangedEventArgs e)
        {
            var editor = GetActiveEditorControl();
            var text = GetEditorText(editor);
            if (text == _lastEditorText) return;
            _lastEditorText = text;
            UpdateHighlightPreview();

            // Auto-complete trigger: show after typing 2+ identifier chars
            int cursorPos = GetCursorPosition(editor);
            if (cursorPos > 1 && cursorPos <= text.Length)
            {
                int wordStart = cursorPos;
                while (wordStart > 0 && IsIdentifierChar(text[wordStart - 1]))
                    wordStart--;
                string word = text.Substring(wordStart, cursorPos - wordStart);
                if (word.Length >= 2)
                {
                    var matches = _allCompletions.Where(c => c.Label.StartsWith(word, StringComparison.OrdinalIgnoreCase)).ToList();
                    if (matches.Count > 0 && matches.Count < 30)
                        ShowCompletion(word);
                    else
                        HideCompletion();
                }
                else
                {
                    HideCompletion();
                }
            }
            else
            {
                HideCompletion();
            }

            // Update tab dirty marker
            RefreshTabStrip();
        }
        #endregion

        #region ── File Open/Save ─────────────────────────────────────────────────
        private async void OpenFile(object? sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                AllowMultiple = false,
                Filters = new List<FileDialogFilter>
                {
                    new() { Name = "H# Source", Extensions = { "hto" } },
                    new() { Name = "All Files", Extensions = { "*" } }
                }
            };
            var res = await dlg.ShowAsync(this);
            if (res != null && res.Length > 0)
            {
                OpenFileInTab(res[0]);
                // auto-open parent folder
                var parentDir = Path.GetDirectoryName(res[0]);
                if (!string.IsNullOrEmpty(parentDir) && _openFolderPath != parentDir)
                {
                    _openFolderPath = parentDir;
                    PopulateFileTree(_openFolderPath);
                }
            }
        }

        private async void SaveFile(object? sender, RoutedEventArgs e)
        {
            var tab = ActiveTab;
            if (tab == null) { AppendOutput("没有打开的标签页。"); return; }
            string path = tab.FilePath;

            if (string.IsNullOrEmpty(path))
            {
                var sfd = new SaveFileDialog
                {
                    Filters = new List<FileDialogFilter>
                    {
                        new() { Name = "H# Source", Extensions = { "hto" } }
                    }
                };
                path = await sfd.ShowAsync(this);
                if (string.IsNullOrEmpty(path)) return;
                // rename the tab
                _tabEditors.Remove(tab.FilePath);
                tab.FilePath = path;
                _tabEditors[path] = GetActiveEditorControl()!;
            }

            var editor = GetEditorControlForTab(tab);
            var text = GetEditorText(editor);
            File.WriteAllText(path, text);
            tab.SavedText = text;
            RefreshTabStrip();
            UpdateHighlightPreview();
            AppendOutput($"已保存: {path}");
            if (_openFolderPath == null)
            {
                _openFolderPath = Path.GetDirectoryName(path);
                if (!string.IsNullOrEmpty(_openFolderPath)) PopulateFileTree(_openFolderPath);
            }
        }

        private async void SaveFileAs(object? sender, RoutedEventArgs e)
        {
            var tab = ActiveTab;
            if (tab == null) return;
            var sfd = new SaveFileDialog
            {
                Filters = new List<FileDialogFilter>
                {
                    new() { Name = "H# Source", Extensions = { "hto" } }
                }
            };
            var path = await sfd.ShowAsync(this);
            if (string.IsNullOrEmpty(path)) return;
            _tabEditors.Remove(tab.FilePath);
            tab.FilePath = path;
            _tabEditors[path] = GetActiveEditorControl()!;
            SaveFile(sender, e);
        }

        private void Exit(object? sender, RoutedEventArgs e) => Close();
        #endregion

        #region ── View Toggles ───────────────────────────────────────────────────
        private void ToggleFileTree(object? sender, RoutedEventArgs e)
        {
            var panel = this.FindControl<Border>("FileTreePanel");
            var col = GetFileTreeColumnDef();
            if (panel != null && col != null)
            {
                if (col.Width.Value > 0)
                {
                    _splitterStartWidth = col.Width.Value;
                    col.Width = new GridLength(0);
                    panel.IsVisible = false;
                }
                else
                {
                    col.Width = new GridLength(_splitterStartWidth > 0 ? _splitterStartWidth : 220);
                    panel.IsVisible = true;
                }
            }
        }

        private void TogglePreview(object? sender, RoutedEventArgs e)
        {
            var panel = this.FindControl<TabControl>("RightPanel");
            if (panel != null) panel.IsVisible = !panel.IsVisible;
        }

        private void ToggleOutput(object? sender, RoutedEventArgs e)
        {
            var box = this.FindControl<TextBox>("BottomOutput");
            if (box != null) box.IsVisible = !box.IsVisible;
        }
        #endregion

        #region ── Highlight Preview ──────────────────────────────────────────────
        private void UpdateHighlightPreview()
        {
            var preview = this.FindControl<TextBlock>("HighlightPreview");
            if (preview == null) return;
            var editorCtrl = GetActiveEditorControl();
            var text = GetEditorText(editorCtrl);

            Dispatcher.UIThread.Post(() =>
            {
                preview.Inlines.Clear();
                if (string.IsNullOrEmpty(text)) return;
                var pattern = @"//.*?$|/\*(?:.|\n)*?\*/|""(?:\\.|[^""])*""|'(?:\\.|[^'])*'|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b";
                var matches = Regex.Matches(text, pattern, RegexOptions.Singleline | RegexOptions.Multiline);
                int lastIndex = 0;
                foreach (Match m in matches)
                {
                    if (m.Index > lastIndex)
                    {
                        preview.Inlines.Add(new Avalonia.Controls.Documents.Run { Text = text.Substring(lastIndex, m.Index - lastIndex), Foreground = Brushes.White });
                    }
                    var token = m.Value;
                    var run = new Avalonia.Controls.Documents.Run { Text = token };
                    if (token.StartsWith("//") || token.StartsWith("/*"))
                        run.Foreground = Brushes.Green;
                    else if (token.StartsWith("\"") || token.StartsWith("'"))
                        run.Foreground = Brushes.Orange;
                    else if (Regex.IsMatch(token, "^\\d"))
                        run.Foreground = Brushes.Magenta;
                    else if (_keywords.Contains(token))
                        run.Foreground = Brushes.CornflowerBlue;
                    else
                        run.Foreground = Brushes.White;
                    preview.Inlines.Add(run);
                    lastIndex = m.Index + m.Length;
                }
                if (lastIndex < text.Length)
                    preview.Inlines.Add(new Avalonia.Controls.Documents.Run { Text = text.Substring(lastIndex), Foreground = Brushes.White });
            });
        }
        #endregion

        #region ── Editor Polling ─────────────────────────────────────────────────
        private void StartEditorPolling()
        {
            _editorPollTimer = new DispatcherTimer(TimeSpan.FromMilliseconds(300), DispatcherPriority.Background, (s, e) =>
            {
                var active = GetActiveEditorControl();
                var t = GetEditorText(active);
                if (t != _lastEditorText)
                {
                    _lastEditorText = t;
                    UpdateHighlightPreview();
                }
            });
            _editorPollTimer.Start();
        }
        #endregion

        #region ── Run/Build/REPL ─────────────────────────────────────────────────
        private string? FindHSharpPy()
        {
            try
            {
                var env = Environment.GetEnvironmentVariable("HSHARP_COMPILER");
                if (!string.IsNullOrEmpty(env) && File.Exists(env)) return Path.GetFullPath(env);
                var cfg = LauncherConfig.GetSelectedCompilerPath();
                if (!string.IsNullOrEmpty(cfg) && File.Exists(cfg)) return Path.GetFullPath(cfg);
            }
            catch { }
            var dir = Directory.GetCurrentDirectory();
            for (int i = 0; i < 12; i++)
            {
                var candidate = Path.Combine(dir, "hsharp.py");
                if (File.Exists(candidate)) return Path.GetFullPath(candidate);
                dir = Path.GetDirectoryName(dir) ?? string.Empty;
                if (string.IsNullOrEmpty(dir)) break;
            }
            return null;
        }

        private string? FindIDEtoolsDll()
        {
            var dir = Directory.GetCurrentDirectory();
            for (int i = 0; i < 8; i++)
            {
                var candidate = Path.Combine(dir, "src", "IDE.Tools", "bin", "Debug", "net7.0", "IDE.Tools.dll");
                if (File.Exists(candidate)) return Path.GetFullPath(candidate);
                candidate = Path.Combine(dir, "src", "IDE.Tools", "bin", "Release", "net7.0", "IDE.Tools.dll");
                if (File.Exists(candidate)) return Path.GetFullPath(candidate);
                dir = Path.GetDirectoryName(dir) ?? string.Empty;
                if (string.IsNullOrEmpty(dir)) break;
            }
            return null;
        }

        private async Task<int> RunExternal(string executable, string arguments)
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = executable,
                    Arguments = arguments,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                var p = Process.Start(psi) ?? throw new Exception("Failed to start process");
                currentProcess = p;
                _ = Task.Run(async () =>
                {
                    string? line;
                    while ((line = await p.StandardOutput.ReadLineAsync()) != null) AppendOutput(line);
                });
                _ = Task.Run(async () =>
                {
                    string? line;
                    while ((line = await p.StandardError.ReadLineAsync()) != null) AppendOutput(line);
                });
                await p.WaitForExitAsync();
                currentProcess = null;
                try { p.Dispose(); } catch { }
                return p.ExitCode;
            }
            catch (Exception ex) { AppendOutput("Error: " + ex.Message); return 1; }
        }

        private void OnStop(object? sender, RoutedEventArgs e)
        {
            try
            {
                if (currentProcess != null && !currentProcess.HasExited)
                {
                    currentProcess.Kill(true);
                    AppendOutput("Process terminated by user.");
                }
                else AppendOutput("No running process to stop.");
            }
            catch (Exception ex) { AppendOutput("Failed to stop: " + ex.Message); }
        }

        private void AppendOutput(string line)
        {
            Dispatcher.UIThread.Post(() =>
            {
                var outBox = this.FindControl<TextBox>("OutputBox");
                var bottom = this.FindControl<TextBox>("BottomOutput");
                if (outBox != null) outBox.Text += line + "\n";
                if (bottom != null) bottom.Text += line + "\n";
            });
        }

        private async void OnRun(object? sender, RoutedEventArgs e)
        {
            var editorCtrl = GetActiveEditorControl();
            var code = GetEditorText(editorCtrl);
            bool deleteTemp = false;
            string fileToRun = currentFile;
            if (string.IsNullOrEmpty(fileToRun))
            {
                var tmp = Path.Combine(Path.GetTempPath(), $"hsharp_unsaved_{Guid.NewGuid()}.hto");
                File.WriteAllText(tmp, code);
                fileToRun = tmp;
                deleteTemp = true;
            }
            else File.WriteAllText(fileToRun, code);

            AppendOutput($"Running {fileToRun}...");
            var dll = FindIDEtoolsDll();
            if (dll != null) await RunExternal("dotnet", Quote(dll) + " run -- run " + Quote(fileToRun));
            else
            {
                var python = Environment.GetEnvironmentVariable("HSHARP_PYTHON") ?? "python3";
                var hsharp = FindHSharpPy();
                if (hsharp == null) AppendOutput("hsharp.py not found.");
                else await RunExternal(python, Quote(hsharp) + " " + Quote(fileToRun));
            }
            if (deleteTemp) { try { File.Delete(fileToRun); } catch { } }
        }

        private async void OnBuild(object? sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(currentFile)) { AppendOutput("No file open to build."); return; }
            AppendOutput($"Emitting bytecode for {currentFile}...");
            var python = Environment.GetEnvironmentVariable("HSHARP_PYTHON") ?? "python3";
            var hsharp = FindHSharpPy();
            if (hsharp == null) AppendOutput("hsharp.py not found.");
            else await RunExternal(python, Quote(hsharp) + " --emit-bc " + Quote(currentFile));
        }

        private async void OnQoderBuild(object? sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(currentFile)) { AppendOutput("No file open to build with qoder."); return; }
            AppendOutput($"使用 qoder 编译 {currentFile}...");
            try
            {
                var (ok, outp) = await EnvironmentChecker.CompileWithQoderAsync(currentFile);
                AppendOutput(ok ? ("qoder 编译成功:\n" + outp) : ("qoder 编译失败:\n" + outp));
            }
            catch (Exception ex) { AppendOutput("qoder 编译异常: " + ex.Message); }
        }

        private async void OnRunBc(object? sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(currentFile)) { AppendOutput("No file open to run bytecode."); return; }
            var bc = Path.ChangeExtension(currentFile, ".hbc");
            if (!File.Exists(bc)) { AppendOutput($"Bytecode file not found: {bc}"); return; }
            var python = Environment.GetEnvironmentVariable("HSHARP_PYTHON") ?? "python3";
            var hsharp = FindHSharpPy();
            if (hsharp == null) AppendOutput("hsharp.py not found.");
            else await RunExternal(python, Quote(hsharp) + " --run-bc " + Quote(bc));
        }

        private async void OnRepl(object? sender, RoutedEventArgs e)
        {
            AppendOutput("Starting REPL...");
            var python = Environment.GetEnvironmentVariable("HSHARP_PYTHON") ?? "python3";
            var hsharp = FindHSharpPy();
            if (hsharp == null) { AppendOutput("hsharp.py not found."); return; }
            try { Process.Start(new ProcessStartInfo { FileName = python, Arguments = Quote(hsharp), UseShellExecute = true }); }
            catch (Exception ex) { AppendOutput("Failed to start REPL: " + ex.Message); }
        }

        static string Quote(string s) => s.Contains(' ') ? '"' + s + '"' : s;

        private bool TryLoadAvaloniaEdit()
        {
            try
            {
                var editorType = Type.GetType("AvaloniaEdit.TextEditor, AvaloniaEdit");
                if (editorType == null) return false;
                return true;
            }
            catch { return false; }
        }
        #endregion

        #region ── D3 Viewer ──────────────────────────────────────────
        private double _camYaw = 225;
        private double _camPitch = 35;
        private double _camDist = 1.0;
        private double _camPanX = 0;
        private double _camPanY = 0;
        private double _camLookX, _camLookY, _camLookZ;
        private bool _camDragging = false;
        private Point _camLastMouse;
        private int _camDragButton = 0;
        private List<D3SystemInfo> _d3Systems = new();
        private List<D3ScreenRegion> _d3ScreenRegions = new();
        private D3ScreenRegion? _d3Hovered = null;
        private D3ScreenRegion? _d3Selected = null;
        private D3ViewerWindow? _d3PopupWindow;

        public double CamDist => _camDist;

        private struct D3ScreenRegion
        {
            public D3RegionInfo Region;
            public string SystemName;
            public string SystemType;
            public Rect ScreenBounds;
            public double Depth;
        }

        // ── External window API ────────────────────────────────────
        public void SetCamPreset(double yaw, double pitch, double dist)
        {
            _camYaw = yaw; _camPitch = pitch; _camDist = dist;
        }

        public void OnD3RefreshExternal()
        {
            var editorCtrl = GetActiveEditorControl();
            var text = GetEditorText(editorCtrl);
            _d3Systems = ParseD3Systems(text);
            _d3Selected = null; _d3Hovered = null;
            RenderD3View(_d3Systems);
        }

        public void D3ZoomInExternal()
        {
            _camDist = Math.Clamp(_camDist * 0.8, 0.1, 10.0);
            UpdateAllZoomLabels();
            RenderD3View(_d3Systems);
        }

        public void D3ZoomOutExternal()
        {
            _camDist = Math.Clamp(_camDist * 1.25, 0.1, 10.0);
            UpdateAllZoomLabels();
            RenderD3View(_d3Systems);
        }

        public void D3ZoomFitExternal()
        {
            if (_d3Systems.Count == 0) return;
            var allRegions = new List<D3RegionInfo>();
            foreach (var sys in _d3Systems) allRegions.AddRange(sys.Regions);
            if (allRegions.Count == 0) return;
            int aMinX = allRegions.Min(r => r.MinX), aMaxX = allRegions.Max(r => r.MaxX);
            int aMinY = allRegions.Min(r => r.MinY), aMaxY = allRegions.Max(r => r.MaxY);
            int aMinZ = allRegions.Min(r => r.MinZ), aMaxZ = allRegions.Max(r => r.MaxZ);
            double sx = aMaxX - aMinX, sy = aMaxY - aMinY, sz = aMaxZ - aMinZ;
            if (sx < 1) sx = 1; if (sy < 1) sy = 1; if (sz < 1) sz = 1;
            double ms = Math.Max(sx, Math.Max(sy, sz));
            var canvas = GetActiveD3Canvas();
            double cw = canvas != null && canvas.Bounds.Width > 0 ? canvas.Bounds.Width : 280;
            double ch = canvas != null && canvas.Bounds.Height > 0 ? canvas.Bounds.Height : 200;
            _camDist = Math.Clamp(ms / (Math.Min(cw, ch) * 0.7) * 1.0, 0.1, 10.0);
            _camPanX = 0; _camPanY = 0;
            UpdateAllZoomLabels();
            RenderD3View(_d3Systems);
        }

        public void OnD3CanvasMouseDownExternal(Canvas canvas, PointerPressedEventArgs e)
        {
            var pt = e.GetPosition(canvas);
            _camDragging = true; _camLastMouse = pt;
            var props = e.GetCurrentPoint(canvas).Properties;
            if (props.IsLeftButtonPressed) _camDragButton = 1;
            else if (props.IsRightButtonPressed) _camDragButton = 2;
            else _camDragButton = 0;
            _d3Selected = null;
            foreach (var sr in _d3ScreenRegions) { if (sr.ScreenBounds.Contains(pt)) { _d3Selected = sr; break; } }
            RenderD3View(_d3Systems);
        }

        public void OnD3CanvasMouseMoveExternal(Canvas canvas, PointerEventArgs e)
        {
            var pt = e.GetPosition(canvas);
            if (_camDragging)
            {
                double dx = pt.X - _camLastMouse.X, dy = pt.Y - _camLastMouse.Y;
                if (_camDragButton == 1) { _camYaw -= dx * 0.5; _camPitch += dy * 0.5; _camPitch = Math.Clamp(_camPitch, 2, 88); }
                else if (_camDragButton == 2) { _camPanX += dx; _camPanY += dy; }
                _camLastMouse = pt;
                RenderD3View(_d3Systems);
                return;
            }
            var newHovered = (D3ScreenRegion?)null;
            foreach (var sr in _d3ScreenRegions) { if (sr.ScreenBounds.Contains(pt)) { newHovered = sr; break; } }
            if (newHovered?.Region.Name != _d3Hovered?.Region.Name) { _d3Hovered = newHovered; RenderD3View(_d3Systems); }
        }

        public void OnD3CanvasMouseUpExternal() { _camDragging = false; _camDragButton = 0; }

        public void OnD3CanvasMouseWheelExternal(PointerWheelEventArgs e)
        {
            _camDist = Math.Clamp(_camDist * (1.0 - e.Delta.Y * 0.1), 0.1, 10.0);
            UpdateAllZoomLabels();
            RenderD3View(_d3Systems);
        }

        public void DockD3Viewer()
        {
            if (_d3PopupWindow != null)
            {
                _d3PopupWindow.Close();
                _d3PopupWindow = null;
            }
            UpdatePopOutButton();
        }

        public void Window_D3ViewerClosed()
        {
            _d3PopupWindow = null;
            UpdatePopOutButton();
        }

        private void UpdateAllZoomLabels()
        {
            var mainLabel = this.FindControl<TextBlock>("D3ZoomLabel");
            if (mainLabel != null) mainLabel.Text = $"{_camDist:F1}×";
            if (_d3PopupWindow != null) _d3PopupWindow.UpdateZoomLabel(_camDist);
        }

        private Canvas? GetActiveD3Canvas()
        {
            if (_d3PopupWindow != null) return _d3PopupWindow.D3Canvas;
            return this.FindControl<Canvas>("D3Canvas");
        }

        private void UpdatePopOutButton()
        {
            var btn = this.FindControl<Button>("D3PopOutBtn");
            if (btn != null)
            {
                if (_d3PopupWindow != null) { btn.Content = "已分离"; btn.Background = new SolidColorBrush(Color.Parse("#2a2a1a")); }
                else { btn.Content = "分离"; btn.Background = new SolidColorBrush(Color.Parse("#2a1a1a")); }
            }
        }

        private void OnD3PopOut(object? s, RoutedEventArgs e)
        {
            if (_d3PopupWindow != null)
            {
                DockD3Viewer();
                return;
            }
            _d3PopupWindow = new D3ViewerWindow(this);
            _d3PopupWindow.Closed += (_, _) => Window_D3ViewerClosed();
            _d3PopupWindow.Show();
            _d3PopupWindow.UpdateZoomLabel(_camDist);
            UpdatePopOutButton();
            RenderD3View(_d3Systems);
        }

        private void OnD3CamTop(object? s, RoutedEventArgs e) { _camYaw = 0; _camPitch = 5; OnD3Refresh(null, null!); }
        private void OnD3CamFront(object? s, RoutedEventArgs e) { _camYaw = 270; _camPitch = 25; OnD3Refresh(null, null!); }
        private void OnD3CamSide(object? s, RoutedEventArgs e) { _camYaw = 0; _camPitch = 25; OnD3Refresh(null, null!); }
        private void OnD3CamReset(object? s, RoutedEventArgs e) { _camYaw = 225; _camPitch = 35; _camDist = 1.0; OnD3Refresh(null, null!); }

        private void OnD3ZoomIn(object? s, RoutedEventArgs e)
        {
            _camDist *= 0.8;
            _camDist = Math.Clamp(_camDist, 0.1, 10.0);
            var label = this.FindControl<TextBlock>("D3ZoomLabel");
            if (label != null) label.Text = $"{_camDist:F1}×";
            OnD3Refresh(null, null!);
        }

        private void OnD3ZoomOut(object? s, RoutedEventArgs e)
        {
            _camDist *= 1.25;
            _camDist = Math.Clamp(_camDist, 0.1, 10.0);
            var label = this.FindControl<TextBlock>("D3ZoomLabel");
            if (label != null) label.Text = $"{_camDist:F1}×";
            OnD3Refresh(null, null!);
        }

        private void OnD3ZoomFit(object? s, RoutedEventArgs e)
        {
            if (_d3Systems.Count == 0) return;
            var allRegions = new List<D3RegionInfo>();
            foreach (var sys in _d3Systems) allRegions.AddRange(sys.Regions);
            if (allRegions.Count == 0) return;
            int aMinX = allRegions.Min(r => r.MinX), aMaxX = allRegions.Max(r => r.MaxX);
            int aMinY = allRegions.Min(r => r.MinY), aMaxY = allRegions.Max(r => r.MaxY);
            int aMinZ = allRegions.Min(r => r.MinZ), aMaxZ = allRegions.Max(r => r.MaxZ);
            double sx = aMaxX - aMinX, sy = aMaxY - aMinY, sz = aMaxZ - aMinZ;
            if (sx < 1) sx = 1; if (sy < 1) sy = 1; if (sz < 1) sz = 1;
            double ms = Math.Max(sx, Math.Max(sy, sz));
            var canvas = this.FindControl<Canvas>("D3Canvas");
            double cw = canvas != null && canvas.Bounds.Width > 0 ? canvas.Bounds.Width : 280;
            double ch = canvas != null && canvas.Bounds.Height > 0 ? canvas.Bounds.Height : 200;
            double minDim = Math.Min(cw, ch);
            _camDist = ms / (minDim * 0.7) * 1.0;
            _camDist = Math.Clamp(_camDist, 0.1, 10.0);
            _camPanX = 0; _camPanY = 0;
            var label = this.FindControl<TextBlock>("D3ZoomLabel");
            if (label != null) label.Text = $"{_camDist:F1}×";
            OnD3Refresh(null, null!);
        }

        private void OnD3CanvasMouseDown(object? sender, PointerPressedEventArgs e)
        {
            var canvas = this.FindControl<Canvas>("D3Canvas"); if (canvas == null) return;
            var pt = e.GetPosition(canvas);
            _camDragging = true; _camLastMouse = pt;
            var props = e.GetCurrentPoint(canvas).Properties;
            if (props.IsLeftButtonPressed) _camDragButton = 1;
            else if (props.IsRightButtonPressed) _camDragButton = 2;
            else _camDragButton = 0;
            _d3Selected = null;
            foreach (var sr in _d3ScreenRegions) { if (sr.ScreenBounds.Contains(pt)) { _d3Selected = sr; break; } }
            RenderD3View(_d3Systems);
        }

        private void OnD3CanvasMouseMove(object? sender, PointerEventArgs e)
        {
            var canvas = this.FindControl<Canvas>("D3Canvas"); if (canvas == null) return;
            var pt = e.GetPosition(canvas);
            if (_camDragging)
            {
                double dx = pt.X - _camLastMouse.X, dy = pt.Y - _camLastMouse.Y;
                if (_camDragButton == 1) { _camYaw -= dx * 0.5; _camPitch += dy * 0.5; _camPitch = Math.Clamp(_camPitch, 2, 88); }
                else if (_camDragButton == 2) { _camPanX += dx; _camPanY += dy; }
                _camLastMouse = pt;
                RenderD3View(_d3Systems);
                return;
            }
            var newHovered = (D3ScreenRegion?)null;
            foreach (var sr in _d3ScreenRegions) { if (sr.ScreenBounds.Contains(pt)) { newHovered = sr; break; } }
            if (newHovered?.Region.Name != _d3Hovered?.Region.Name) { _d3Hovered = newHovered; RenderD3View(_d3Systems); }
        }

        private void OnD3CanvasMouseUp(object? sender, PointerReleasedEventArgs e) { _camDragging = false; _camDragButton = 0; }
        private void OnD3CanvasMouseWheel(object? sender, PointerWheelEventArgs e)
        {
            _camDist *= (1.0 - e.Delta.Y * 0.1);
            _camDist = Math.Clamp(_camDist, 0.1, 10.0);
            var label = this.FindControl<TextBlock>("D3ZoomLabel");
            if (label != null) label.Text = $"{_camDist:F1}×";
            RenderD3View(_d3Systems);
        }

        private void OnD3Refresh(object? sender, RoutedEventArgs e)
        {
            var editorCtrl = GetActiveEditorControl();
            var text = GetEditorText(editorCtrl);
            _d3Systems = ParseD3Systems(text);
            _d3Selected = null; _d3Hovered = null;
            RenderD3View(_d3Systems);
        }

        private List<D3SystemInfo> ParseD3Systems(string code)
        {
            var systems = new List<D3SystemInfo>();
            var d3Pattern = @"3dsizepower\s+(\w+)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}";
            var em3dPattern = @"em3d\s+(\w+)\s*(?:extends\s+(\w+))?\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}";
            var regionPattern = @"region\s+(\w+)\s*\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\)(?:\s+implements\s+([^{]+?))?\s*\{";
            var regionInterfacePattern = @"region_interface\s+(\w+)\s*\{";
            foreach (Match dm in Regex.Matches(code, d3Pattern, RegexOptions.Singleline))
            {
                var sys = new D3SystemInfo { Name = dm.Groups[1].Value, Type = "3dsizepower" };
                var body = dm.Groups[2].Value;
                foreach (Match rm in Regex.Matches(body, regionPattern, RegexOptions.Singleline))
                    sys.Regions.Add(new D3RegionInfo { Name = rm.Groups[1].Value, MinX = int.Parse(rm.Groups[2].Value), MinY = int.Parse(rm.Groups[3].Value), MinZ = int.Parse(rm.Groups[4].Value), MaxX = int.Parse(rm.Groups[5].Value), MaxY = int.Parse(rm.Groups[6].Value), MaxZ = int.Parse(rm.Groups[7].Value), Implements = rm.Groups[8].Success ? rm.Groups[8].Value.Trim().Split(',').Select(s => s.Trim()).ToList() : new List<string>() });
                foreach (Match rim in Regex.Matches(body, regionInterfacePattern, RegexOptions.Singleline))
                    sys.InterfaceNames.Add(rim.Groups[1].Value);
                systems.Add(sys);
            }
            foreach (Match em in Regex.Matches(code, em3dPattern, RegexOptions.Singleline))
            {
                var sys = new D3SystemInfo { Name = em.Groups[1].Value, Type = "em3d", Parent = em.Groups[2].Success ? em.Groups[2].Value : null };
                var body = em.Groups[3].Value;
                if (sys.Parent != null)
                {
                    var parent = systems.FirstOrDefault(s => s.Name == sys.Parent);
                    if (parent != null) { sys.Regions.AddRange(parent.Regions.Select(r => new D3RegionInfo { Name = r.Name, MinX = r.MinX, MinY = r.MinY, MinZ = r.MinZ, MaxX = r.MaxX, MaxY = r.MaxY, MaxZ = r.MaxZ, Implements = new List<string>(r.Implements) })); sys.InterfaceNames.AddRange(parent.InterfaceNames); }
                }
                foreach (Match rm in Regex.Matches(body, regionPattern, RegexOptions.Singleline))
                    sys.Regions.Add(new D3RegionInfo { Name = rm.Groups[1].Value, MinX = int.Parse(rm.Groups[2].Value), MinY = int.Parse(rm.Groups[3].Value), MinZ = int.Parse(rm.Groups[4].Value), MaxX = int.Parse(rm.Groups[5].Value), MaxY = int.Parse(rm.Groups[6].Value), MaxZ = int.Parse(rm.Groups[7].Value), Implements = rm.Groups[8].Success ? rm.Groups[8].Value.Trim().Split(',').Select(s => s.Trim()).ToList() : new List<string>() });
                systems.Add(sys);
            }
            return systems;
        }

        private (double sx, double sy) Project(double wx, double wy, double wz, double cx, double cy, double cz, double scale, double panX, double panY)
        {
            double yRad = _camYaw * Math.PI / 180.0, pRad = _camPitch * Math.PI / 180.0;
            double dx = wx - cx, dy = wy - cy, dz = wz - cz;
            double rx = dx * Math.Cos(yRad) - dz * Math.Sin(yRad);
            double rz = dx * Math.Sin(yRad) + dz * Math.Cos(yRad);
            double ry = dy;
            double sy = ry * Math.Cos(pRad) - rz * Math.Sin(pRad);
            double sz = ry * Math.Sin(pRad) + rz * Math.Cos(pRad);
            return (rx * scale + panX, -sy * scale + panY);
        }

        private void RenderD3View(List<D3SystemInfo> systems)
        {
            var mainCanvas = this.FindControl<Canvas>("D3Canvas");
            if (mainCanvas != null)
            {
                var infoText = this.FindControl<TextBlock>("D3Info");
                var statusText = this.FindControl<TextBlock>("D3Status");
                RenderD3ToCanvas(mainCanvas, infoText, statusText, systems);
            }
            if (_d3PopupWindow != null)
            {
                RenderD3ToCanvas(_d3PopupWindow.D3Canvas, _d3PopupWindow.InfoText, _d3PopupWindow.StatusText, systems);
            }
        }

        private void RenderD3ToCanvas(Canvas canvas, TextBlock? infoText, TextBlock? statusText, List<D3SystemInfo> systems)
        {
            canvas.Children.Clear();
            _d3ScreenRegions.Clear();

            bool hasRegions = systems.Count > 0 && systems.Sum(s => s.Regions.Count) > 0;
            int aMinX, aMaxX, aMinY, aMaxY, aMinZ, aMaxZ;
            List<(D3RegionInfo Region, string SysName, string SysType)> allRegions;

            if (hasRegions)
            {
                allRegions = new List<(D3RegionInfo Region, string SysName, string SysType)>();
                foreach (var s in systems) foreach (var r in s.Regions) allRegions.Add((r, s.Name, s.Type));
                aMinX = allRegions.Min(r => r.Region.MinX); aMaxX = allRegions.Max(r => r.Region.MaxX);
                aMinY = allRegions.Min(r => r.Region.MinY); aMaxY = allRegions.Max(r => r.Region.MaxY);
                aMinZ = allRegions.Min(r => r.Region.MinZ); aMaxZ = allRegions.Max(r => r.Region.MaxZ);
            }
            else
            {
                aMinX = -50; aMaxX = 50; aMinY = -50; aMaxY = 50; aMinZ = -50; aMaxZ = 50;
                allRegions = new();
                if (infoText != null)
                {
                    if (systems.Count == 0)
                        infoText.Text = "坐标系 — 等待数据…";
                    else
                        infoText.Text = "0 区域 — 显示坐标系";
                }
                if (statusText != null)
                {
                    if (systems.Count == 0)
                        statusText.Text = "在代码中定义 3dsizepower + region 块即可可视化";
                    else
                        statusText.Text = "当前系统内无区域定义";
                }
            }

            double wcx = (aMinX + aMaxX) / 2.0, wcy = (aMinY + aMaxY) / 2.0, wcz = (aMinZ + aMaxZ) / 2.0;
            _camLookX = wcx; _camLookY = wcy; _camLookZ = wcz;
            double cw = canvas.Bounds.Width > 0 ? canvas.Bounds.Width : 280;
            double ch = canvas.Bounds.Height > 0 ? canvas.Bounds.Height : 300;
            double sx = aMaxX - aMinX, sy_ = aMaxY - aMinY, sz = aMaxZ - aMinZ;
            if (sx < 1) sx = 1; if (sy_ < 1) sy_ = 1; if (sz < 1) sz = 1;
            double ms = Math.Max(sx, Math.Max(sy_, sz));
            double scale = Math.Min(cw, ch) / ms * _camDist * 0.7;
            double panX = cw / 2.0 + _camPanX, panY = ch * 0.6 + _camPanY;

            // ── Grid ──────────────────────────────────────────────
            int gs = (int)Math.Pow(10, Math.Floor(Math.Log10(ms * 0.5))); if (gs < 1) gs = 1;
            if (!hasRegions) { gs = 10; }
            int gx0 = (int)(Math.Floor(aMinX / (double)gs) * gs), gx1 = (int)(Math.Ceiling(aMaxX / (double)gs) * gs);
            int gz0 = (int)(Math.Floor(aMinZ / (double)gs) * gs), gz1 = (int)(Math.Ceiling(aMaxZ / (double)gs) * gs);
            double gy = aMinY;
            var gc = new SolidColorBrush(Color.FromArgb(30, 60, 100, 140));
            var gtc = new SolidColorBrush(Color.FromArgb(80, 80, 120, 160));
            for (int gx = gx0; gx <= gx1; gx += gs)
            {
                var a = Project(gx, gy, gz0, wcx, wcy, wcz, scale, panX, panY);
                var b = Project(gx, gy, gz1, wcx, wcy, wcz, scale, panX, panY);
                canvas.Children.Add(new Avalonia.Controls.Shapes.Line { StartPoint = new Point(a.sx, a.sy), EndPoint = new Point(b.sx, b.sy), Stroke = (gx % (gs * 5) == 0) ? gtc : gc, StrokeThickness = 0.5 });
            }
            for (int gz = gz0; gz <= gz1; gz += gs)
            {
                var a = Project(gx0, gy, gz, wcx, wcy, wcz, scale, panX, panY);
                var b = Project(gx1, gy, gz, wcx, wcy, wcz, scale, panX, panY);
                canvas.Children.Add(new Avalonia.Controls.Shapes.Line { StartPoint = new Point(a.sx, a.sy), EndPoint = new Point(b.sx, b.sy), Stroke = (gz % (gs * 5) == 0) ? gtc : gc, StrokeThickness = 0.5 });
            }

            // ── Axes (always drawn) ───────────────────────────────
            var axo = Project(aMinX, aMinY, aMinZ, wcx, wcy, wcz, scale, panX, panY);
            var axeX = Project(aMaxX, aMinY, aMinZ, wcx, wcy, wcz, scale, panX, panY);
            canvas.Children.Add(new Avalonia.Controls.Shapes.Line { StartPoint = new Point(axo.sx, axo.sy), EndPoint = new Point(axeX.sx, axeX.sy), Stroke = new SolidColorBrush(Color.FromRgb(244, 67, 53)), StrokeThickness = 2 });
            canvas.Children.Add(new TextBlock { Text = "X", FontSize = 10, FontWeight = FontWeight.Bold, Foreground = new SolidColorBrush(Color.FromRgb(244, 67, 53)), [Canvas.LeftProperty] = axeX.sx + 3, [Canvas.TopProperty] = axeX.sy - 8 });
            var axeY = Project(aMinX, aMaxY, aMinZ, wcx, wcy, wcz, scale, panX, panY);
            canvas.Children.Add(new Avalonia.Controls.Shapes.Line { StartPoint = new Point(axo.sx, axo.sy), EndPoint = new Point(axeY.sx, axeY.sy), Stroke = new SolidColorBrush(Color.FromRgb(52, 168, 83)), StrokeThickness = 2 });
            canvas.Children.Add(new TextBlock { Text = "Y", FontSize = 10, FontWeight = FontWeight.Bold, Foreground = new SolidColorBrush(Color.FromRgb(52, 168, 83)), [Canvas.LeftProperty] = axeY.sx + 3, [Canvas.TopProperty] = axeY.sy - 14 });
            var axeZ = Project(aMinX, aMinY, aMaxZ, wcx, wcy, wcz, scale, panX, panY);
            canvas.Children.Add(new Avalonia.Controls.Shapes.Line { StartPoint = new Point(axo.sx, axo.sy), EndPoint = new Point(axeZ.sx, axeZ.sy), Stroke = new SolidColorBrush(Color.FromRgb(66, 133, 244)), StrokeThickness = 2 });
            canvas.Children.Add(new TextBlock { Text = "Z", FontSize = 10, FontWeight = FontWeight.Bold, Foreground = new SolidColorBrush(Color.FromRgb(66, 133, 244)), [Canvas.LeftProperty] = axeZ.sx + 3, [Canvas.TopProperty] = axeZ.sy - 8 });
            canvas.Children.Add(new Avalonia.Controls.Shapes.Ellipse { Width = 6, Height = 6, Fill = Brushes.White, [Canvas.LeftProperty] = axo.sx - 3, [Canvas.TopProperty] = axo.sy - 3 });

            // ── Regions (only if present) ─────────────────────────
            if (hasRegions)
            {
                var colors = new[] { (Color.FromRgb(66, 133, 244), "b"), (Color.FromRgb(52, 168, 83), "g"), (Color.FromRgb(251, 188, 4), "y"), (Color.FromRgb(234, 67, 53), "r"), (Color.FromRgb(142, 68, 173), "p"), (Color.FromRgb(26, 188, 156), "t"), (Color.FromRgb(230, 126, 34), "o"), (Color.FromRgb(149, 165, 166), "w") };
                var di = new List<(double d, int ci, (D3RegionInfo R, string S, string T) item)>();
                int ci2 = 0;
                foreach (var it in allRegions) { double cwx = (it.Region.MinX + it.Region.MaxX) / 2.0, cwy = (it.Region.MinY + it.Region.MaxY) / 2.0, cwz = (it.Region.MinZ + it.Region.MaxZ) / 2.0; var cp = Project(cwx, cwy, cwz, wcx, wcy, wcz, scale, panX, panY); di.Add((cp.sy, ci2, it)); ci2++; }
                di.Sort((a, b) => b.d.CompareTo(a.d));
                foreach (var (depth, ci, (region, sysName, sysType)) in di)
                {
                    var corners = new List<(double x, double y, double z)>();
                    for (int ix = 0; ix <= 1; ix++) for (int iy = 0; iy <= 1; iy++) for (int iz = 0; iz <= 1; iz++) corners.Add((ix == 0 ? region.MinX : region.MaxX, iy == 0 ? region.MinY : region.MaxY, iz == 0 ? region.MinZ : region.MaxZ));
                    var proj = corners.Select(c => Project(c.x, c.y, c.z, wcx, wcy, wcz, scale, panX, panY)).ToList();
                    double sminX = proj.Min(p => p.sx), smaxX = proj.Max(p => p.sx), sminY = proj.Min(p => p.sy), smaxY = proj.Max(p => p.sy);
                    var sr = new Rect(sminX, sminY, smaxX - sminX, smaxY - sminY);
                    var color = colors[ci % colors.Length];
                    bool ih = _d3Hovered?.Region.Name == region.Name && _d3Hovered?.SystemName == sysName;
                    bool is_ = _d3Selected?.Region.Name == region.Name && _d3Selected?.SystemName == sysName;
                    byte alpha = (ih || is_) ? (byte)160 : (byte)70;
                    double st = (ih || is_) ? 2.5 : 1.0;
                    var sc2 = is_ ? new SolidColorBrush(Color.FromRgb(255, 220, 80)) : ih ? new SolidColorBrush(Color.FromRgb(180, 220, 255)) : new SolidColorBrush(color.Item1);
                    var fc = new SolidColorBrush(Color.FromArgb(alpha, color.Item1.R, color.Item1.G, color.Item1.B));
                    var topP = new[] { Project(region.MinX, region.MaxY, region.MinZ, wcx, wcy, wcz, scale, panX, panY), Project(region.MaxX, region.MaxY, region.MinZ, wcx, wcy, wcz, scale, panX, panY), Project(region.MaxX, region.MaxY, region.MaxZ, wcx, wcy, wcz, scale, panX, panY), Project(region.MinX, region.MaxY, region.MaxZ, wcx, wcy, wcz, scale, panX, panY) };
                    canvas.Children.Add(new Avalonia.Controls.Shapes.Polygon { Points = new List<Point> { new(topP[0].sx, topP[0].sy), new(topP[1].sx, topP[1].sy), new(topP[2].sx, topP[2].sy), new(topP[3].sx, topP[3].sy) }, Fill = fc, Stroke = sc2, StrokeThickness = st });
                    var df = new SolidColorBrush(Color.FromArgb((byte)(alpha * 0.7), color.Item1.R, color.Item1.G, color.Item1.B));
                    var rp = new[] { Project(region.MaxX, region.MinY, region.MinZ, wcx, wcy, wcz, scale, panX, panY), Project(region.MaxX, region.MaxY, region.MinZ, wcx, wcy, wcz, scale, panX, panY), Project(region.MaxX, region.MaxY, region.MaxZ, wcx, wcy, wcz, scale, panX, panY), Project(region.MaxX, region.MinY, region.MaxZ, wcx, wcy, wcz, scale, panX, panY) };
                    canvas.Children.Add(new Avalonia.Controls.Shapes.Polygon { Points = new List<Point> { new(rp[0].sx, rp[0].sy), new(rp[1].sx, rp[1].sy), new(rp[2].sx, rp[2].sy), new(rp[3].sx, rp[3].sy) }, Fill = df, Stroke = sc2, StrokeThickness = st });
                    var fp = new[] { Project(region.MinX, region.MinY, region.MinZ, wcx, wcy, wcz, scale, panX, panY), Project(region.MaxX, region.MinY, region.MinZ, wcx, wcy, wcz, scale, panX, panY), Project(region.MaxX, region.MaxY, region.MinZ, wcx, wcy, wcz, scale, panX, panY), Project(region.MinX, region.MaxY, region.MinZ, wcx, wcy, wcz, scale, panX, panY) };
                    canvas.Children.Add(new Avalonia.Controls.Shapes.Polygon { Points = new List<Point> { new(fp[0].sx, fp[0].sy), new(fp[1].sx, fp[1].sy), new(fp[2].sx, fp[2].sy), new(fp[3].sx, fp[3].sy) }, Fill = df, Stroke = sc2, StrokeThickness = st });
                    double lx = proj.Average(p => p.sx), ly = proj.Min(p => p.sy) - 16;
                    canvas.Children.Add(new TextBlock { Text = region.Name, FontSize = (ih || is_) ? 10 : 8, FontWeight = (ih || is_) ? FontWeight.Bold : FontWeight.Normal, Foreground = (ih || is_) ? new SolidColorBrush(Color.FromRgb(255, 255, 200)) : new SolidColorBrush(Color.FromRgb(200, 210, 230)), [Canvas.LeftProperty] = lx - 20, [Canvas.TopProperty] = ly });
                    if (region.Implements.Count > 0) canvas.Children.Add(new TextBlock { Text = "↗" + string.Join(",", region.Implements), FontSize = 7, Foreground = new SolidColorBrush(Color.FromRgb(180, 220, 100)), [Canvas.LeftProperty] = lx - 16, [Canvas.TopProperty] = ly + 12 });
                    _d3ScreenRegions.Add(new D3ScreenRegion { Region = region, SystemName = sysName, SystemType = sysType, ScreenBounds = sr, Depth = depth });
                    if (is_) canvas.Children.Add(new Avalonia.Controls.Shapes.Rectangle { [Canvas.LeftProperty] = sr.X - 2, [Canvas.TopProperty] = sr.Y - 2, Width = sr.Width + 4, Height = sr.Height + 4, Fill = null!, Stroke = new SolidColorBrush(Color.FromRgb(255, 220, 60)), StrokeThickness = 1.5, StrokeDashArray = new Avalonia.Collections.AvaloniaList<double> { 4, 4 } });
                }
                if (infoText != null) infoText.Text = $"{systems.Count}s · {allRegions.Count}r · {_camDist:F1}×";
                string stText = $"X:{aMinX}–{aMaxX}  Y:{aMinY}–{aMaxY}  Z:{aMinZ}–{aMaxZ}";
                if (_d3Hovered != null) { var hr = _d3Hovered.Value.Region; stText = $"⏺ {hr.Name}  [{hr.MinX},{hr.MaxX}]×[{hr.MinY},{hr.MaxY}]×[{hr.MinZ},{hr.MaxZ}]"; if (hr.Implements.Count > 0) stText += $"  implements: {string.Join(", ", hr.Implements)}"; }
                if (_d3Selected != null && _d3Hovered == null) { var sr2 = _d3Selected.Value.Region; stText = $"▶ SELECTED: {sr2.Name}  X[{sr2.MinX}–{sr2.MaxX}] Y[{sr2.MinY}–{sr2.MaxY}] Z[{sr2.MinZ}–{sr2.MaxZ}]"; }
                if (statusText != null) statusText.Text = stText;
            }
        }

        public class D3SystemInfo { public string Name { get; set; } = ""; public string Type { get; set; } = "3dsizepower"; public string? Parent { get; set; } public List<D3RegionInfo> Regions { get; set; } = new(); public List<string> InterfaceNames { get; set; } = new(); }
        public class D3RegionInfo { public string Name { get; set; } = ""; public int MinX, MinY, MinZ, MaxX, MaxY, MaxZ; public List<string> Implements { get; set; } = new(); }
        #endregion
    }
}