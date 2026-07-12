using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>登录/注册窗口 ViewModel。支持登录与注册两种模式切换。</summary>
public partial class LoginViewModel : ViewModelBase
{
    private readonly AuthService _authService;
    private readonly AuthState _auth;

    [ObservableProperty]
    private string _username = "teacher1";

    [ObservableProperty]
    private string _password = "teacher12345";

    [ObservableProperty]
    private string _email = "";

    [ObservableProperty]
    private string _displayName = "";

    /// <summary>是否处于注册模式(false=登录)</summary>
    [ObservableProperty]
    private bool _isRegisterMode;

    [ObservableProperty]
    private bool _isBusy;

    [ObservableProperty]
    private string? _errorMessage;

    /// <summary>提交按钮文案(随模式切换)</summary>
    public string SubmitButtonText => IsRegisterMode ? "注 册" : "登 录";

    /// <summary>切换链接文案</summary>
    public string ToggleLinkText => IsRegisterMode ? "已有账号? 去登录" : "没有账号? 去注册";

    /// <summary>标题文案</summary>
    public string HeaderText => IsRegisterMode ? "创建账号" : "欢迎回来";

    /// <summary>副标题文案</summary>
    public string SubHeaderText => IsRegisterMode ? "注册以进入学员 IDE" : "登录以进入学员 IDE";

    public LoginViewModel(AuthService authService, AuthState auth)
    {
        _authService = authService;
        _auth = auth;
    }

    /// <summary>切换登录/注册模式</summary>
    [RelayCommand]
    private void ToggleMode()
    {
        IsRegisterMode = !IsRegisterMode;
        ErrorMessage = null;
        OnPropertyChanged(nameof(SubmitButtonText));
        OnPropertyChanged(nameof(ToggleLinkText));
        OnPropertyChanged(nameof(HeaderText));
        OnPropertyChanged(nameof(SubHeaderText));
    }

    /// <summary>主提交按钮:根据模式执行登录或注册</summary>
    [RelayCommand(CanExecute = nameof(CanSubmit))]
    private async Task SubmitAsync()
    {
        if (string.IsNullOrWhiteSpace(Username) || string.IsNullOrWhiteSpace(Password))
        {
            ErrorMessage = "用户名和密码不能为空";
            return;
        }
        if (IsRegisterMode)
        {
            if (string.IsNullOrWhiteSpace(Email) || !Email.Contains('@'))
            {
                ErrorMessage = "请输入合法的邮箱";
                return;
            }
            await RegisterAsync();
        }
        else
        {
            await LoginAsync();
        }
    }

    private async Task LoginAsync()
    {
        try
        {
            IsBusy = true;
            ErrorMessage = null;
            SetStatus("登录中…");
            var result = await _authService.LoginAsync(Username, Password);
            if (result is null)
            {
                ErrorMessage = "登录失败:无响应";
                return;
            }
            _auth.Set(result);
            SetStatus($"登录成功: {result.User.DisplayName}");
        }
        catch (ApiException ex)
        {
            ErrorMessage = $"登录失败 ({ex.StatusCode}): {ex.Body}";
            SetStatus("登录失败");
        }
        catch (Exception ex)
        {
            ErrorMessage = "登录异常: " + ex.Message;
            SetStatus("登录失败");
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task RegisterAsync()
    {
        try
        {
            IsBusy = true;
            ErrorMessage = null;
            SetStatus("注册中…");
            var dto = new RegisterDto(Username, Email, Password,
                string.IsNullOrWhiteSpace(DisplayName) ? Username : DisplayName);
            var result = await _authService.RegisterAsync(dto);
            if (result is null)
            {
                ErrorMessage = "注册失败:无响应";
                return;
            }
            _auth.Set(result);
            SetStatus($"注册成功: {result.User.DisplayName}");
        }
        catch (ApiException ex)
        {
            ErrorMessage = $"注册失败 ({ex.StatusCode}): {ex.Body}";
            SetStatus("注册失败");
        }
        catch (Exception ex)
        {
            ErrorMessage = "注册异常: " + ex.Message;
            SetStatus("注册失败");
        }
        finally
        {
            IsBusy = false;
        }
    }

    private bool CanSubmit() => !IsBusy;
    partial void OnIsBusyChanged(bool value) => SubmitCommand.NotifyCanExecuteChanged();
}
