namespace ZZW.CodeTeacher.Infrastructure.Persistence;

using System.Linq;
using Microsoft.EntityFrameworkCore;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Infrastructure.Authentication;

/// <summary>
/// 数据库种子初始化器 —— 启动时确保存在默认账户与经典 OJ 题目(含测试用例)。
/// 幂等:仅当对应 Code/Username 不存在时插入,不覆盖已有数据。
/// </summary>
public static class DbSeeder
{
    /// <summary>执行种子初始化(幂等)。</summary>
    public static async Task SeedAsync(CodeTeacherDbContext db, CancellationToken ct = default)
    {
        await db.Database.EnsureCreatedAsync(ct);
        await SeedUsersAsync(db, ct);
        await SeedProblemsAsync(db, ct);
        await db.SaveChangesAsync(ct);
    }

    // ── 默认账户 ──────────────────────────────────────────────
    private static async Task SeedUsersAsync(CodeTeacherDbContext db, CancellationToken ct)
    {
        var hasher = new PasswordHasher();
        var users = new[]
        {
            ("teacher1", "teacher@example.com", "Teacher One", UserRole.Admin, "teacher12345"),
            ("student1", "student@example.com", "Student One", UserRole.Student, "student12345"),
        };

        foreach (var (username, email, displayName, role, password) in users)
        {
            if (await db.Users.AnyAsync(u => u.Username == username, ct)) continue;
            db.Users.Add(User.Create(username, email, hasher.Hash(password), displayName, role));
        }
    }

    // ── 经典 OJ 题目 ──────────────────────────────────────────
    private static async Task SeedProblemsAsync(CodeTeacherDbContext db, CancellationToken ct)
    {
        var existingCodes = await db.Problems.Select(p => p.Code).ToListAsync(ct);
        var toAdd = Problems.Where(p => !existingCodes.Contains(p.Code)).ToList();
        if (toAdd.Count == 0) return;

        foreach (var p in toAdd)
        {
            db.Problems.Add(p);
            // AddTestCase 已在工厂里填充 _testCases,EF 会级联插入
        }
    }

