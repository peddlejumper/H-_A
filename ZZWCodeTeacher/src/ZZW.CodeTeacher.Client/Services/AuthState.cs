using ZZW.CodeTeacher.Application.DTOs;

namespace ZZW.CodeTeacher.Client.Services;

/// <summary>
/// 全局登录状态。登录态变更通过事件广播给所有订阅者(主窗口、IDE 等)。
/// 启动时从 <see cref="AuthTokenStore"/> 加载本地持久化的 token(免重登),
/// 登录成功时保存,退出登录时清除。
/// </summary>
public sealed class AuthState
{
    public string? AccessToken { get; private set; }
    public UserDto? CurrentUser { get; private set; }
    public bool IsLoggedIn => !string.IsNullOrEmpty(AccessToken) && CurrentUser is not null;

    public event EventHandler? Changed;

    public AuthState()
    {
        // 启动时尝试从本地恢复登录态:若有 token 且未过期,直接进 IDE,不进登录页
        var snap = AuthTokenStore.TryLoad();
        if (snap is not null)
        {
            AccessToken = snap.AccessToken;
            CurrentUser = snap.User;
        }
    }

    public void Set(AuthResultDto auth)
    {
        AccessToken = auth.AccessToken;
        CurrentUser = auth.User;
        AuthTokenStore.Save(auth); // 登录成功 → 持久化到本地
        Changed?.Invoke(this, EventArgs.Empty);
    }

    public void Clear()
    {
        AccessToken = null;
        CurrentUser = null;
        AuthTokenStore.Clear(); // 退出登录 → 清除本地凭证
        Changed?.Invoke(this, EventArgs.Empty);
    }
}
