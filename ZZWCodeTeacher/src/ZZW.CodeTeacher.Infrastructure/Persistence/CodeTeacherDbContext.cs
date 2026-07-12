namespace ZZW.CodeTeacher.Infrastructure.Persistence;

using System.Globalization;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.ValueObjects;

/// <summary>
/// EF Core DbContext —— Code-First 模式。
/// 使用 SQLite 作为默认数据库(轻量、零配置),生产环境可切换为 PostgreSQL/SQL Server。
/// </summary>
public sealed class CodeTeacherDbContext(DbContextOptions<CodeTeacherDbContext> options) : DbContext(options)
{
    public DbSet<Problem> Problems => Set<Problem>();
    public DbSet<TestCase> TestCases => Set<TestCase>();
    public DbSet<User> Users => Set<User>();
    public DbSet<Submission> Submissions => Set<Submission>();
    public DbSet<Favorite> Favorites => Set<Favorite>();
    public DbSet<CheckIn> CheckIns => Set<CheckIn>();
    public DbSet<Discussion> Discussions => Set<Discussion>();
    public DbSet<DiscussionReply> DiscussionReplies => Set<DiscussionReply>();
    public DbSet<Solution> Solutions => Set<Solution>();
    public DbSet<SolutionLike> SolutionLikes => Set<SolutionLike>();
    public DbSet<Announcement> Announcements => Set<Announcement>();
    public DbSet<AnnouncementRead> AnnouncementReads => Set<AnnouncementRead>();
    public DbSet<Group> Groups => Set<Group>();
    public DbSet<GroupMember> GroupMembers => Set<GroupMember>();
    public DbSet<ReviewItem> ReviewItems => Set<ReviewItem>();
    public DbSet<BlogPost> BlogPosts => Set<BlogPost>();
    public DbSet<BlogLike> BlogLikes => Set<BlogLike>();
    public DbSet<KnowledgePoint> KnowledgePoints => Set<KnowledgePoint>();
    public DbSet<ProblemKnowledgePoint> ProblemKnowledgePoints => Set<ProblemKnowledgePoint>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // ── Problem 聚合 ──
        modelBuilder.Entity<Problem>(e =>
        {
            e.ToTable("problems");
            e.HasKey(p => p.Id);
            e.Property(p => p.Code).HasMaxLength(20).IsRequired();
            e.HasIndex(p => p.Code).IsUnique();
            e.Property(p => p.Title).HasMaxLength(200).IsRequired();
            e.Property(p => p.Description).HasColumnType("TEXT");
            e.Property(p => p.Difficulty).HasConversion<string>();
            e.Property(p => p.CheckerType).HasConversion<string>().HasMaxLength(20).HasDefaultValue(CheckerType.Exact);
            e.Property(p => p.Template).HasColumnType("TEXT");
            e.Property(p => p.Tags).HasColumnType("TEXT"); // JSON 序列化

            // SupportedLanguages:逗号分隔的 int 枚举值列
            var langComparer = new ValueComparer<IReadOnlyList<SupportedLanguage>>(
                (a, b) => (a == null && b == null) || (a != null && b != null && a.SequenceEqual(b)),
                c => c == null ? 0 : c.Aggregate(0, (h, x) => HashCode.Combine(h, (int)x)),
                c => c == null ? new List<SupportedLanguage>() : c.ToList());
            e.Property(p => p.SupportedLanguages)
                .HasConversion(
                    v => string.Join(',', v.Select(x => (int)x)),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries)
                          .Select(x => (SupportedLanguage)int.Parse(x, CultureInfo.InvariantCulture)).ToList().AsReadOnly(),
                    langComparer)
                .HasColumnName("supported_languages")
                .HasColumnType("TEXT");

            e.Property(p => p.CreatedAt).HasColumnType("TEXT");
            e.Property(p => p.UpdatedAt).HasColumnType("TEXT");
            // 忽略领域事件(不持久化)
            e.Ignore(p => p.DomainEvents);

            // 配置 TestCases 导航:使用 _testCases backing field(因为是 computed readonly 属性)
            e.HasMany(p => p.TestCases).WithOne().HasForeignKey(t => t.ProblemId)
                .OnDelete(DeleteBehavior.Cascade);
            e.Navigation(p => p.TestCases).UsePropertyAccessMode(PropertyAccessMode.Field);
        });

        modelBuilder.Entity<TestCase>(e =>
        {
            e.ToTable("test_cases");
            e.HasKey(t => t.Id);
            e.Property(t => t.Input).HasColumnType("TEXT");
            e.Property(t => t.ExpectedOutput).HasColumnType("TEXT");
            e.HasIndex(t => new { t.ProblemId, t.Order }).IsUnique();
        });

        // ── User 聚合 ──
        modelBuilder.Entity<User>(e =>
        {
            e.ToTable("users");
            e.HasKey(u => u.Id);
            e.Property(u => u.Username).HasMaxLength(32).IsRequired();
            e.HasIndex(u => u.Username).IsUnique();
            e.Property(u => u.Email).HasMaxLength(256).IsRequired();
            e.HasIndex(u => u.Email).IsUnique();
            e.Property(u => u.PasswordHash).HasMaxLength(512).IsRequired();
            e.Property(u => u.DisplayName).HasMaxLength(50);
            e.Property(u => u.Role).HasConversion<string>();
            e.Ignore(u => u.DomainEvents);
        });

        // ── Submission 聚合 ──
        modelBuilder.Entity<Submission>(e =>
        {
            e.ToTable("submissions");
            e.HasKey(s => s.Id);
            e.Property(s => s.Status).HasConversion<string>();
            // CodeSnapshot 值对象 → 拆解为列(complex type);Language 改为枚举 string 转换
            e.ComplexProperty(s => s.Code, c =>
            {
                c.Property(p => p.Content).HasColumnType("TEXT").HasColumnName("code_content");
                c.Property(p => p.Language).HasConversion<string>().HasMaxLength(20).HasColumnName("code_language");
                c.Property(p => p.LineCount).HasColumnName("code_line_count");
                c.Property(p => p.CharCount).HasColumnName("code_char_count");
            });
            e.Ignore(s => s.DomainEvents);
            // JudgeReport 以 JSON 字符串持久化(含用例明细)
            e.Property(s => s.Report)
                .HasConversion(
                    v => v.HasValue ? System.Text.Json.JsonSerializer.Serialize(v.Value, (System.Text.Json.JsonSerializerOptions?)null) : null,
                    v => string.IsNullOrWhiteSpace(v) ? null : System.Text.Json.JsonSerializer.Deserialize<JudgeReport>(v, (System.Text.Json.JsonSerializerOptions?)null))
                .HasColumnName("report_json")
                .HasColumnType("TEXT");
        });

        // ── Favorite ──
        modelBuilder.Entity<Favorite>(e =>
        {
            e.ToTable("favorites");
            e.HasKey(f => f.Id);
            e.Property(f => f.CreatedAt).HasColumnType("TEXT");
            // UserId + ProblemId 唯一(防重复收藏)
            e.HasIndex(f => new { f.UserId, f.ProblemId }).IsUnique();
        });

        // ── CheckIn ──
        modelBuilder.Entity<CheckIn>(e =>
        {
            e.ToTable("check_ins");
            e.HasKey(c => c.Id);
            e.Property(c => c.CreatedAt).HasColumnType("TEXT");
            // UserId + CheckInDate 唯一(同用户同日不可重复打卡)
            e.HasIndex(c => new { c.UserId, c.CheckInDate }).IsUnique();
        });

        // ── Discussion 聚合 ──
        modelBuilder.Entity<Discussion>(e =>
        {
            e.ToTable("discussions");
            e.HasKey(d => d.Id);
            e.Property(d => d.Title).HasMaxLength(200).IsRequired();
            e.Property(d => d.Content).HasColumnType("TEXT").IsRequired();
            e.Property(d => d.CreatedAt).HasColumnType("TEXT");
            // 配置 Discussion → DiscussionReply 一对多
            e.HasMany(d => d.Replies).WithOne().HasForeignKey(r => r.DiscussionId)
                .OnDelete(DeleteBehavior.Cascade);
            e.Navigation(d => d.Replies).UsePropertyAccessMode(PropertyAccessMode.Field);
        });

        modelBuilder.Entity<DiscussionReply>(e =>
        {
            e.ToTable("discussion_replies");
            e.HasKey(r => r.Id);
            e.Property(r => r.Content).HasColumnType("TEXT").IsRequired();
            e.Property(r => r.CreatedAt).HasColumnType("TEXT");
        });

        // ── Solution 聚合 ──
        modelBuilder.Entity<Solution>(e =>
        {
            e.ToTable("solutions");
            e.HasKey(s => s.Id);
            e.Property(s => s.Title).HasMaxLength(200).IsRequired();
            e.Property(s => s.Content).HasColumnType("TEXT").IsRequired();
            e.Property(s => s.Code).HasColumnType("TEXT");
            e.Property(s => s.Language).HasConversion<string>().HasMaxLength(20);
            e.Property(s => s.CreatedAt).HasColumnType("TEXT");
            e.Property(s => s.UpdatedAt).HasColumnType("TEXT");
        });

        modelBuilder.Entity<SolutionLike>(e =>
        {
            e.ToTable("solution_likes");
            e.HasKey(l => l.Id);
            e.Property(l => l.CreatedAt).HasColumnType("TEXT");
            // 同用户同题解唯一
            e.HasIndex(l => new { l.SolutionId, l.UserId }).IsUnique();
        });

        // ── Announcement ──
        modelBuilder.Entity<Announcement>(e =>
        {
            e.ToTable("announcements");
            e.HasKey(a => a.Id);
            e.Property(a => a.Title).HasMaxLength(200).IsRequired();
            e.Property(a => a.Content).HasColumnType("TEXT").IsRequired();
            e.Property(a => a.CreatedAt).HasColumnType("TEXT");
        });

        modelBuilder.Entity<AnnouncementRead>(e =>
        {
            e.ToTable("announcement_reads");
            e.HasKey(r => r.Id);
            e.Property(r => r.ReadAt).HasColumnType("TEXT");
            e.HasIndex(r => new { r.AnnouncementId, r.UserId }).IsUnique();
        });

        // ── Group ──
        modelBuilder.Entity<Group>(e =>
        {
            e.ToTable("groups");
            e.HasKey(g => g.Id);
            e.Property(g => g.Name).HasMaxLength(100).IsRequired();
            e.Property(g => g.Description).HasColumnType("TEXT");
            e.Property(g => g.InviteCode).HasMaxLength(32).IsRequired();
            e.HasIndex(g => g.InviteCode).IsUnique();
            e.Property(g => g.CreatedAt).HasColumnType("TEXT");
        });

        modelBuilder.Entity<GroupMember>(e =>
        {
            e.ToTable("group_members");
            e.HasKey(m => m.Id);
            e.Property(m => m.Role).HasConversion<string>();
            e.Property(m => m.JoinedAt).HasColumnType("TEXT");
            // 同用户同班级唯一
            e.HasIndex(m => new { m.GroupId, m.UserId }).IsUnique();
        });

        // ── ReviewItem(SM-2) ──
        modelBuilder.Entity<ReviewItem>(e =>
        {
            e.ToTable("review_items");
            e.HasKey(r => r.Id);
            e.Property(r => r.EaseFactor).HasColumnType("REAL");
            e.Property(r => r.CreatedAt).HasColumnType("TEXT");
            e.Property(r => r.LastReviewedAt).HasColumnType("TEXT");
            // 同用户同题目唯一(一道题一个复习项)
            e.HasIndex(r => new { r.UserId, r.ProblemId }).IsUnique();
        });

        // ── BlogPost ──
        modelBuilder.Entity<BlogPost>(e =>
        {
            e.ToTable("blog_posts");
            e.HasKey(b => b.Id);
            e.Property(b => b.Title).HasMaxLength(200).IsRequired();
            e.Property(b => b.Summary).HasColumnType("TEXT");
            e.Property(b => b.Content).HasColumnType("TEXT").IsRequired();
            e.Property(b => b.Tags).HasColumnType("TEXT"); // JSON 序列化(EF Core 原始集合)
            e.Property(b => b.CreatedAt).HasColumnType("TEXT");
            e.Property(b => b.UpdatedAt).HasColumnType("TEXT");
        });

        modelBuilder.Entity<BlogLike>(e =>
        {
            e.ToTable("blog_likes");
            e.HasKey(l => l.Id);
            e.Property(l => l.CreatedAt).HasColumnType("TEXT");
            e.HasIndex(l => new { l.BlogPostId, l.UserId }).IsUnique();
        });

        // ── KnowledgePoint ──
        modelBuilder.Entity<KnowledgePoint>(e =>
        {
            e.ToTable("knowledge_points");
            e.HasKey(k => k.Id);
            e.Property(k => k.Name).HasMaxLength(100).IsRequired();
            e.Property(k => k.Description).HasColumnType("TEXT");
            e.Property(k => k.CreatedAt).HasColumnType("TEXT");
            // 自关联(父节点)不强制外键约束,允许自由构建树
            e.HasIndex(k => k.ParentId);
        });

        modelBuilder.Entity<ProblemKnowledgePoint>(e =>
        {
            e.ToTable("problem_knowledge_points");
            e.HasKey(p => p.Id);
            e.HasIndex(p => new { p.ProblemId, p.KnowledgePointId }).IsUnique();
            e.HasIndex(p => p.KnowledgePointId);
        });
    }
}
