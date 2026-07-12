using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using ZZW.CodeTeacher.Client.Services;
using ZZW.CodeTeacher.Domain.Enums;

namespace ZZW.CodeTeacher.Client.ViewModels;

/// <summary>右侧 AI 教练面板。
/// 支持多轮上下文(历史一起发)、按题目保留历史(切题不丢)、流式输出(打字机)、对话导出。</summary>
#pragma warning disable CA1001 // _streamCts 持有可释放字段,但 VM 生命周期与应用相同,实现 IDisposable 属过度设计
public partial class AiChatPanelViewModel : ViewModelBase
{
    private readonly AiService _ai;

    [ObservableProperty]
    private string _currentProblemId = "";

    [ObservableProperty]
    private string _currentCode = "";

    [ObservableProperty]
    private string? _lastError;

    [ObservableProperty]
    private string _userInput = "";

    [ObservableProperty]
    private bool _isThinking;

    /// <summary>AI 是否已配置可用(绑定到 UI:未配置时显示"去设置"提示)</summary>
    [ObservableProperty]
    private bool _isAiAvailable;

    /// <summary>未配置时的提示文案</summary>
#pragma warning disable CA1822
    public string UnavailableHint => "AI 未接入 — 点击下方「AI 设置」按钮,接入飞书智能体 / 豆包 / OpenAI";
#pragma warning restore CA1822

    /// <summary>当前教学语言(由 MainIdeViewModel 同步;决定 AI prompt 模板)</summary>
    public SupportedLanguage CurrentLanguage { get; private set; } = SupportedLanguage.Python;

    /// <summary>当前题目对应的对话历史(供 UI 绑定显示)</summary>
    public ObservableCollection<ChatMessage> History { get; } = new();

    /// <summary>按题目 ID 保留的多轮上下文消息(role/content,发给 AI 用)</summary>
    private readonly Dictionary<string, List<AiService.ChatMessage>> _contextByProblem = new();

    /// <summary>当前流式请求的取消令牌(用于中途取消)</summary>
    private CancellationTokenSource? _streamCts;

    public AiChatPanelViewModel(AiService ai)
    {
        _ai = ai;
        IsAiAvailable = _ai.IsAvailable;
        _ai.SettingsChanged += (_, _) => IsAiAvailable = _ai.IsAvailable;
    }

    /// <summary>切换题目上下文:恢复该题的历史(若有),否则初始化系统提示。</summary>
    public void SetContext(string problemId, string code)
    {
        // 流式中切换题目:先取消当前请求
        _streamCts?.Cancel();

        CurrentProblemId = problemId;
        CurrentCode = code;

        History.Clear();
        if (_contextByProblem.TryGetValue(problemId, out var ctx) && ctx.Count > 0)
        {
            // 恢复历史:把上下文消息渲染到 UI(系统消息不显示在 UI,只显示 user/assistant)
            foreach (var m in ctx)
            {
                if (m.Role == "user") History.Add(new ChatMessage("你", m.Content, false));
                else if (m.Role == "assistant") History.Add(new ChatMessage("教练", m.Content, true));
            }
        }
        else
        {
            // 新题目:初始化上下文(系统提示)
            _contextByProblem[problemId] = new List<AiService.ChatMessage>
            {
                new(BuildSystemPrompt(), "system")
            };
            History.Add(new ChatMessage("系统", BuildSystemPrompt(), false));
        }
    }

    /// <summary>设置当前语言,并刷新系统提示(若已有上下文)</summary>
    public void SetLanguage(SupportedLanguage language)
    {
        if (CurrentLanguage == language && History.Count > 0) return;
        CurrentLanguage = language;
        if (!string.IsNullOrEmpty(CurrentProblemId))
        {
            // 更新该题上下文的系统提示(首位)
            if (_contextByProblem.TryGetValue(CurrentProblemId, out var ctx))
            {
                var sys = BuildSystemPrompt();
                if (ctx.Count > 0 && ctx[0].Role == "system")
                    ctx[0] = new AiService.ChatMessage(sys, "system");
                else
                    ctx.Insert(0, new AiService.ChatMessage(sys, "system"));
            }
            // UI 顶部插入新的系统提示(不破坏已有对话)
            History.Insert(0, new ChatMessage("系统", BuildSystemPrompt(), false));
        }
    }

    public void SetLastError(string? error) => LastError = error;

