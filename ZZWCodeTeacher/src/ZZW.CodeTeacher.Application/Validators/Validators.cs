namespace ZZW.CodeTeacher.Application.Validators;

using FluentValidation;
using ZZW.CodeTeacher.Application.Commands;

/// <summary>创建题目命令验证</summary>
public sealed class CreateProblemCommandValidator : AbstractValidator<CreateProblemCommand>
{
    public CreateProblemCommandValidator()
    {
        RuleFor(x => x.Code).NotEmpty().MaximumLength(20)
            .Matches(@"^P\d{3,5}$").WithMessage("题号格式应为 P001 ~ P99999");
        RuleFor(x => x.Title).NotEmpty().MaximumLength(200);
        RuleFor(x => x.Description).NotEmpty();
        RuleFor(x => x.Difficulty).IsInEnum();
        RuleFor(x => x.TimeLimitMs).InclusiveBetween(100, 30000);
        RuleFor(x => x.MemoryLimitKb).InclusiveBetween(1024, 524288);
        RuleFor(x => x.Tags).Must(t => t is null || t.Count <= 10)
            .WithMessage("标签数量不能超过 10");
        RuleFor(x => x.SupportedLanguages)
            .NotNull().WithMessage("必须指定至少 1 种支持的语言")
            .Must(list => list is not null && list.Count > 0)
            .WithMessage("必须指定至少 1 种支持的语言")
            .Must(list => list is null || list.Distinct().Count() == list.Count)
            .WithMessage("支持语言不能有重复");
    }
}

/// <summary>更新题目命令验证</summary>
public sealed class UpdateProblemCommandValidator : AbstractValidator<UpdateProblemCommand>
{
    public UpdateProblemCommandValidator()
    {
        RuleFor(x => x.Id).NotEmpty();
        RuleFor(x => x.Title).MaximumLength(200).When(x => x.Title is not null);
        RuleFor(x => x.TimeLimitMs).InclusiveBetween(100, 30000).When(x => x.TimeLimitMs.HasValue);
        RuleFor(x => x.MemoryLimitKb).InclusiveBetween(1024, 524288).When(x => x.MemoryLimitKb.HasValue);
    }
}

/// <summary>添加测试用例命令验证</summary>
public sealed class AddTestCaseCommandValidator : AbstractValidator<AddTestCaseCommand>
{
    public AddTestCaseCommandValidator()
    {
        RuleFor(x => x.ProblemId).NotEmpty();
        RuleFor(x => x.ExpectedOutput).NotNull();
    }
}

/// <summary>注册命令验证</summary>
public sealed class RegisterCommandValidator : AbstractValidator<RegisterCommand>
{
    public RegisterCommandValidator()
    {
        RuleFor(x => x.Username).NotEmpty().Length(3, 32)
            .Matches(@"^[a-zA-Z0-9_]+$").WithMessage("用户名只能包含字母、数字、下划线");
        RuleFor(x => x.Email)
            .NotEmpty()
            .Must(e => !string.IsNullOrWhiteSpace(e) && EmailRegex.IsValidEmail(e))
            .WithMessage("'Email' 不是有效的电子邮件地址");
        RuleFor(x => x.Password).NotEmpty().MinimumLength(8).MaximumLength(128);
        RuleFor(x => x.DisplayName).MaximumLength(50);
    }
}

/// <summary>登录命令验证</summary>
public sealed class LoginCommandValidator : AbstractValidator<LoginCommand>
{
    public LoginCommandValidator()
    {
        RuleFor(x => x.Username).NotEmpty();
        RuleFor(x => x.Password).NotEmpty();
    }
}

/// <summary>
/// 简单但实用的邮件格式校验(.NET 10 的 MailAddress 过于严格,改用正则)。
/// 规则:local@domain.tld,local 与 domain 由字母数字+._%- 组成,tld 至少 2 个字母。
/// </summary>
internal static class EmailRegex
{
    private static readonly System.Text.RegularExpressions.Regex Pattern =
        new(@"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$",
            System.Text.RegularExpressions.RegexOptions.Compiled);

    public static bool IsValidEmail(string email) => Pattern.IsMatch(email);
}

/// <summary>提交代码命令验证</summary>
public sealed class SubmitCodeCommandValidator : AbstractValidator<SubmitCodeCommand>
{
    public SubmitCodeCommandValidator()
    {
        RuleFor(x => x.ProblemId).NotEmpty();
        RuleFor(x => x.Code).NotEmpty().MaximumLength(65536)
            .WithMessage("代码长度不能超过 64KB");
        RuleFor(x => x.Language).IsInEnum()
            .WithMessage("不支持的语言,请使用 SupportedLanguage 枚举值");
    }
}
