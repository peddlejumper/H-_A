# ZZW Code Teacher — .NET 10 完整重构方案

> 基于 Clean Architecture（洋葱架构）+ .NET 10 + C# 13 的企业级重构。
> H# 限定为后端控制面板脚本层，前端采用 TREA 风格。

## 目录

1. [架构总览](#1-架构总览)
2. [项目结构](#2-项目结构)
3. [分层设计说明](#3-分层设计说明)
4. [H# 控制面板定位](#4-h-控制面板定位)
5. [.NET 10 新特性应用](#5-net-10-新特性应用)
6. [数据模型设计（DDD）](#6-数据模型设计ddd)
7. [API 端点规范](#7-api-端点规范)
8. [依赖注入与生命周期](#8-依赖注入与生命周期)
9. [中间件管道](#9-中间件管道)
10. [质量保障](#10-质量保障)
11. [运行指南](#11-运行指南)

---

## 1. 架构总览

采用 **洋葱架构（Onion Architecture）**，依赖方向始终从外向内：

```
┌─────────────────────────────────────────────────────┐
│  表示层 & 基础设施层（外层，依赖内层）                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ TREA 前端 │  │  API 层   │  │H# 控制面板│         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       │ REST        │              │ HTTP           │
│       ▼             ▼              ▼                │
│  ┌─────────────────────────────────────────────┐   │
│  │          Application 层（应用服务）           │   │
│  │  CQRS · FluentValidation · AutoMapper       │   │
│  │  Pipeline Behaviors: 验证→日志→异常          │   │
│  └──────────────────────┬──────────────────────┘   │
│                         │ 依赖倒置                   │
│                         ▼                            │
│  ┌─────────────────────────────────────────────┐   │
│  │          Domain 层（领域核心，零依赖）         │   │
│  │  实体 · 值对象 · 领域事件 · 仓储接口          │   │
│  │  Problem / User / Submission 聚合根           │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**核心原则：**
- Domain 层零外部依赖（不引用 EF Core、ASP.NET Core 等任何框架）
- 依赖方向：Infrastructure → Application → Domain（外→内）
- 依赖倒置：Domain 定义仓储接口，Infrastructure 实现

---

## 2. 项目结构

```
ZZWCodeTeacher/
├── Directory.Build.props          # 共享编译配置（C# 13、Nullable、文档注释）
├── Directory.Packages.props       # 中央包版本管理（CPM）
│
├── src/
│   ├── ZZW.CodeTeacher.Domain/              # 领域层（零依赖）
│   │   ├── Entities/          Problem.cs · User.cs（聚合根 + 聚合内实体）
│   │   ├── ValueObjects/      CodeSnapshot.cs · JudgeReport.cs
│   │   ├── Enums/             DifficultyLevel · SubmissionStatus · UserRole
│   │   ├── Events/            IDomainEvent · ProblemCreatedEvent · ...
│   │   ├── Repositories/      IProblemRepository · IUserRepository · IUnitOfWork
│   │   ├── Services/          JudgingService · AuthorizationService（领域服务）
│   │   └── Exceptions/        DomainException · NotFoundException
│   │
│   ├── ZZW.CodeTeacher.Application/         # 应用层
│   │   ├── DTOs/              ProblemDto · UserDto · SubmissionDto · ApiResponse
│   │   ├── Commands/          CreateProblemCommand · LoginCommand · ...
│   │   ├── Queries/           ListProblemsQuery · GetDashboardStatsQuery · ...
│   │   ├── UseCases/          CreateProblemHandler · RegisterHandler · ...
│   │   ├── Validators/        FluentValidation 验证规则
│   │   ├── Behaviors/         LoggingBehavior · ValidationBehavior
│   │   ├── Mappings/          AutoMapper MappingProfile
│   │   ├── Interfaces/        IPasswordHasher · ITokenService · ICurrentUser
│   │   └── DependencyInjection.cs
│   │
│   ├── ZZW.CodeTeacher.Infrastructure/      # 基础设施层
│   │   ├── Persistence/       CodeTeacherDbContext（EF Core Code-First）
│   │   ├── Repositories/      ProblemRepository · UserRepository · UnitOfWork
│   │   ├── Authentication/    JwtTokenService · PasswordHasher（PBKDF2）
│   │   ├── Caching/           MemoryCacheService（System.Threading.Lock）
│   │   ├── Logging/           Serilog 配置
│   │   └── DependencyInjection.cs
│   │
│   ├── ZZW.CodeTeacher.Api/                # 表示层（H# API）
│   │   ├── Controllers/       ProblemsController · UsersController ·
│   │   │                      SubmissionsController · DashboardController ·
│   │   │                      HSharpPanelController
│   │   ├── Middlewares/       GlobalExceptionMiddleware · RequestLoggingMiddleware
│   │   ├── Extensions/        CurrentUserService · ServiceCollectionExtensions
│   │   ├── Program.cs         Minimal Hosting Model 入口
│   │   └── appsettings.json   配置（连接串、JWT、CORS、H# 解释器路径）
│   │
│   ├── ZZW.CodeTeacher.HSharpPanel/        # H# 控制面板
│   │   ├── HSharpScriptRunner.cs   .NET 宿主，调用 H# 解释器进程
│   │   ├── scripts/            health_check.hto · bulk_import_problems.hto ·
│   │   │                       submission_analytics.hto
│   │   ├── rules/             submission_limit.hto（动态规则）
│   │   └── config/            problems_seed.json
│   │
│   └── ZZW.CodeTeacher.Web/               # TREA 风格前端
│       └── wwwroot/
│           ├── index.html     单页应用入口
│           ├── css/trea.css   TREA 设计系统
│           └── js/            api.js（API 客户端）· app.js（视图渲染）
│
├── tests/
│   ├── ZZW.CodeTeacher.Domain.Tests/        领域单元测试
│   ├── ZZW.CodeTeacher.Application.Tests/   应用层测试（NSubstitute mock）
│   └── ZZW.CodeTeacher.Api.IntegrationTests/  集成测试（WebApplicationFactory）
│
└── docs/
    └── REFACTOR_PLAN.md         本文档
```

---

## 3. 分层设计说明

### Domain 层（领域核心）

**职责：** 定义业务实体、值对象、聚合根、领域事件、仓储接口。**零外部依赖**。

| 组件 | 示例 | 说明 |
|------|------|------|
| 聚合根 | `Problem`、`User`、`Submission` | 维护一致性边界，通过工厂方法创建 |
| 值对象 | `CodeSnapshot`、`JudgeReport` | 不可变 `record struct`，按值比较 |
| 领域事件 | `ProblemCreatedEvent` | 聚合根内部收集，基础设施层发布 |
| 仓储接口 | `IProblemRepository` | 定义在领域层，基础设施层实现 |
| 领域服务 | `JudgingService` | 跨聚合无状态业务逻辑 |
| 领域异常 | `DomainException` | 业务规则违反时抛出 |

**聚合根设计要点：**
- 私有 setter，通过方法修改状态（`Update()`、`SetActive()`）
- 工厂方法 `Create()` 封装创建逻辑并校验
- 内部维护 `_domainEvents` 列表

### Application 层（应用服务）

**职责：** 编排业务用例，DTO 转换，请求验证。**不包含业务规则**。

| 组件 | 说明 |
|------|------|
| CQRS 命令 | `CreateProblemCommand` → `CreateProblemHandler` |
| CQRS 查询 | `ListProblemsQuery` → `ListProblemsHandler` |
| Pipeline Behaviors | 验证 → 日志 → 异常（MediatR 管道） |
| Validators | FluentValidation 自动验证每个请求 |
| DTO | 与领域实体解耦的数据传输对象 |
| 接口 | `IPasswordHasher`、`ITokenService`（基础设施实现） |

### Infrastructure 层（基础设施）

**职责：** 实现领域层接口，处理技术细节。

| 组件 | 实现 |
|------|------|
| DbContext | `CodeTeacherDbContext`（EF Core Code-First，SQLite） |
| 仓储 | `ProblemRepository` 等实现 `IProblemRepository` |
| 认证 | `JwtTokenService` + `PasswordHasher`（PBKDF2） |
| 缓存 | `MemoryCacheService`（`.NET 10 System.Threading.Lock`） |
| 日志 | Serilog（控制台 + 滚动文件） |

### API 层（表示层，H# API）

**职责：** 仅包含控制器、中间件、路由定义。**不含任何业务逻辑或 UI 渲染**。

| 组件 | 说明 |
|------|------|
| 控制器 | RESTful 端点，委托给 MediatR |
| 中间件 | 全局异常、请求日志、CORS、限流 |
| 认证 | JWT Bearer + RBAC 角色授权 |
| 版本控制 | `Asp.Versioning`（URL 路径 `/api/v1/`） |
| 文档 | Swagger / OpenAPI 自动生成 |

---

## 4. H# 控制面板定位

H# 在新架构中**不再承担 UI 渲染**，而是作为**后端控制面板脚本层**：

```
┌──────────────┐     HTTP      ┌──────────────┐    Process    ┌─────────────┐
│  .NET API    │ ◄─────────── │  H# 脚本     │ ◄─────────── │ 管理员/定时器 │
│  /panel/run  │              │  (.hto)      │              └─────────────┘
└──────────────┘              └──────────────┘
```

**H# 控制面板职责：**

| 脚本 | 用途 |
|------|------|
| `health_check.hto` | 检查 API 连通性，输出 JSON 健康报告 |
| `bulk_import_problems.hto` | 从 JSON 批量导入题目（初始化数据） |
| `submission_analytics.hto` | 拉取提交数据生成分析报告 |
| `rules/submission_limit.hto` | 动态规则：提交频率限制（.NET 在提交前调用） |

**通信机制：** H# 通过 `http_get`/`http_post` host 函数调用 .NET API；.NET 通过 `HSharpScriptRunner` 启动 Python 解释器执行 H# 脚本。

---

## 5. .NET 10 新特性应用

| 特性 | 应用位置 | 代码示例 |
|------|----------|----------|
| **Primary Constructors** | 所有 Handler、Service、Middleware | `class CreateProblemHandler(IProblemRepository repo, IUnitOfWork uow)` |
| **System.Threading.Lock** | MemoryCacheService | `private readonly System.Threading.Lock _lock = new();` |
| **Enumerable.CountBy** | GetDashboardStatsHandler | `problems.CountBy(p => p.Difficulty)` |
| **Enumerable.AggregateBy** | GetDashboardStatsHandler | `subs.AggregateBy(s => s.UserId, seed, func)` |
| **Enumerable.Order** | GetDashboardStatsHandler | `.Order()` 替代 `OrderBy(x => x)` |
| **JsonIgnoreCondition.WhenWritingNull** | Infrastructure.JsonOptions | `DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull` |
| **自定义缩进字符** | Infrastructure.JsonOptions | `IndentCharacter = ' '`、`IndentSize = 2` |
| **Collection Expression** | 各处初始化 | `Tags = tags?.ToList().AsReadOnly() ?? []` |
| **async Stream EF Core** | 仓储查询 | `AsAsyncEnumerable()` |

---

## 6. 数据模型设计（DDD）

### 聚合根 Problem

```
Problem（聚合根）
├── Id: Guid
├── Code: string (唯一, P001~P99999)
├── Title: string
├── Description: string
├── Difficulty: DifficultyLevel
├── TimeLimitMs / MemoryLimitKb
├── Template: string
├── Tags: IReadOnlyList<string>
├── IsActive: bool
├── TestCases: TestCase[]（聚合内实体）
│   ├── Input / ExpectedOutput
│   ├── IsSample
│   └── Order
└── DomainEvents: List<IDomainEvent>
```

### 聚合根 User

```
User（聚合根）
├── Id: Guid
├── Username / Email (唯一)
├── PasswordHash: string
├── DisplayName
├── Role: UserRole (Student/Teacher/Admin)
├── IsActive / LastLoginAt
└── DomainEvents
```

### 聚合根 Submission

```
Submission（聚合根）
├── Id: Guid
├── ProblemId / UserId
├── Code: CodeSnapshot（值对象）
│   ├── Content / Language
│   └── LineCount / CharCount
├── Status: SubmissionStatus
├── Report: JudgeReport（值对象）
├── Score: int
└── DomainEvents
```

---

## 7. API 端点规范

遵循 RESTful 规范，统一前缀 `/api/v1/`：

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/problems` | 分页查询题目 | 公开 |
| GET | `/problems/{id}` | 题目详情 | 公开 |
| POST | `/problems` | 创建题目 | Teacher/Admin |
| PUT | `/problems/{id}` | 更新题目 | Teacher/Admin |
| DELETE | `/problems/{id}` | 删除题目 | Admin |
| POST | `/problems/{id}/testcases` | 添加测试用例 | Teacher/Admin |
| PATCH | `/problems/{id}/active` | 启用/禁用 | Teacher/Admin |
| POST | `/users/register` | 注册 | 公开 |
| POST | `/users/login` | 登录 | 公开 |
| GET | `/users/me` | 当前用户 | 认证 |
| GET | `/users` | 用户列表 | Admin |
| PATCH | `/users/{id}/role` | 修改角色 | Admin |
| POST | `/submissions` | 提交代码 | 认证 |
| GET | `/submissions/{id}` | 提交详情 | 认证 |
| GET | `/submissions/user/{id}` | 用户提交记录 | 认证 |
| GET | `/submissions` | 全部提交 | Teacher/Admin |
| POST | `/submissions/{id}/rejudge` | 重新评测 | Teacher/Admin |
| GET | `/dashboard/stats` | 仪表盘统计 | 认证 |
| GET | `/panel/scripts` | H# 脚本列表 | 认证 |
| POST | `/panel/run/{name}` | 执行 H# 脚本 | 认证 |

**统一响应格式：**
```json
{
  "success": true,
  "data": { ... },
  "message": null,
  "errorCode": null
}
```

**错误响应：**
```json
{
  "success": false,
  "errorCode": "VALIDATION_ERROR",
  "message": "题号格式应为 P001 ~ P99999",
  "traceId": "..."
}
```

---

## 8. 依赖注入与生命周期

| 服务 | 生命周期 | 理由 |
|------|----------|------|
| DbContext | Scoped | 单请求内共享，请求结束释放 |
| 仓储 | Scoped | 依赖 DbContext |
| UnitOfWork | Scoped | 协调事务 |
| ICurrentUser | Scoped | 依赖 HttpContext |
| IPasswordHasher | Singleton | 无状态 |
| ITokenService | Singleton | 无状态 |
| ICacheService | Singleton | 全局缓存 |
| IHSharpScriptRunner | Scoped | 每次执行独立进程 |

---

## 9. 中间件管道

```
请求 → GlobalExceptionMiddleware → RequestLoggingMiddleware → SerilogRequestLogging
     → HttpsRedirection → CORS → RateLimiter → Authentication → Authorization
     → Controllers
```

- **GlobalExceptionMiddleware**：捕获所有异常，按类型映射状态码（DomainException→400，NotFoundException→404）
- **RequestLoggingMiddleware**：记录每个请求的方法、路径、状态码、耗时
- **RateLimiter**：每 IP 每分钟 100 次（.NET 10 内置）
- **CORS**：允许前端跨域

---

## 10. 质量保障

### 单元测试（xUnit + NSubstitute + FluentAssertions）

- **Domain.Tests**：测试聚合根的创建、状态变更、领域事件、校验规则
- **Application.Tests**：测试 Handler 的编排逻辑，mock 仓储

### 集成测试（WebApplicationFactory）

- **Api.IntegrationTests**：测试完整 HTTP 管道，使用内存数据库
- 测试状态码、权限控制、错误响应

### 代码质量

- `AnalysisLevel = latest-recommended`（代码分析器推荐级别）
- `GenerateDocumentationFile = true`（XML 文档注释）
- `Nullable = enable`（空引用安全）
- `TreatWarningsAsErrors` 可在生产环境启用

---

## 11. 运行指南

### 构建与运行

```bash
# 由于沙盒环境限制，dotnet CLI 首次配置需要手动执行
# 在项目根目录运行：
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
dotnet restore
dotnet build

# 运行 API（默认 https://localhost:5000）
dotnet run --project src/ZZW.CodeTeacher.Api

# 运行测试
dotnet test

# 生成解决方案文件（如果需要）
dotnet new sln -n ZZWCodeTeacher --force
dotnet sln add **/*.csproj
```

### 数据库迁移（EF Core Code-First）

```bash
# 安装 EF 工具
dotnet tool install --global dotnet-ef

# 创建迁移
dotnet ef migrations add InitialCreate \
  --project src/ZZW.CodeTeacher.Infrastructure \
  --startup-project src/ZZW.CodeTeacher.Api

# 应用迁移
dotnet ef database update \
  --project src/ZZW.CodeTeacher.Infrastructure \
  --startup-project src/ZZW.CodeTeacher.Api
```

### 运行 H# 控制面板脚本

```bash
# 直接执行 H# 脚本
python3 hsharp.py ZZWCodeTeacher/src/ZZW.CodeTeacher.HSharpPanel/scripts/health_check.hto

# 通过 API 触发
curl -X POST http://localhost:5000/api/v1/panel/run/health_check
```

---

## 技术栈总结

| 层 | 技术 |
|----|------|
| 领域层 | C# 13 record struct、聚合根模式、领域事件 |
| 应用层 | MediatR 12（CQRS）、FluentValidation、AutoMapper |
| 基础设施 | EF Core 10（SQLite）、JWT、Serilog、MemoryCache |
| API | ASP.NET Core 10、Swagger、API 版本控制、限流 |
| H# 面板 | H# 脚本 + .NET Process 宿主 |
| 前端 | 原生 HTML/CSS/JS（TREA 风格设计系统） |
| 测试 | xUnit、NSubstitute、FluentAssertions、WebApplicationFactory |
