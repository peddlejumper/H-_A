using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>代码编辑器(中心上半)ViewModel。绑定到原生 TextBox(等宽字体)。</summary>
#pragma warning disable CA1001 // _saveCts 持有可释放字段,但 VM 生命周期与应用相同,实现 IDisposable 属过度设计
public partial class CodeEditorViewModel : ViewModelBase
{
    private readonly DraftStore? _drafts;
    private readonly AuthState? _auth;
    private readonly AppSettingsService? _settings;
    private Guid _currentProblemId;
    private CancellationTokenSource? _saveCts;

    [ObservableProperty]
    private string _code = "";

    [ObservableProperty]
    private SupportedLanguage _language = SupportedLanguage.Python;

    [ObservableProperty]
    private string _title = "(未选择题目)";

    [ObservableProperty]
    private string _description = "";

    [ObservableProperty]
    private string _tags = "";

    [ObservableProperty]
    private string _sampleInput = "";

    [ObservableProperty]
    private string _sampleOutput = "";

    /// <summary>编辑器字号(可调节,默认 13;初值从 AppSettings 读取)</summary>
    [ObservableProperty]
    private int _fontSize = 13;

    /// <summary>Tab 宽度(转空格数,默认 4;初值从 AppSettings 读取)</summary>
    [ObservableProperty]
    private int _tabWidth = 4;

    /// <summary>当前代码行数(实时统计,绑定到状态栏)</summary>
    [ObservableProperty]
    private int _lineCount;

    /// <summary>当前代码字符数(实时统计,绑定到状态栏)</summary>
    [ObservableProperty]
    private int _charCount;

    /// <summary>当前题目支持的语言(供下拉绑定)</summary>
    public ObservableCollection<SupportedLanguage> AvailableLanguages { get; } = new();

    /// <summary>全部 15 种语言(用于无题时下拉占位)</summary>
    public static IReadOnlyList<SupportedLanguage> AllLanguages { get; } =
        Enum.GetValues<SupportedLanguage>();

    public CodeEditorViewModel() : this(null, null, null) { }

    public CodeEditorViewModel(DraftStore? drafts, AuthState? auth, AppSettingsService? settings)
    {
        _drafts = drafts;
        _auth = auth;
        _settings = settings;

        // 从本地设置读取编辑器默认配置(无设置文件时使用内置默认值)
        if (settings is not null)
        {
            FontSize = settings.GetEditorFontSize();
            TabWidth = settings.GetEditorTabWidth();
            Language = settings.GetDefaultLanguage();
        }

        UpdateStats();
    }

    /// <summary>当前题号(用于导出文件名前缀)</summary>
    public string CurrentProblemCode { get; private set; } = "untitled";

    public void SetProblem(ProblemDto problem)
    {
        _currentProblemId = problem.Id;
        CurrentProblemCode = problem.Code;
        Title = $"{problem.Code} — {problem.Title}";
        Description = problem.Description;
        Tags = problem.Tags.Count > 0 ? string.Join(", ", problem.Tags) : "(无标签)";

        // 刷新可选语言下拉
        AvailableLanguages.Clear();
        foreach (var lang in problem.SupportedLanguages.Count > 0
                     ? problem.SupportedLanguages
                     : AllLanguages)
        {
            AvailableLanguages.Add(lang);
        }
        // 默认选第一个支持的语言(会触发 OnLanguageChanged → 加载草稿或模板)
        Language = AvailableLanguages.Count > 0 ? AvailableLanguages[0] : SupportedLanguage.Python;

        // 兜底:OnLanguageChanged 未覆盖到(如语言未变)时,显式加载一次
        if (string.IsNullOrEmpty(Code) || IsDefaultTemplate(Code))
            LoadCodeForCurrentLanguage(force: true);

        if (problem.Samples.Count > 0)
        {
            var s = problem.Samples[0];
            SampleInput = s.Input;
            SampleOutput = s.Output;
        }
        else
        {
            SampleInput = "";
            SampleOutput = "";
        }

        SetStatus($"已加载题目: {Title} (语言: {Language.DisplayName()})");
    }

