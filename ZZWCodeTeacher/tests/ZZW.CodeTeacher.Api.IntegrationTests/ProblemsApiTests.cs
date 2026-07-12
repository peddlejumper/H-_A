namespace ZZW.CodeTeacher.Api.IntegrationTests;

using System.Net;
using System.Net.Http.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Xunit;
using ZZW.CodeTeacher.Infrastructure.Persistence;

public class ProblemsApiTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;

    public ProblemsApiTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.WithWebHostBuilder(b =>
        {
            b.ConfigureServices(s =>
            {
                // 使用内存数据库替代 SQLite
                s.AddDbContext<CodeTeacherDbContext>(opt => opt.UseInMemoryDatabase("TestDb"));
            });
        }).CreateClient();
    }

    [Fact]
    public async Task ListProblems_ShouldReturn200()
    {
        var resp = await _client.GetAsync("/api/v1/problems");
        resp.StatusCode.Should().Be(HttpStatusCode.OK);
    }

    [Fact]
    public async Task GetById_WhenNotFound_ShouldReturn404()
    {
        var resp = await _client.GetAsync($"/api/v1/problems/{Guid.NewGuid()}");
        resp.StatusCode.Should().Be(HttpStatusCode.NotFound);
    }

    [Fact]
    public async Task Create_WithoutAuth_ShouldReturn401()
    {
        var resp = await _client.PostAsJsonAsync("/api/v1/problems", new
        {
            Code = "P001", Title = "T", Description = "D",
            Difficulty = 0, TimeLimitMs = 1000, MemoryLimitKb = 65536,
            Template = "", Tags = Array.Empty<string>()
        });
        resp.StatusCode.Should().Be(HttpStatusCode.Unauthorized);
    }
}
