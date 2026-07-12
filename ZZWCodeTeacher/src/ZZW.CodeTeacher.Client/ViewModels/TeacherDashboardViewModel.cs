using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Extensions.DependencyInjection;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>
/// 教师/管理员后台:题目管理 / 提交管理 / 用户管理 三 Tab。
/// 题目:CRUD + 启用切换 + 加用例;提交:列表 + 状态筛选 + 重新评测;用户:列表 + 搜索 + 角色切换。
/// </summary>
public partial class TeacherDashboardViewModel : ViewModelBase
{
    private readonly ProblemService _problems;
    private readonly UserService _users;
    private readonly SubmissionAdminService _submissions;
    private readonly AuthState _auth;
    private readonly IServiceProvider _sp;

    /// <summary>题目列表(题目管理 Tab)</summary>
    public ObservableCollection<ProblemListItemDto> Problems { get; } = new();

    /// <summary>提交列表(提交管理 Tab)</summary>
    public ObservableCollection<SubmissionDto> Submissions { get; } = new();

    /// <summary>用户列表(用户管理 Tab)</summary>
    public ObservableCollection<UserDto> Users { get; } = new();

    [ObservableProperty] private ProblemListItemDto? _selectedProblem;
    [ObservableProperty] private bool _isLoading;
    [ObservableProperty] private string? _errorMessage;
    [ObservableProperty] private string _searchText = "";
    [ObservableProperty] private ProblemEditVm? _currentProblemEditor;

    /// <summary>用户管理:当前选中的用户(点击行选中)</summary>
    [ObservableProperty] private UserDto? _selectedUser;

    /// <summary>用户管理:角色切换下拉的当前值(与 SelectedUser 联动)</summary>
    [ObservableProperty] private UserRole _selectedUserRole = UserRole.Student;

    /// <summary>提交管理:状态筛选下拉的当前值</summary>
    [ObservableProperty] private SubmissionStatusOptionVm? _selectedStatusOption;

    /// <summary>班级管理 VM(第 4 个 Tab「班级管理」内容)</summary>
    public GroupManagementViewModel Groups { get; }

    /// <summary>单学员进度 VM(用户 Tab 选中用户后展示进度详情)</summary>
    public UserProgressViewModel UserProgress { get; }

    /// <summary>用户 Tab 是否展开进度详情面板(选中用户后可切换)</summary>
    [ObservableProperty] private bool _isProgressPanelOpen;

    /// <summary>角色选项(Student/Teacher/Admin)</summary>
    public UserRole[] RoleOptions { get; } = { UserRole.Student, UserRole.Teacher, UserRole.Admin };

    /// <summary>难度选项(编辑表单下拉)</summary>
    public DifficultyLevel[] DifficultyOptions { get; } =
        { DifficultyLevel.Easy, DifficultyLevel.Medium, DifficultyLevel.Hard };

    /// <summary>提交状态筛选选项(含"全部状态")</summary>
    public ObservableCollection<SubmissionStatusOptionVm> SubmissionStatusOptions { get; } = new()
    {
        new(null, "全部状态"),
        new(SubmissionStatus.Pending, "等待中"),
        new(SubmissionStatus.Running, "评测中"),
        new(SubmissionStatus.Accepted, "通过"),
        new(SubmissionStatus.WrongAnswer, "答案错误"),
        new(SubmissionStatus.TimeLimitExceeded, "超时"),
        new(SubmissionStatus.RuntimeError, "运行错误"),
        new(SubmissionStatus.CompileError, "编译错误"),
    };

    public TeacherDashboardViewModel(ProblemService problems, UserService users,
        SubmissionAdminService submissions, AuthState auth, IServiceProvider sp,
        GroupManagementViewModel groups, UserProgressViewModel userProgress)
    {
        _problems = problems;
        _users = users;
        _submissions = submissions;
        _auth = auth;
        _sp = sp;
        Groups = groups;
        UserProgress = userProgress;

        // 默认状态筛选 = 全部(设置时会触发 OnSelectedStatusOptionChanged → 拉取提交)
        SelectedStatusOption = SubmissionStatusOptions[0];
        CurrentProblemEditor = new ProblemEditVm();

        // 初始加载题目与用户(提交由状态筛选变更触发)
        _ = RefreshProblemsAsync();
        _ = RefreshUsersAsync();
        // 班级列表后台加载(失败不阻塞)
        _ = Groups.RefreshAsync();
    }