    // 题目工厂:每道题含样例 + 隐藏测试用例
    private static readonly IReadOnlyList<Problem> Problems = new[]
    {
        // P001 — A+B Problem(基础入门)
        BuildProblem(
            "P001", "A+B Problem",
            "读取两个整数 a 与 b,输出它们的和。\n\n**输入格式**\n一行,两个空格分隔的整数 a 与 b。\n\n**输出格式**\n一行,一个整数,表示 a + b。",
            DifficultyLevel.Easy, 1000, 65536,
            "a, b = map(int, input().split())\nprint(a + b)",
            new[] { "入门", "基础" },
            new[]
            {
                ("1 2", "3", true),
                ("0 0", "0", false),
                ("-5 5", "0", false),
                ("100 200", "300", false),
                ("999999 1", "1000000", false),
            }),

        // P002 — 求 n 的阶乘
        BuildProblem(
            "P002", "阶乘",
            "给定一个非负整数 n,求 n!(n 的阶乘)。规定 0! = 1。\n\n**输入格式**\n一行,一个非负整数 n(0 ≤ n ≤ 20)。\n\n**输出格式**\n一行,一个整数,表示 n!。",
            DifficultyLevel.Easy, 1000, 65536,
            "n = int(input())\nresult = 1\nfor i in range(1, n + 1):\n    result *= i\nprint(result)",
            new[] { "数学", "循环" },
            new[]
            {
                ("0", "1", true),
                ("5", "120", false),
                ("1", "1", false),
                ("10", "3628800", false),
                ("3", "6", true),
            }),

        // P003 — 判断奇偶性
        BuildProblem(
            "P003", "判断奇偶性",
            "给定一个整数 n,判断它是奇数还是偶数。\n\n**输入格式**\n一行,一个整数 n。\n\n**输出格式**\n输出 `odd`(奇数)或 `even`(偶数)。",
            DifficultyLevel.Easy, 1000, 65536,
            "n = int(input())\nprint('even' if n % 2 == 0 else 'odd')",
            new[] { "入门", "条件判断" },
            new[]
            {
                ("4", "even", true),
                ("7", "odd", false),
                ("0", "even", false),
                ("-3", "odd", false),
                ("100", "even", false),
            }),

        // P004 — 最大值与最小值
        BuildProblem(
            "P004", "最大值与最小值",
            "给定 n 个整数,求其中的最大值与最小值之差。\n\n**输入格式**\n第一行一个整数 n。第二行 n 个空格分隔的整数。\n\n**输出格式**\n一行,一个整数,表示最大值减最小值。",
            DifficultyLevel.Easy, 1000, 65536,
            "n = int(input())\nnums = list(map(int, input().split()))\nprint(max(nums) - min(nums))",
            new[] { "数组", "基础" },
            new[]
            {
                ("5\n1 2 3 4 5", "4", true),
                ("3\n10 10 10", "0", false),
                ("1\n42", "0", false),
                ("4\n-5 -1 -9 -3", "8", false),
                ("6\n100 1 50 25 75 0", "100", false),
            }),

        // P005 — 斐波那契数列第 n 项
        BuildProblem(
            "P005", "斐波那契数列",
            "斐波那契数列定义:F(1)=1, F(2)=1, F(n)=F(n-1)+F(n-2)。给定 n,求 F(n)。\n\n**输入格式**\n一行,一个正整数 n(1 ≤ n ≤ 40)。\n\n**输出格式**\n一行,一个整数,表示 F(n)。",
            DifficultyLevel.Medium, 1000, 65536,
            "n = int(input())\na, b = 1, 1\nfor _ in range(n - 1):\n    a, b = b, a + b\nprint(a)",
            new[] { "递推", "数列" },
            new[]
            {
                ("1", "1", true),
                ("10", "55", false),
                ("2", "1", false),
                ("20", "6765", false),
                ("6", "8", true),
            }),

        // P006 — 数组求和
        BuildProblem(
            "P006", "数组求和",
            "给定 n 个整数,求它们的和。\n\n**输入格式**\n第一行一个整数 n。第二行 n 个空格分隔的整数。\n\n**输出格式**\n一行,一个整数,表示所有元素之和。",
            DifficultyLevel.Easy, 1000, 65536,
            "n = int(input())\nnums = list(map(int, input().split()))\nprint(sum(nums))",
            new[] { "数组", "入门" },
            new[]
            {
                ("3\n1 2 3", "6", true),
                ("1\n5", "5", false),
                ("4\n-1 -2 -3 -4", "-10", false),
                ("2\n0 0", "0", false),
                ("5\n10 20 30 40 50", "150", false),
            }),

        // P007 — 字符串反转
        BuildProblem(
            "P007", "字符串反转",
            "给定一个字符串,将其反转后输出。\n\n**输入格式**\n一行,一个字符串(长度不超过 1000,不含空格)。\n\n**输出格式**\n一行,反转后的字符串。",
            DifficultyLevel.Easy, 1000, 65536,
            "s = input()\nprint(s[::-1])",
            new[] { "字符串", "基础" },
            new[]
            {
                ("hello", "olleh", true),
                ("abc", "cba", false),
                ("a", "a", false),
                ("12345", "54321", false),
                ("racecar", "racecar", true),
            }),

        // P008 — 统计元音字母
        BuildProblem(
            "P008", "统计元音字母",
            "给定一个字符串(仅含小写字母),统计其中元音字母(a, e, i, o, u)的个数。\n\n**输入格式**\n一行,一个字符串。\n\n**输出格式**\n一行,一个整数,表示元音字母的个数。",
            DifficultyLevel.Easy, 1000, 65536,
            "s = input()\nvowels = set('aeiou')\nprint(sum(1 for c in s if c in vowels))",
            new[] { "字符串", "计数" },
            new[]
            {
                ("hello", "2", true),
                ("aeiou", "5", false),
                ("xyz", "0", false),
                ("programming", "3", false),
                ("queue", "4", true),
            }),
    };

    /// <summary>构造题目(含测试用例)。支持全部 15 种语言。</summary>
    private static Problem BuildProblem(
        string code, string title, string description,
        DifficultyLevel difficulty, int timeLimitMs, int memoryLimitKb,
        string template, string[] tags,
        IReadOnlyList<(string Input, string Expected, bool IsSample)> cases)
    {
        var langs = new[]
        {
            SupportedLanguage.Python, SupportedLanguage.JavaScript,
            SupportedLanguage.TypeScript, SupportedLanguage.Java,
            SupportedLanguage.C, SupportedLanguage.Cpp,
            SupportedLanguage.CSharp, SupportedLanguage.Go,
            SupportedLanguage.Rust, SupportedLanguage.Ruby,
            SupportedLanguage.PHP, SupportedLanguage.Swift,
            SupportedLanguage.Kotlin, SupportedLanguage.Scala,
        };
        var p = Problem.Create(code, title, description, difficulty,
            timeLimitMs, memoryLimitKb, template, tags, langs);
        foreach (var (input, expected, isSample) in cases)
            p.AddTestCase(input, expected, isSample);
        return p;
    }
}
