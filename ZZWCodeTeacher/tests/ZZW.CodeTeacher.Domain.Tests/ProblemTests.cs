namespace ZZW.CodeTeacher.Domain.Tests;

using FluentAssertions;
using Xunit;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.Enums;
using ZZW.CodeTeacher.Domain.Exceptions;

public class ProblemTests
{
    [Fact]
    public void Create_WithValidData_ShouldSucceed()
    {
        // Arrange & Act
        var problem = Problem.Create("P001", "两数之和", "描述", DifficultyLevel.Easy);

        // Assert
        problem.Should().NotBeNull();
        problem.Code.Should().Be("P001");
        problem.Title.Should().Be("两数之和");
        problem.Difficulty.Should().Be(DifficultyLevel.Easy);
        problem.IsActive.Should().BeTrue();
        problem.TestCases.Should().BeEmpty();
        problem.DomainEvents.Should().ContainSingle(e => e is Events.ProblemCreatedEvent);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("TOOLONGCODETOOLONGCODE")]
    public void Create_WithInvalidCode_ShouldThrow(string code)
    {
        var act = () => Problem.Create(code, "标题", "描述", DifficultyLevel.Easy);
        act.Should().Throw<DomainException>();
    }

    [Fact]
    public void AddTestCase_ShouldIncrementOrder()
    {
        var problem = Problem.Create("P001", "T", "D", DifficultyLevel.Easy);
        problem.AddTestCase("1 2", "3", false);
        problem.AddTestCase("4 5", "9", true);

        problem.TestCases.Should().HaveCount(2);
        problem.TestCases[0].Order.Should().Be(1);
        problem.TestCases[1].Order.Should().Be(2);
        problem.TestCases[1].IsSample.Should().BeTrue();
    }

    [Fact]
    public void AddTestCase_ExceedingLimit_ShouldThrow()
    {
        var problem = Problem.Create("P001", "T", "D", DifficultyLevel.Easy);
        for (var i = 0; i < 50; i++)
            problem.AddTestCase("in", "out");

        var act = () => problem.AddTestCase("extra", "out");
        act.Should().Throw<DomainException>().WithMessage("*50*");
    }

    [Fact]
    public void SetActive_ShouldRaiseEvent()
    {
        var problem = Problem.Create("P001", "T", "D", DifficultyLevel.Easy);
        problem.ClearDomainEvents();

        problem.SetActive(false);

        problem.IsActive.Should().BeFalse();
        problem.DomainEvents.Should().ContainSingle(e => e is Events.ProblemStatusChangedEvent);
    }
}

public class SubmissionTests
{
    [Fact]
    public void Create_ShouldBePending()
    {
        var sub = Submission.Create(Guid.NewGuid(), Guid.NewGuid(), "let x = 1;", SupportedLanguage.HSharp);
        sub.Status.Should().Be(SubmissionStatus.Pending);
        sub.Code.LineCount.Should().Be(1);
        sub.Score.Should().Be(0);
    }

    [Fact]
    public void SetResult_AllPassed_ShouldBeAccepted()
    {
        var sub = Submission.Create(Guid.NewGuid(), Guid.NewGuid(), "code", SupportedLanguage.HSharp);
        var report = new ValueObjects.JudgeReport(2, 2, 100, 1024,
            new[] { ValueObjects.TestCaseResult.Pass(0, 50, 0), ValueObjects.TestCaseResult.Pass(1, 50, 0) });

        sub.SetResult(report);

        sub.Status.Should().Be(SubmissionStatus.Accepted);
        sub.Score.Should().Be(100);
    }
}
