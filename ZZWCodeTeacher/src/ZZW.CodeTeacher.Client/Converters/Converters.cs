using System.Globalization;
using Avalonia.Data.Converters;
using Avalonia.Media;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.Converters;

/// <summary>对象非 null → true,null → false</summary>
public sealed class NullToBoolConverter : IValueConverter
{
    public static readonly NullToBoolConverter Instance = new();
    /// <summary>反转:null → true,非 null → false(用于"空态占位"显示)</summary>
    public static readonly NullToBoolConverter InvertedInstance = new() { _inverted = true };
    private bool _inverted;

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        var hasValue = value is not null;
        return _inverted ? !hasValue : hasValue;
    }
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>集合 Count == 0 → true(空状态显示)</summary>
public sealed class CountToBoolConverter : IValueConverter
{
    public static readonly CountToBoolConverter Instance = new();
    /// <summary>反转:Count != 0 → true(用于"有数据/有未读"时显示 Badge)</summary>
    public static readonly CountToBoolConverter InvertedInstance = new() { _inverted = true };

    private bool _inverted;

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        var isEmpty = value switch
        {
            int n => n == 0,
            System.Collections.ICollection c => c.Count == 0,
            _ => true
        };
        return _inverted ? !isEmpty : isEmpty;
    }
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>整数 → 柱状图宽度(每单位 12px,最小 2px)</summary>
public sealed class CountToWidthConverter : IValueConverter
{
    public static readonly CountToWidthConverter Instance = new();
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is int n) return Math.Max(2, n * 12);
        return 2;
    }
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>提交状态 → 颜色</summary>
public sealed class StatusToColorConverter : IValueConverter
{
    public static readonly StatusToColorConverter Instance = new();
    public static readonly IBrush Accepted = new SolidColorBrush(Color.FromRgb(0x16, 0xA3, 0x4A));
    public static readonly IBrush Wrong = new SolidColorBrush(Color.FromRgb(0xDC, 0x26, 0x26));
    public static readonly IBrush Warn = new SolidColorBrush(Color.FromRgb(0xEA, 0x58, 0x0C));
    public static readonly IBrush Info = new SolidColorBrush(Color.FromRgb(0x6B, 0x72, 0x80));

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is SubmissionStatus s)
        {
            return s switch
            {
                SubmissionStatus.Accepted => Accepted,
                SubmissionStatus.WrongAnswer or SubmissionStatus.CompileError => Wrong,
                SubmissionStatus.TimeLimitExceeded or SubmissionStatus.RuntimeError => Warn,
                _ => Info
            };
        }
        return Info;
    }
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>bool → "通过"/"失败"</summary>
public sealed class BoolToPassFailTextConverter : IValueConverter
{
    public static readonly BoolToPassFailTextConverter Instance = new();
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        => value is true ? "通过" : "失败";
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>bool → 绿色/红色画刷</summary>
public sealed class BoolToPassFailBrushConverter : IValueConverter
{
    public static readonly BoolToPassFailBrushConverter Instance = new();
    private static readonly IBrush Pass = new SolidColorBrush(Color.FromRgb(0x16, 0xA3, 0x4A));
    private static readonly IBrush Fail = new SolidColorBrush(Color.FromRgb(0xDC, 0x26, 0x26));

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        => value is true ? Pass : Fail;
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>bool → 测试结果背景色(true=绿/false=红)</summary>
public sealed class BoolToTestResultBrushConverter : IValueConverter
{
    public static readonly BoolToTestResultBrushConverter Instance = new();
    private static readonly IBrush Ok = new SolidColorBrush(Color.FromRgb(0x16, 0xA3, 0x4A));
    private static readonly IBrush Fail = new SolidColorBrush(Color.FromRgb(0xDC, 0x26, 0x26));

    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        => value is true ? Ok : Fail;
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>难度等级(DifficultyLevel?)→ 中文显示(null=全部难度)。</summary>
public sealed class DifficultyToStringConverter : IValueConverter
{
    public static readonly DifficultyToStringConverter Instance = new();
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        => value switch
        {
            null => "全部难度",
            DifficultyLevel.Easy => "简单",
            DifficultyLevel.Medium => "中等",
            DifficultyLevel.Hard => "困难",
            _ => value.ToString()
        };
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>用户角色 → 中文显示。</summary>
public sealed class RoleToStringConverter : IValueConverter
{
    public static readonly RoleToStringConverter Instance = new();
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        => value switch
        {
            UserRole.Student => "学员",
            UserRole.Teacher => "教师",
            UserRole.Admin => "管理员",
            _ => value?.ToString() ?? ""
        };
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>字符串相等比较(用于 RadioButton 单选切换:7d/30d/90d、scope=all/week/month)。
/// Convert: value 与 parameter 相等返回 true;ConvertBack: value=true 时回写 parameter,false 时跳过。</summary>
public sealed class StringEqualsConverter : IValueConverter
{
    public static readonly StringEqualsConverter Instance = new();
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        => string.Equals(value?.ToString(), parameter?.ToString(), StringComparison.OrdinalIgnoreCase);

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => value is true ? parameter : Avalonia.AvaloniaProperty.UnsetValue;
}

/// <summary>SupportedLanguage 枚举 → 显示名(如 Python / C++ / H#),用于 ComboBox 绑定。</summary>
public sealed class LanguageDisplayNameConverter : IValueConverter
{
    public static readonly LanguageDisplayNameConverter Instance = new();
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        => value is SupportedLanguage lang ? lang.DisplayName() : value?.ToString();
    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