    // ── 刷新 ──

    [RelayCommand]
    public async Task RefreshAllAsync()
    {
        await Task.WhenAll(RefreshProblemsAsync(), RefreshSubmissionsAsync(), RefreshUsersAsync());
    }

    [RelayCommand]
    public async Task RefreshProblemsAsync()
    {
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            var page = await _problems.ListAsync(1, 200);
            Problems.Clear();
            if (page is not null)
                foreach (var p in page.Items) Problems.Add(p);
            SetStatus($"题目已刷新: {Problems.Count} 条");
        }
        catch (Exception ex)
        {
            ErrorMessage = "题目列表加载失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    public async Task RefreshSubmissionsAsync()
    {
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            var status = SelectedStatusOption?.Value;
            var page = await _submissions.ListAllAsync(1, 200, status);
            Submissions.Clear();
            if (page is not null)
                foreach (var s in page.Items) Submissions.Add(s);
            SetStatus($"提交已刷新: {Submissions.Count} 条");
        }
        catch (Exception ex)
        {
            ErrorMessage = "提交列表加载失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    public async Task RefreshUsersAsync()
    {
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            var page = await _users.ListAsync(1, 200, search: SearchText);
            Users.Clear();
            if (page is not null)
                foreach (var u in page.Items) Users.Add(u);
            SetStatus($"用户已刷新: {Users.Count} 条");
        }
        catch (Exception ex)
        {
            ErrorMessage = "用户列表加载失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    // 状态筛选变更 → 重新拉取提交
    partial void OnSelectedStatusOptionChanged(SubmissionStatusOptionVm? value)
        => _ = RefreshSubmissionsAsync();

    // 选中用户变更 → 同步角色下拉到该用户当前角色,并加载其进度详情
    partial void OnSelectedUserChanged(UserDto? value)
    {
        if (value is not null)
        {
            SelectedUserRole = value.Role;
            // 后台加载该学员进度(后端未就绪则面板显示"暂无数据")
            _ = UserProgress.LoadAsync(value.Id);
            IsProgressPanelOpen = true;
        }
        else
        {
            IsProgressPanelOpen = false;
        }
    }

    // 角色下拉变更 → 调接口切换(仅当与当前用户角色不同时)
    partial void OnSelectedUserRoleChanged(UserRole value)
    {
        if (SelectedUser is not null && value != SelectedUser.Role)
            _ = ChangeUserRoleAsync(SelectedUser, value);
    }

    /// <summary>折叠/展开进度详情面板(用户 Tab 底部)。</summary>
    [RelayCommand]
    private void ToggleProgressPanel() => IsProgressPanelOpen = !IsProgressPanelOpen;

    private async Task ChangeUserRoleAsync(UserDto user, UserRole role)
    {
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            var updated = await _users.UpdateRoleAsync(user.Id, role);
            if (updated is not null)
            {
                // 记录不可变:按值定位旧记录,替换为新记录(保持原位置)
                var idx = Users.IndexOf(user);
                if (idx >= 0)
                {
                    Users.RemoveAt(idx);
                    Users.Insert(idx, updated);
                }
                SelectedUser = updated;
                SetStatus($"已将 {user.Username} 角色切换为 {role}");
            }
        }
        catch (Exception ex)
        {
            ErrorMessage = "角色切换失败: " + ex.Message;
            ShowError(ErrorMessage);
            // 回滚下拉显示到真实角色
            if (SelectedUser is not null) SelectedUserRole = SelectedUser.Role;
        }
        finally
        {
            IsLoading = false;
        }
    }

    // ── 题目管理 ──

    /// <summary>新建题目:清空编辑表单为空白</summary>
    [RelayCommand]
    private void NewProblem()
    {
        SelectedProblem = null;
        CurrentProblemEditor = new ProblemEditVm();
        SetStatus("新建题目:填写表单后点保存");
    }

    /// <summary>编辑选中题:拉取详情后填充表单</summary>
    [RelayCommand]
    private async Task EditProblemAsync()
    {
        if (SelectedProblem is null)
        {
            ShowError("请先在左侧选择一道题目");
            return;
        }
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            var detail = await _problems.GetAsync(SelectedProblem.Id);
            if (detail is null)
            {
                ShowError("题目详情加载失败");
                return;
            }
            CurrentProblemEditor = ProblemEditVm.FromDetail(detail);
            SetStatus($"编辑题目: {detail.Code} — {detail.Title}");
        }
        catch (Exception ex)
        {
            ErrorMessage = "题目详情加载失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>保存题目(EditingId 为空则创建,否则更新)</summary>
    [RelayCommand]
    private async Task SaveProblemAsync()
    {
        var ed = CurrentProblemEditor;
        if (ed is null)
        {
            ShowError("编辑器未初始化");
            return;
        }
        if (string.IsNullOrWhiteSpace(ed.Code))
        {
            ShowError("题号不能为空");
            return;
        }
        if (string.IsNullOrWhiteSpace(ed.Title))
        {
            ShowError("标题不能为空");
            return;
        }

        try
        {
            IsLoading = true;
            ErrorMessage = null;
            var langs = ed.SelectedLanguages;
            var tags = ed.TagList;

            if (ed.EditingId is null)
            {
                var created = await _problems.CreateAsync(new CreateProblemDto(
                    ed.Code.Trim(), ed.Title.Trim(), ed.Description, ed.Difficulty,
                    ed.TimeLimitMs, ed.MemoryLimitKb, ed.Template, tags, langs));
                if (created is not null)
                {
                    ed.EditingId = created.Id;
                    SetStatus($"题目已创建: {created.Code}");
                }
            }
            else
            {
                var updated = await _problems.UpdateAsync(ed.EditingId.Value, new UpdateProblemDto(
                    ed.Title.Trim(), ed.Description, ed.Difficulty,
                    ed.TimeLimitMs, ed.MemoryLimitKb, ed.Template, tags, langs));
                if (updated is not null)
                    SetStatus($"题目已更新: {updated.Code}");
            }

            await RefreshProblemsAsync();
        }
        catch (Exception ex)
        {
            ErrorMessage = "保存题目失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task DeleteProblemAsync()
    {
        var id = SelectedProblem?.Id ?? CurrentProblemEditor?.EditingId;
        if (id is null)
        {
            ShowError("请先选择一道题目");
            return;
        }
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            await _problems.DeleteAsync(id.Value);
            SetStatus("题目已删除");
            if (CurrentProblemEditor?.EditingId == id)
                CurrentProblemEditor = new ProblemEditVm();
            await RefreshProblemsAsync();
        }
        catch (Exception ex)
        {
            ErrorMessage = "删除题目失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    [RelayCommand]
    private async Task ToggleProblemActiveAsync()
    {
        if (SelectedProblem is null)
        {
            ShowError("请先选择一道题目");
            return;
        }
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            var target = !SelectedProblem.IsActive;
            await _problems.ToggleAsync(SelectedProblem.Id, target);
            SetStatus($"题目已{(target ? "启用" : "停用")}");
            await RefreshProblemsAsync();
        }
        catch (Exception ex)
        {
            ErrorMessage = "启用状态切换失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    /// <summary>给当前编辑题追加一个测试用例(题目须已保存,即 EditingId 非空)</summary>
    [RelayCommand]
    private async Task AddTestCaseAsync()
    {
        var ed = CurrentProblemEditor;
        if (ed is null)
        {
            ShowError("编辑器未初始化");
            return;
        }
        if (ed.EditingId is null)
        {
            ShowError("请先保存题目,再添加测试用例");
            return;
        }
        if (string.IsNullOrEmpty(ed.NewTestCaseInput) && string.IsNullOrEmpty(ed.NewTestCaseExpected))
        {
            ShowError("用例输入与期望输出不能同时为空");
            return;
        }
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            await _problems.AddTestCaseAsync(ed.EditingId.Value, new AddTestCaseDto(
                ed.NewTestCaseInput ?? "", ed.NewTestCaseExpected ?? "", ed.NewTestCaseIsSample));
            SetStatus("测试用例已添加");
            ed.NewTestCaseInput = "";
            ed.NewTestCaseExpected = "";
            ed.NewTestCaseIsSample = false;
            await RefreshProblemsAsync();
        }
        catch (Exception ex)
        {
            ErrorMessage = "添加用例失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    // ── 提交管理 ──

    /// <summary>重新评测指定提交(行按钮触发)</summary>
    [RelayCommand]
    private async Task RejudgeAsync(SubmissionDto? sub)
    {
        if (sub is null) return;
        try
        {
            IsLoading = true;
            ErrorMessage = null;
            await _submissions.RejudgeAsync(sub.Id);
            SetStatus($"已触发重新评测: {sub.ProblemCode} / {sub.Username}");
            await RefreshSubmissionsAsync();
        }
        catch (Exception ex)
        {
            ErrorMessage = "重新评测失败: " + ex.Message;
            ShowError(ErrorMessage);
        }
        finally
        {
            IsLoading = false;
        }
    }

    // ── 用户管理 ──

    /// <summary>选中某用户(行按钮触发),联动底部角色切换区</summary>
    [RelayCommand]
    private void SelectUser(UserDto? user) => SelectedUser = user;

    [RelayCommand]
    private void BackToIde() => NavigateTo(null!);
}

/// <summary>题目创建/编辑表单视图模型(承载表单字段与校验态)</summary>
public partial class ProblemEditVm : ObservableObject
{
    [ObservableProperty] private Guid? _editingId;
    [ObservableProperty] private string _code = "";
    [ObservableProperty] private string _title = "";
    [ObservableProperty] private string _description = "";
    [ObservableProperty] private DifficultyLevel _difficulty = DifficultyLevel.Easy;
    [ObservableProperty] private int _timeLimitMs = 1000;
    [ObservableProperty] private int _memoryLimitKb = 262144; // 256 MB
    [ObservableProperty] private string _template = "";
    [ObservableProperty] private string _tags = "";

    // 添加用例的输入字段
    [ObservableProperty] private string _newTestCaseInput = "";
    [ObservableProperty] private string _newTestCaseExpected = "";
    [ObservableProperty] private bool _newTestCaseIsSample;

    /// <summary>支持语言勾选列表(初始化时填充全部 15 种语言)</summary>
    public ObservableCollection<LanguageOptionVm> LanguageOptions { get; } = new();

    /// <summary>是否为新建态(题号可编辑)</summary>
    public bool IsNew => EditingId is null;

    /// <summary>已勾选的支持语言(保存时读取)</summary>
    public IReadOnlyList<SupportedLanguage> SelectedLanguages =>
        LanguageOptions.Where(o => o.IsSelected).Select(o => o.Language).ToArray();

    /// <summary>标签列表(逗号分隔字符串拆分,去空白)</summary>
    public IReadOnlyList<string> TagList =>
        Tags.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

    public ProblemEditVm()
    {
        foreach (SupportedLanguage lang in Enum.GetValues<SupportedLanguage>())
            LanguageOptions.Add(new LanguageOptionVm(lang));
    }

    /// <summary>从题目详情构造编辑表单(预填字段 + 回勾支持语言)</summary>
    public static ProblemEditVm FromDetail(ProblemDto d)
    {
        var vm = new ProblemEditVm
        {
            EditingId = d.Id,
            Code = d.Code,
            Title = d.Title,
            Description = d.Description,
            Difficulty = d.Difficulty,
            TimeLimitMs = d.TimeLimitMs,
            MemoryLimitKb = d.MemoryLimitKb,
            Template = d.Template,
            Tags = string.Join(", ", d.Tags),
        };
        foreach (var opt in vm.LanguageOptions)
            opt.IsSelected = d.SupportedLanguages.Contains(opt.Language);
        return vm;
    }

    // EditingId 变更 → 通知 IsNew 重新求值(控制题号输入框是否可用)
    partial void OnEditingIdChanged(Guid? value)
        => OnPropertyChanged(nameof(IsNew));
}

/// <summary>语言勾选项:是否选中 + 语言枚举 + 显示名</summary>
public partial class LanguageOptionVm : ObservableObject
{
    [ObservableProperty] private bool _isSelected;

    public SupportedLanguage Language { get; }
    public string DisplayName => Language.DisplayName();

    public LanguageOptionVm(SupportedLanguage lang) => Language = lang;
}

/// <summary>提交状态筛选选项(Value 为 null 表示"全部状态")</summary>
public sealed record SubmissionStatusOptionVm(SubmissionStatus? Value, string Display);