    /// <summary>为当前 (problem, language) 加载草稿;无草稿则用模板。force=true 时无视"已有非模板代码"判断。</summary>
    private void LoadCodeForCurrentLanguage(bool force)
    {
        if (_currentProblemId == Guid.Empty) return;

        // 优先加载草稿
        if (_drafts is not null && _auth?.CurrentUser is not null)
        {
            var draft = _drafts.Get(_auth.CurrentUser.Id, _currentProblemId, Language.ToString());
            if (draft is not null)
            {
                Code = draft;
                return;
            }
        }

        // 无草稿:force 时用模板覆盖;否则仅在空/默认模板时替换
        if (force || string.IsNullOrWhiteSpace(Code) || IsDefaultTemplate(Code))
            Code = DefaultTemplate(Language);
    }

    /// <summary>切换语言时:有草稿则恢复草稿;否则空/默认模板时切换到新语言骨架。</summary>
    partial void OnLanguageChanged(SupportedLanguage value)
    {
        LoadCodeForCurrentLanguage(force: false);
        SetStatus($"已切换语言: {value.DisplayName()}");
    }

    /// <summary>代码变化时:更新统计 + 防抖保存草稿(500ms 内无再次输入则写盘)。</summary>
    partial void OnCodeChanged(string value)
    {
        UpdateStats();
        ScheduleDraftSave();
    }

    private void ScheduleDraftSave()
    {
        if (_drafts is null || _auth?.CurrentUser is null || _currentProblemId == Guid.Empty) return;
        _saveCts?.Cancel();
        _saveCts = new CancellationTokenSource();
        var token = _saveCts.Token;
        _ = Task.Run(async () =>
        {
            try
            {
                await Task.Delay(500, token);
                _drafts.Save(_auth.CurrentUser.Id, _currentProblemId, Language.ToString(), Code ?? "");
            }
            catch (OperationCanceledException) { /* 防抖:被新输入取消 */ }
        }, token);
    }

    private void UpdateStats()
    {
        CharCount = Code?.Length ?? 0;
        LineCount = string.IsNullOrEmpty(Code) ? 0 : Code.Count(c => c == '\n') + 1;
    }

    /// <summary>字号 +1(上限 22)</summary>
    [RelayCommand]
    private void ZoomIn() => FontSize = Math.Min(22, FontSize + 1);

    /// <summary>字号 -1(下限 10)</summary>
    [RelayCommand]
    private void ZoomOut() => FontSize = Math.Max(10, FontSize - 1);

    /// <summary>恢复默认字号</summary>
    [RelayCommand]
    private void ZoomReset() => FontSize = 13;

    /// <summary>清空编辑器(确认交给 UI 层;VM 只负责执行)</summary>
    [RelayCommand]
    private void ClearCode()
    {
        Code = "";
        SetStatus("编辑器已清空");
    }

    /// <summary>重置为当前语言的默认模板</summary>
    [RelayCommand]
    private void ResetTemplate()
    {
        Code = DefaultTemplate(Language);
        SetStatus($"已重置为 {Language.DisplayName()} 默认模板");
    }

    public void AppendCode(string snippet)
    {
        Code += snippet;
    }

    /// <summary>判断代码是否仍是某种语言的默认模板(用于切换语言时自动替换)</summary>
    private static bool IsDefaultTemplate(string code)
    {
        var trimmed = code.Trim();
        return AllLanguages.Any(l => trimmed == DefaultTemplate(l).Trim());
    }

