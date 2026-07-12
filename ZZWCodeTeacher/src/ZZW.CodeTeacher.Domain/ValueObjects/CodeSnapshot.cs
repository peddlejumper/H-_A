namespace ZZW.CodeTeacher.Domain.ValueObjects;

using ZZW.CodeTeacher.Domain.Enums;

/// <summary>
/// 代码快照值对象 —— 记录某次提交的代码内容与语言。
/// 值对象:不可变、无身份、按值比较。
/// Language 为强类型枚举 SupportedLanguage,杜绝字符串硬编码。
/// </summary>
public readonly record struct CodeSnapshot(
    string Content,
    SupportedLanguage Language,
    int LineCount,
    int CharCount)
{
    /// <summary>从源码文本创建代码快照(自动统计行数与字符数)</summary>
    public static CodeSnapshot Create(string content, SupportedLanguage language)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(content);
        var lineCount = content.Count(c => c == '\n') + 1;
        return new CodeSnapshot(content, language, lineCount, content.Length);
    }

    /// <summary>代码是否为空</summary>
    public bool IsEmpty => CharCount == 0;
}
