# ZZW Code Teacher — 智能代码教练(全 H# 实现)

> 一个**教学型 OJ + AI 辅助 IDE**,全部用 H# 语言开发。
> 客户端使用 H# 自带的 HwdUI 桌面框架,服务端使用 H# net_module 实现 HTTP API。
> AI 只做"辅助学习"(提示 / 解释 / 启发),绝不替学员写代码。

---

## 项目定位

| 角色 | 形态 | 入口 |
|------|------|------|
| **学员 (Learner)** | 桌面 IDE(基于 HwdUI) | `main_client.hto` |
| **管理员 / 老师 (Admin)** | 桌面管理台(基于 HwdUI) | `main_admin.hto` |
| **服务端 (Server)** | H# HTTP API 后台 | `main_server.hto` |

学员与管理员共用同一个 H# 服务,客户端通过 Token 区分身份。

---

## 核心原则

1. **AI 只做"教练",不做"代写"**
   - 学员提交代码失败时,AI 只能给出"定位 + 提示方向",严禁输出可直接粘贴的正确代码
   - 学员请求"帮我写"时,AI 必须拒绝并提示"请自己尝试,我可以提示思路"
2. **代码沙箱执行**
   - 学员提交 → 服务端用 H# 解释器(或 `hsvm`)在受限目录、超时、内存上限下运行
   - 与样例输入对比输出,记录通过/失败/超时/错误
3. **教学 OJ 闭环**
   - 题目 → 提交 → 自动评测 → 排行榜 → 错题本 → AI 针对性讲解

---

## 目录结构

```
zzw-code-teacher/
├── README.md                     ← 本文件
├── main_server.hto               ← 服务端入口
├── main_client.hto               ← 学员端入口
├── main_admin.hto                ← 管理端入口
│
├── shared/                       ← 共享模块(客户端/服务端/管理端共用)
│   ├── models.hto                ← 数据模型(User/Problem/Submission/Course/...)
│   ├── storage.hto               ← 基于 JSON 文件的存储抽象
│   ├── http_client.hto           ← HTTP 客户端封装(基于 net_module)
│   ├── http_server.hto           ← 简易 HTTP 路由/分发(基于 socket 原语)
│   ├── ai_client.hto             ← OpenAI 兼容 API 客户端 + 提示模板
│   ├── judge.hto                 ← 评测引擎(执行 H# 源码,对比输出)
│   ├── auth.hto                  ← 密码哈希 + Token 生成/校验
│   ├── json_utils.hto            ← JSON 序列化/反序列化
│   └── highlighter.hto           ← H# 语法高亮(token → 颜色映射)
│
├── server/                       ← 服务端
│   ├── server.hto                ← 启动 + 路由注册
│   ├── routes_auth.hto           ← 登录/注册/Token
│   ├── routes_problem.hto        ← 题目 CRUD(学员只读,管理员可写)
│   ├── routes_submission.hto     ← 提交代码 + 拉取结果
│   ├── routes_ai.hto             ← AI 提示 / 错误解释
│   ├── routes_user.hto           ← 学员: 个人信息 / 错题 / 进度
│   └── routes_admin.hto          ← 管理员: 用户/题目/课程/统计
│
├── client/                       ← 学员端(桌面 IDE)
│   ├── login_window.hto          ← 登录窗口
│   ├── main_ide.hto              ← 主 IDE 窗口(三栏)
│   ├── problem_browser.hto       ← 左侧题目浏览器
│   ├── code_editor.hto           ← 中央代码编辑器(行号 + 语法高亮)
│   ├── runner_panel.hto          ← 底部运行/评测输出
│   ├── ai_chat_panel.hto         ← 右侧 AI 教练对话框
│   ├── profile_window.hto        ← 学习画像窗口
│   └── ide_theme.hto             ← IDE 主题(配色/字体)
│
├── admin/                        ← 管理端
│   ├── login_window.hto          ← 管理员登录
│   ├── dashboard.hto             ← 仪表盘(用户数/提交数/通过率)
│   ├── user_mgmt.hto             ← 用户管理
│   ├── problem_mgmt.hto          ← 题目管理(增删改 + 测试数据)
│   ├── review_panel.hto          ← 提交审核 + AI 提示词管理
│   ├── course_mgmt.hto           ← 课程 / 班级管理
│   └── settings.hto              ← 系统设置(AI Key / 评测超时)
│
└── data/                         ← 运行时数据
    ├── users.json                ← 用户表
    ├── problems.json             ← 题目表
    ├── submissions.json          ← 提交记录
    ├── courses.json              ← 课程
    ├── progress.json             ← 学习进度
    ├── config.json               ← 服务端配置
    └── uploads/                  ← 学员代码归档
```

---

## 启动流程

```bash
# 1. 启动 HTTP 服务端(通过 Python 桥接,默认 127.0.0.1:8765)
#    桥接层负责把 HTTP 请求转成 stdin/stdout JSON 协议,再喂给 H# 调度进程
python3 python_host/server_runner.py 8765

# 2. 启动学员 IDE
python3 hsharp.py main_client.hto

# 3. 启动管理端
python3 hsharp.py main_admin.hto
```

> 服务端**必须**通过 `python_host/server_runner.py` 启动,而**不能**直接
> `python3 hsharp.py main_server.hto`。`main_server_dispatch.hto` 走的是
> stdin/stdout 协议,需要 Python 桥接层把它暴露成 HTTP。

### 桥接层协议

| 方向 | 格式 | 说明 |
|------|------|------|
| 桥接 → H# | `{"id":N,"method":"GET","path":"/api/...","headers":{...},"body":"..."}\n` | 每行一个 JSON 请求 |
| H# → 桥接 | `RESP {"id":N,"status":200,"body":"...","content_type":"..."}\n` | 响应带原 `id` 用于路由回包 |
| 启动握手 | H# 进程启动后向 stdout 写 `READY\n`,桥接层收到后才开始转交请求 |

---


## 数据流

```
┌──────────┐    HTTP+JSON    ┌──────────┐    子进程    ┌────────┐
│ 学员 IDE │ ──────────────▶ │ H# Server│ ──────────▶ │ hsvm   │
│  HwdUI   │ ◀────────────── │          │ ◀────────── │ 评测   │
└──────────┘                 └─────┬────┘             └────────┘
       │                            │
       │ AI 提示请求                 │ AI 提示转发
       ▼                            ▼
┌──────────┐                 ┌──────────────┐
│  AI 对话 │ ◀───────────── │ OpenAI 兼容  │
│  面板    │   SSE/流式      │  API(用户    │
└──────────┘                 │  配置 Key)  │
                              └──────────────┘
```

---

## 已实现模块

- [x] 数据模型 + JSON 存储
- [x] 简易 HTTP 服务(基于 socket)
- [x] HTTP 客户端(基于 net_module)
- [x] OpenAI 兼容 AI 客户端(流式)
- [x] 学员 IDE(题目浏览 / 代码编辑 / 运行 / 评测 / AI 提示)
- [x] 管理员台(用户 / 题目 / 审核 / 仪表盘)
- [x] H# 语法高亮
- [x] 评测引擎(子进程 hsvm + 超时)

---

## 后续 TODO

- [ ] 实时代码协作(WebSocket)
- [ ] 代码 Diff 视图
- [ ] 错题本导出 PDF
- [ ] 学习画像图谱可视化
- [ ] 多语言学员(暂时只支持 H#)
