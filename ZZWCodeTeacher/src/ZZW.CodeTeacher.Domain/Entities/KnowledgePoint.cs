namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 知识点聚合根 —— 自关联(ParentId)形成树形结构,用于构建知识点图谱。
/// </summary>
public sealed class KnowledgePoint
{
    /// <summary>知识点唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>名称</summary>
    public string Name { get; private set; } = string.Empty;

    /// <summary>描述</summary>
    public string Description { get; private set; } = string.Empty;

    /// <summary>父知识点 Id( null 表示根节点)</summary>
    public Guid? ParentId { get; private set; }

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    // EF Core 构造函数
    private KnowledgePoint() { }

    /// <summary>工厂方法:创建知识点</summary>
    public static KnowledgePoint Create(string name, string description, Guid? parentId = null)
    {
        if (string.IsNullOrWhiteSpace(name))
            throw new DomainException("知识点名称不能为空");
        if (name.Length > 100)
            throw new DomainException("知识点名称长度不能超过 100");

        return new KnowledgePoint
        {
            Id = Guid.NewGuid(),
            Name = name.Trim(),
            Description = description ?? string.Empty,
            ParentId = parentId,
            CreatedAt = DateTime.UtcNow
        };
    }
}

/// <summary>
/// 题目与知识点的多对多关联实体。
/// </summary>
public sealed class ProblemKnowledgePoint
{
    /// <summary>关联唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>题目 Id</summary>
    public Guid ProblemId { get; private set; }

    /// <summary>知识点 Id</summary>
    public Guid KnowledgePointId { get; private set; }

    private ProblemKnowledgePoint() { }

    public static ProblemKnowledgePoint Create(Guid problemId, Guid knowledgePointId)
    {
        if (problemId == Guid.Empty)
            throw new DomainException("题目 Id 不能为空");
        if (knowledgePointId == Guid.Empty)
            throw new DomainException("知识点 Id 不能为空");

        return new ProblemKnowledgePoint
        {
            Id = Guid.NewGuid(),
            ProblemId = problemId,
            KnowledgePointId = knowledgePointId
        };
    }
}
