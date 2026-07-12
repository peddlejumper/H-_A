namespace ZZW.CodeTeacher.Domain.Entities;

using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 班级/小组聚合根 —— 教师创建,学员凭邀请码加入。
/// </summary>
public sealed class Group
{
    /// <summary>班级唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>班级名称</summary>
    public string Name { get; private set; } = string.Empty;

    /// <summary>描述</summary>
    public string Description { get; private set; } = string.Empty;

    /// <summary>创建者(教师)用户 Id</summary>
    public Guid CreatorId { get; private set; }

    /// <summary>创建时间</summary>
    public DateTime CreatedAt { get; private set; }

    /// <summary>邀请码(6 位,加入班级用)</summary>
    public string InviteCode { get; private set; } = string.Empty;

    // EF Core 构造函数
    private Group() { }

    /// <summary>工厂方法:创建班级(自动生成邀请码,创建者自动成为 Owner)</summary>
    public static Group Create(Guid creatorId, string name, string description)
    {
        if (creatorId == Guid.Empty)
            throw new DomainException("创建者 Id 不能为空");
        if (string.IsNullOrWhiteSpace(name))
            throw new DomainException("班级名称不能为空");
        if (name.Length > 100)
            throw new DomainException("班级名称长度不能超过 100");

        return new Group
        {
            Id = Guid.NewGuid(),
            CreatorId = creatorId,
            Name = name.Trim(),
            Description = description ?? string.Empty,
            InviteCode = GenerateInviteCode(),
            CreatedAt = DateTime.UtcNow
        };
    }

    /// <summary>生成 6 位邀请码(大写字母+数字)</summary>
    private static string GenerateInviteCode()
    {
        const string chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
        var span = new char[6];
        var random = Random.Shared;
        for (var i = 0; i < 6; i++)
            span[i] = chars[random.Next(chars.Length)];
        return new string(span);
    }
}

/// <summary>
/// 班级成员实体 —— 记录用户与班级的归属关系及角色。
/// </summary>
public sealed class GroupMember
{
    /// <summary>成员关系唯一标识</summary>
    public Guid Id { get; private set; }

    /// <summary>班级 Id</summary>
    public Guid GroupId { get; private set; }

    /// <summary>用户 Id</summary>
    public Guid UserId { get; private set; }

    /// <summary>成员角色(Owner / Member)</summary>
    public GroupMemberRole Role { get; private set; }

    /// <summary>加入时间</summary>
    public DateTime JoinedAt { get; private set; }

    private GroupMember() { }

    public static GroupMember Create(Guid groupId, Guid userId, GroupMemberRole role)
    {
        if (groupId == Guid.Empty)
            throw new DomainException("班级 Id 不能为空");
        if (userId == Guid.Empty)
            throw new DomainException("用户 Id 不能为空");

        return new GroupMember
        {
            Id = Guid.NewGuid(),
            GroupId = groupId,
            UserId = userId,
            Role = role,
            JoinedAt = DateTime.UtcNow
        };
    }
}
