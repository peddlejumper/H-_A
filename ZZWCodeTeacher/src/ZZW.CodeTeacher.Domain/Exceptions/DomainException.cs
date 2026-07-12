namespace ZZW.CodeTeacher.Domain.Exceptions;

/// <summary>
/// 领域异常 —— 表示违反业务规则的错误。
/// </summary>
public class DomainException : Exception
{
    public DomainException(string message) : base(message) { }
    public DomainException(string message, Exception innerException) : base(message, innerException) { }
}

/// <summary>实体未找到异常</summary>
public class NotFoundException : DomainException
{
    public NotFoundException(string entityName, object key)
        : base($"{entityName} 未找到，键：{key}") { }
}

/// <summary>权限不足异常</summary>
public class ForbiddenException : DomainException
{
    public ForbiddenException(string message) : base(message) { }
}
