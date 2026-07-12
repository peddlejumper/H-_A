namespace ZZW.CodeTeacher.Domain.Enums;

/// <summary>题目难度等级</summary>
public enum DifficultyLevel
{
    Easy = 0,
    Medium = 1,
    Hard = 2
}

/// <summary>提交评测状态</summary>
public enum SubmissionStatus
{
    Pending = 0,
    Running = 1,
    Accepted = 2,
    WrongAnswer = 3,
    TimeLimitExceeded = 4,
    RuntimeError = 5,
    CompileError = 6,
    MemoryLimitExceeded = 7
}

/// <summary>
/// 评测输出比对器类型(决定 expected/actual 如何比较)。
/// </summary>
public enum CheckerType
{
    /// <summary>精确匹配(行级,容忍行尾空白)</summary>
    Exact = 0,

    /// <summary>浮点容差:逐行 Trim,数字行用浮点容差,非数字行精确匹配</summary>
    FloatTolerance = 1,

    /// <summary>特判(Special Judge):需外部 checker 脚本,暂未实现,降级为 Exact</summary>
    SpecialJudge = 2
}

/// <summary>用户角色</summary>
public enum UserRole
{
    Student = 0,
    Teacher = 1,
    Admin = 2
}

/// <summary>班级成员角色</summary>
public enum GroupMemberRole
{
    Member = 0,
    Owner = 1
}

/// <summary>
/// 支持的教学编程语言(15 种主流语言)。
/// 提交代码与题目支持语言都基于此枚举,杜绝散落的字符串硬编码。
/// </summary>
public enum SupportedLanguage
{
    Python = 0,
    JavaScript = 1,
    TypeScript = 2,
    Java = 3,
    C = 4,
    Cpp = 5,
    CSharp = 6,
    Go = 7,
    Rust = 8,
    Ruby = 9,
    PHP = 10,
    Swift = 11,
    Kotlin = 12,
    Scala = 13,
    HSharp = 14
}

/// <summary>SupportedLanguage 的辅助扩展:提供显示名与文件后缀等元数据。</summary>
public static class SupportedLanguageExtensions
{
    /// <summary>显示名(用于 UI 下拉与日志)</summary>
    public static string DisplayName(this SupportedLanguage lang) => lang switch
    {
        SupportedLanguage.Python => "Python",
        SupportedLanguage.JavaScript => "JavaScript",
        SupportedLanguage.TypeScript => "TypeScript",
        SupportedLanguage.Java => "Java",
        SupportedLanguage.C => "C",
        SupportedLanguage.Cpp => "C++",
        SupportedLanguage.CSharp => "C#",
        SupportedLanguage.Go => "Go",
        SupportedLanguage.Rust => "Rust",
        SupportedLanguage.Ruby => "Ruby",
        SupportedLanguage.PHP => "PHP",
        SupportedLanguage.Swift => "Swift",
        SupportedLanguage.Kotlin => "Kotlin",
        SupportedLanguage.Scala => "Scala",
        SupportedLanguage.HSharp => "H#",
        _ => lang.ToString()
    };

    /// <summary>源文件后缀(含点)</summary>
    public static string FileExtension(this SupportedLanguage lang) => lang switch
    {
        SupportedLanguage.Python => ".py",
        SupportedLanguage.JavaScript => ".js",
        SupportedLanguage.TypeScript => ".ts",
        SupportedLanguage.Java => ".java",
        SupportedLanguage.C => ".c",
        SupportedLanguage.Cpp => ".cpp",
        SupportedLanguage.CSharp => ".cs",
        SupportedLanguage.Go => ".go",
        SupportedLanguage.Rust => ".rs",
        SupportedLanguage.Ruby => ".rb",
        SupportedLanguage.PHP => ".php",
        SupportedLanguage.Swift => ".swift",
        SupportedLanguage.Kotlin => ".kt",
        SupportedLanguage.Scala => ".scala",
        SupportedLanguage.HSharp => ".hs",
        _ => ".txt"
    };

    /// <summary>是否需要编译步骤(编译型语言)</summary>
    public static bool IsCompiled(this SupportedLanguage lang) => lang switch
    {
        SupportedLanguage.Java => true,
        SupportedLanguage.C => true,
        SupportedLanguage.Cpp => true,
        SupportedLanguage.CSharp => true,
        SupportedLanguage.Go => true,
        SupportedLanguage.Rust => true,
        SupportedLanguage.Swift => true,
        SupportedLanguage.Kotlin => true,
        SupportedLanguage.Scala => true,
        SupportedLanguage.TypeScript => true, // tsc → js
        _ => false
    };

    /// <summary>从字符串解析(忽略大小写,失败返回 null)</summary>
    public static SupportedLanguage? ParseOrNull(string? text)
    {
        if (string.IsNullOrWhiteSpace(text)) return null;
        // 先按枚举名/DisplayName 匹配
        foreach (SupportedLanguage v in Enum.GetValues<SupportedLanguage>())
        {
            if (string.Equals(v.ToString(), text, StringComparison.OrdinalIgnoreCase) ||
                string.Equals(v.DisplayName(), text, StringComparison.OrdinalIgnoreCase))
            {
                return v;
            }
        }
        // 常见别名
        return text.Trim().ToLowerInvariant() switch
        {
            "py" or "python3" => SupportedLanguage.Python,
            "js" => SupportedLanguage.JavaScript,
            "ts" => SupportedLanguage.TypeScript,
            "c++" or "cpp" or "cxx" => SupportedLanguage.Cpp,
            "c#" or "cs" or "csharp" => SupportedLanguage.CSharp,
            "golang" => SupportedLanguage.Go,
            "rs" => SupportedLanguage.Rust,
            "rb" => SupportedLanguage.Ruby,
            "kt" => SupportedLanguage.Kotlin,
            "hsharp" or "h#" or "hs" => SupportedLanguage.HSharp,
            _ => null
        };
    }
}