    /// <summary>各语言的默认代码骨架(A+B 问题模板)</summary>
    private static string DefaultTemplate(SupportedLanguage lang) => lang switch
    {
        SupportedLanguage.Python => """
            # 读取输入 → 计算 → 输出
            a, b = map(int, input().split())
            print(a + b)
            """,
        SupportedLanguage.JavaScript => """
            // 读取输入 → 计算 → 输出(Node.js)
            const readline = require('readline');
            const rl = readline.createInterface({ input: process.stdin });
            rl.on('line', (line) => {
                const [a, b] = line.split(' ').map(Number);
                console.log(a + b);
            });
            """,
        SupportedLanguage.TypeScript => """
            // 读取输入 → 计算 → 输出(编译为 JS 后用 node 运行)
            const readline = require('readline');
            const rl = readline.createInterface({ input: process.stdin });
            rl.on('line', (line: string) => {
                const [a, b] = line.split(' ').map(Number);
                console.log(a + b);
            });
            """,
        SupportedLanguage.Java => """
            import java.util.Scanner;
            // 读取输入 → 计算 → 输出
            public class main {
                public static void main(String[] args) {
                    Scanner sc = new Scanner(System.in);
                    int a = sc.nextInt(), b = sc.nextInt();
                    System.out.println(a + b);
                }
            }
            """,
        SupportedLanguage.C => """
            #include <stdio.h>
            // 读取输入 → 计算 → 输出
            int main() {
                int a, b;
                scanf("%d %d", &a, &b);
                printf("%d\\n", a + b);
                return 0;
            }
            """,
        SupportedLanguage.Cpp => """
            #include <iostream>
            using namespace std;
            // 读取输入 → 计算 → 输出
            int main() {
                int a, b;
                cin >> a >> b;
                cout << a + b << endl;
                return 0;
            }
            """,
        SupportedLanguage.CSharp => """
            // 读取输入 → 计算 → 输出
            using System;
            var line = Console.ReadLine()!.Split();
            Console.WriteLine(int.Parse(line[0]) + int.Parse(line[1]));
            """,
        SupportedLanguage.Go => """
            package main
            import "fmt"
            // 读取输入 → 计算 → 输出
            func main() {
                var a, b int
                fmt.Scan(&a, &b)
                fmt.Println(a + b)
            }
            """,
        SupportedLanguage.Rust => """
            use std::io::{self, BufRead};
            // 读取输入 → 计算 → 输出
            fn main() {
                let stdin = io::stdin();
                let line = stdin.lock().lines().next().unwrap().unwrap();
                let nums: Vec<i32> = line.split_whitespace()
                    .map(|s| s.parse().unwrap()).collect();
                println!("{}", nums[0] + nums[1]);
            }
            """,
        SupportedLanguage.Ruby => """
            # 读取输入 → 计算 → 输出
            a, b = gets.split.map(&:to_i)
            puts a + b
            """,
        SupportedLanguage.PHP => """
            <?php
            // 读取输入 → 计算 → 输出
            fscanf(STDIN, "%d %d", $a, $b);
            echo $a + $b . PHP_EOL;
            """,
        SupportedLanguage.Swift => """
            import Foundation
            // 读取输入 → 计算 → 输出
            let line = readLine()!
            let nums = line.split(separator: " ").map { Int($0)! }
            print(nums[0] + nums[1])
            """,
        SupportedLanguage.Kotlin => """
            // 读取输入 → 计算 → 输出
            fun main() {
                val (a, b) = readLine()!!.split(" ").map { it.toInt() }
                println(a + b)
            }
            """,
        SupportedLanguage.Scala => """
            // 读取输入 → 计算 → 输出
            object main extends App {
                val nums = scala.io.StdIn.readLine().split(" ").map(_.toInt)
                println(nums(0) + nums(1))
            }
            """,
        SupportedLanguage.HSharp => """"
            // 在下方编写你的 H# 解法
            // 读取输入 → 计算 → 输出结果
            let a = 0;
            let b = 0;
            // ...
            print(a + b);
            """",
        _ => "// 在此编写代码\n"
    };
}