    /// <summary>按当前语言生成 AI 教练系统提示(只给思路不写答案)</summary>
    private string BuildSystemPrompt()
    {
        var langName = CurrentLanguage.DisplayName();
        var style = CurrentLanguage switch
        {
            SupportedLanguage.Python => "遵循 PEP 8,优先使用标准库与推导式;强调可读性",
            SupportedLanguage.JavaScript => "使用 ES6+ 语法,注意异步与作用域;避免全局污染",
            SupportedLanguage.TypeScript => "强调类型安全,优先用 interface/type 而非 any",
            SupportedLanguage.Java => "遵循 Effective Java;类与方法的职责单一;注意泛型与异常",
            SupportedLanguage.C => "注意内存与指针安全;检查返回值;避免缓冲区溢出",
            SupportedLanguage.Cpp => "优先 RAII 与 STL;避免裸 new/delete;注意移动语义",
            SupportedLanguage.CSharp => "使用 LINQ 与模式匹配;遵循 .NET 命名规范;注意可空引用",
            SupportedLanguage.Go => "简洁显式;组合优于继承;错误必须检查;gofmt 风格",
            SupportedLanguage.Rust => "充分利用所有权与借用;优先 ? 传播错误;避免 unsafe",
            SupportedLanguage.Ruby => "Ruby 之道:优雅与表达力优先;块与迭代器是核心",
            SupportedLanguage.PHP => "PSR 风格;注意类型声明;避免 SQL 注入与 XSS",
            SupportedLanguage.Swift => "可选类型与值类型优先;协议导向编程;避免强制解包",
            SupportedLanguage.Kotlin => "空安全与表达式优先;优先 data class 与扩展函数",
            SupportedLanguage.Scala => "函数式优先;不可变数据;善用模式匹配与 case class",
            SupportedLanguage.HSharp => "H# 语法:let 声明、print 输出;思路简洁直接",
            _ => "通用编程最佳实践"
        };
        return $"💡 我是 {langName} AI 教练,只给思路不写答案。{style}。点击上方按钮可请求提示/解释/审查。";
    }

    [RelayCommand]
    private async Task GetHintAsync()
    {
        if (string.IsNullOrEmpty(CurrentProblemId))
        {
            SetStatus("请先选择题再请求 AI 提示");
            return;
        }
        AppendUser("[请求思路提示]");
        var userMsg = $"当前语言: {CurrentLanguage}\n题目ID: {CurrentProblemId}\n学生代码:\n```\n{CurrentCode}\n```\n错误: {LastError ?? "(无)"}\n\n请给出这道题的解题思路提示,不要直接给答案。";
        await StreamAsync(userMsg, "铁律:只给思路和方向,绝不直接写出完整答案代码。用引导式提问启发学生。");
    }

    [RelayCommand]
    private async Task ExplainErrorAsync()
    {
        if (string.IsNullOrEmpty(CurrentProblemId))
        {
            SetStatus("请先选择题再请求 AI 解释");
            return;
        }
        AppendUser("[请求错误解释]");
        var userMsg = $"当前语言: {CurrentLanguage}\n学生代码:\n```\n{CurrentCode}\n```\n报错信息:\n{LastError ?? "(无)"}\n\n请解释这个错误的含义、产生原因,并提示如何修复,但不要直接写出完整答案。";
        await StreamAsync(userMsg, "铁律:解释错误原因与定位方法,不要直接给出修正后的完整代码,可以指出哪一行哪一类问题。");
    }

    [RelayCommand]
    private async Task ReviewCodeAsync()
    {
        if (string.IsNullOrEmpty(CurrentProblemId))
        {
            SetStatus("请先选择题再请求 AI 审查");
            return;
        }
        AppendUser("[请求代码审查]");
        var userMsg = $"当前语言: {CurrentLanguage}\n请审查以下代码并给出改进建议:\n```\n{CurrentCode}\n```\n\n从可读性、边界条件、性能、语言风格四个维度简短点评。";
        await StreamAsync(userMsg, "铁律:审查代码质量(可读性/边界/性能/风格),指出问题与改进方向,但不要直接重写整段代码。");
    }

    [RelayCommand]
    private async Task SendFreeChatAsync()
    {
        if (string.IsNullOrWhiteSpace(UserInput)) return;
        var msg = UserInput;
        AppendUser(msg);
        UserInput = "";
        await StreamAsync(msg, "你是编程学习助手,回答简洁,优先启发而非代写。");
    }

