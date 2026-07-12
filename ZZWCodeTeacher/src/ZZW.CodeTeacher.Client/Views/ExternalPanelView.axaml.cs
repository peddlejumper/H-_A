using Avalonia.Controls;

namespace ZZW.CodeTeacher.Client.Views;

/// <summary>
/// 第三方平台面板视图 —— 纯 Avalonia 实现(无 CEF)。
/// 第三方平台通过系统浏览器打开,视图内显示登录状态与洛谷题库导航。
/// </summary>
public partial class ExternalPanelView : UserControl
{
    public ExternalPanelView() => InitializeComponent();
}
