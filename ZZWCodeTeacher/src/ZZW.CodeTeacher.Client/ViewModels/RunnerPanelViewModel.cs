using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>运行/提交面板(中心下半)。</summary>
public partial class RunnerPanelViewModel : ViewModelBase
{
    private readonly SubmissionService _submissions;
    private ProblemDto? _problem;
    private SupportedLanguage _language = SupportedLanguage.Python;

    [ObservableProperty]
    private string _output = "";

    [ObservableProperty]
    private string _status = "就绪";

    [ObservableProperty]
    private bool _isRunning;

    [ObservableProperty]
    private string? _errorMessage;

    public RunnerPanelViewModel(SubmissionService submissions)
    {
        _submissions = submissions;
    }

    /// <summary>当前提交语言(由 MainIdeViewModel 在编辑器语言切换时同步)</summary>
    public SupportedLanguage Language
    {
        get => _language;
        set => SetProperty(ref _language, value);
    }

    public void SetProblem(ProblemDto problem)
    {
        _problem = problem;
        Output = "";
        Status = "就绪";
        ErrorMessage = null;
    }

    [RelayCommand]
    public async Task RunSampleAsync(string code)
    {
        if (_problem is null)
        {
            Status = "请先选择题";
            return;
        }
        if (_problem.Samples.Count == 0)
        {
            Status = "该题没有样例";
            return;
        }

        try
        {
            IsRunning = true;
            ErrorMessage = null;
            Status = "运行样例…";
            // 直接提交评测,得到完整评测结果
            var sub = await _submissions.SubmitAsync(new SubmitCodeDto(_problem.Id, code, Language));
            if (sub is not null)
            {
                Status = $"样例: {(sub.PassedCases == sub.TotalCases ? "通过 ✓" : $"未通过 {sub.PassedCases}/{sub.TotalCases}")}";
                Output = sub.ErrorMessage ?? $"已通过 {sub.PassedCases}/{sub.TotalCases} 用例,分数 {sub.Score}";
            }
        }
        catch (Exception ex)
        {
            ErrorMessage = ex.Message;
            Status = "运行失败";
            Output = ex.Message;
        }
        finally
        {
            IsRunning = false;
        }
    }

    [RelayCommand]
    public async Task<SubmissionDto?> SubmitAsync(string code)
    {
        if (_problem is null)
        {
            Status = "请先选择题";
            return null;
        }
        try
        {
            IsRunning = true;
            ErrorMessage = null;
            Status = $"提交评测中…({Language.DisplayName()})";
            var sub = await _submissions.SubmitAsync(new SubmitCodeDto(_problem.Id, code, Language));
            if (sub is not null)
            {
                Status = $"提交完成: {sub.Status}, 分数 {sub.Score}/{sub.TotalCases}";
                Output = FormatReport(sub);
            }
            return sub;
        }
        catch (Exception ex)
        {
            ErrorMessage = ex.Message;
            Status = "提交失败";
            Output = ex.Message;
            return null;
        }
        finally
        {
            IsRunning = false;
        }
    }

    private static string FormatReport(SubmissionDto s)
    {
        var lines = new List<string>
        {
            $"# 提交 {s.Id}",
            $"题目: {s.ProblemCode} - {s.ProblemTitle}",
            $"语言: {s.Language}",
            $"状态: {s.Status}",
            $"通过: {s.PassedCases}/{s.TotalCases}    分数: {s.Score}",
            $"耗时: {s.ElapsedMs} ms    代码行数: {s.LineCount}",
        };
        if (!string.IsNullOrWhiteSpace(s.ErrorMessage))
        {
            lines.Add("");
            lines.Add("## 错误信息");
            lines.Add(s.ErrorMessage);
        }
        return string.Join('\n', lines);
    }
}
