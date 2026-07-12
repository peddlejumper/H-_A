using CommunityToolkit.Mvvm.ComponentModel;
using Serilog;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>所有 ViewModel 基类 —— 继承 ObservableObject 以支持属性变更通知。</summary>
public abstract class ViewModelBase : ObservableObject
{
    /// <summary>切换主窗口活动内容(登录 ↔ IDE)。</summary>
    public event EventHandler<ViewModelBase?>? RequestViewChange;
    public event EventHandler<string>? RequestStatus;
    public event EventHandler<string>? RequestError;

    protected void NavigateTo(ViewModelBase? next)
        => RequestViewChange?.Invoke(this, next);

    protected void SetStatus(string text) => RequestStatus?.Invoke(this, text);

    /// <summary>广播错误信息到状态栏,并写入本地错误日志(便于排查)。</summary>
    protected void ShowError(string text)
    {
        Log.Error("ViewModel 错误: {Error}", text);
        RequestError?.Invoke(this, text);
    }
}