    /// <summary>停止当前流式生成(若正在生成)</summary>
    [RelayCommand]
    private void StopStreaming()
    {
        _streamCts?.Cancel();
        IsThinking = false;
    }

    /// <summary>导出当前题目对话为 Markdown 文本(返回内容,由 View 触发文件保存)</summary>
    public string ExportMarkdown()
    {
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"# AI 教练对话记录");
        sb.AppendLine(FormattableString.Invariant($"题目: {CurrentProblemId}    语言: {CurrentLanguage.DisplayName()}"));
        sb.AppendLine(FormattableString.Invariant($"导出时间: {DateTime.Now:yyyy-MM-dd HH:mm}"));
        sb.AppendLine();
        foreach (var m in History)
        {
            if (m.Role == "系统" && History.IndexOf(m) > 0) continue; // 只保留首条系统提示
            sb.AppendLine(FormattableString.Invariant($"## {m.Role}"));
            sb.AppendLine(m.Body);
            sb.AppendLine();
        }
        return sb.ToString();
    }

    /// <summary>核心:把历史上下文 + 新 user 消息发给 AI,流式接收并实时更新 UI。
    /// 完成后把完整 assistant 回复写回该题上下文(实现多轮记忆)。</summary>
    private async Task StreamAsync(string userMessage, string extraRule)
    {
        if (!IsAiAvailable)
        {
            AppendAssistant("[AI 未配置] 请先在「AI 设置」中接入飞书智能体 / 豆包 / OpenAI。");
            return;
        }
        if (string.IsNullOrEmpty(CurrentProblemId) || !_contextByProblem.ContainsKey(CurrentProblemId))
        {
            // 兜底:无题目上下文时用临时上下文
            SetContext(CurrentProblemId.Length > 0 ? CurrentProblemId : "_scratch_", CurrentCode);
        }

        var ctx = _contextByProblem[CurrentProblemId];

        // 追加 user 消息到上下文
        ctx.Add(new AiService.ChatMessage(userMessage, "user"));

        // 创建一条空的 assistant 消息,流式追加
        var assistantMsg = new ChatMessage("教练", "", true);
        History.Add(assistantMsg);
        var assistantSb = new System.Text.StringBuilder();

        _streamCts?.Cancel();
        _streamCts = new CancellationTokenSource();

        try
        {
            IsThinking = true;
            await foreach (var delta in _ai.AskStreamAsync(ctx, _streamCts.Token))
            {
                assistantSb.Append(delta);
                assistantMsg.Body = assistantSb.ToString();
            }
            if (assistantSb.Length == 0)
                assistantMsg.Body = "(无响应)";
        }
        catch (OperationCanceledException)
        {
            if (assistantSb.Length == 0)
            {
                History.Remove(assistantMsg);
                ctx.RemoveAt(ctx.Count - 1); // 回滚 user 消息
            }
            else
            {
                assistantMsg.Body = assistantSb + "\n\n[已停止]";
            }
        }
        catch (ApiException ex)
        {
            assistantMsg.Body = $"[AI 服务异常 {ex.StatusCode}] {ex.Body}";
            ctx.RemoveAt(ctx.Count - 1); // 出错回滚 user 消息,避免污染上下文
        }
        catch (Exception ex)
        {
            assistantMsg.Body = "[AI 暂时不可用] " + ex.Message;
            ctx.RemoveAt(ctx.Count - 1);
        }
        finally
        {
            IsThinking = false;
            // 成功:把 assistant 完整回复加入上下文(多轮记忆)
            if (!string.IsNullOrEmpty(assistantSb.ToString()) && ctx.Count > 0 && ctx[^1].Role == "user")
            {
                ctx.Add(new AiService.ChatMessage(assistantMsg.Body, "assistant"));
            }
        }
    }

    private void AppendUser(string text) => History.Add(new ChatMessage("你", text, false));
    private void AppendAssistant(string text) => History.Add(new ChatMessage("教练", text, true));
}

/// <summary>聊天消息(UI 绑定用)。Body 可在流式过程中被更新并通知 UI。</summary>
public sealed class ChatMessage : ObservableObject
{
    public string Role { get; }
    public bool IsAssistant { get; }
    public string Prefix => Role + ":";

    private string _body = "";
    public string Body
    {
        get => _body;
        set { _body = value; OnPropertyChanged(); }
    }

    public ChatMessage(string role, string text, bool isAssistant)
    {
        Role = role;
        _body = text;
        IsAssistant = isAssistant;
    }
}
