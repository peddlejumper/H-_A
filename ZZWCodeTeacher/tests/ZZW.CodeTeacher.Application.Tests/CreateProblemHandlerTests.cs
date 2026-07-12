namespace ZZW.CodeTeacher.Application.Tests;

using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using NSubstitute;
using Xunit;
using ZZW.CodeTeacher.Application.Commands;
using ZZW.CodeTeacher.Application.UseCases;
using ZZW.CodeTeacher.Application.Interfaces;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Exceptions;
using ZZW.CodeTeacher.Domain.Repositories;

public class CreateProblemHandlerTests
{
    private static readonly string[] Tags = { "数组" };
    private readonly IProblemRepository _repo = Substitute.For<IProblemRepository>();
    private readonly IUnitOfWork _uow = Substitute.For<IUnitOfWork>();
    private readonly AutoMapper.IMapper _mapper;

    public CreateProblemHandlerTests()
    {
        var expr = new AutoMapper.MapperConfigurationExpression();
        expr.AddProfile<Mappings.MappingProfile>();
        var config = new AutoMapper.MapperConfiguration(expr, NullLoggerFactory.Instance);
        _mapper = config.CreateMapper();
    }

    [Fact]
    public async Task Handle_WithValidCommand_ShouldCreateProblem()
    {
        // Arrange
        _repo.GetByCodeAsync("P001", Arg.Any<CancellationToken>())
            .Returns((Problem?)null);
        var handler = new CreateProblemHandler(_repo, _uow, _mapper);
        var cmd = new CreateProblemCommand("P001", "两数之和", "描述",
            DifficultyLevel.Easy, 1000, 65536, "template", Tags,
            new[] { SupportedLanguage.Python });

        // Act
        var result = await handler.Handle(cmd, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Code.Should().Be("P001");
        await _repo.Received(1).AddAsync(Arg.Any<Problem>(), Arg.Any<CancellationToken>());
        await _uow.Received(1).SaveChangesAsync(Arg.Any<CancellationToken>());
    }

    [Fact]
    public async Task Handle_WithDuplicateCode_ShouldThrow()
    {
        // Arrange
        var existing = Problem.Create("P001", "旧", "D", DifficultyLevel.Easy);
        _repo.GetByCodeAsync("P001", Arg.Any<CancellationToken>()).Returns(existing);
        var handler = new CreateProblemHandler(_repo, _uow, _mapper);
        var cmd = new CreateProblemCommand("P001", "新", "D",
            DifficultyLevel.Easy, 1000, 65536, "", [],
            new[] { SupportedLanguage.Python });

        // Act
        var act = async () => await handler.Handle(cmd, CancellationToken.None);

        // Assert
        await act.Should().ThrowAsync<DomainException>().WithMessage("*P001*已存在*");
    }
}
