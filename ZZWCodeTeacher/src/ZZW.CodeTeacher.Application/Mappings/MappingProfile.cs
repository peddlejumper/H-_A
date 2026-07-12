namespace ZZW.CodeTeacher.Application.Mappings;

using AutoMapper;
using ZZW.CodeTeacher.Application.DTOs;
using ZZW.CodeTeacher.Domain.Entities;
using ZZW.CodeTeacher.Domain.ValueObjects;

/// <summary>
/// AutoMapper 映射配置。
/// </summary>
public sealed class MappingProfile : Profile
{
    public MappingProfile()
    {
        CreateMap<Problem, ProblemDto>()
            .ForMember(d => d.TestCaseCount, opt => opt.MapFrom(s => s.TestCases.Count))
            .ForMember(d => d.Samples, opt => opt.MapFrom(s =>
                s.TestCases
                    .Where(t => t.IsSample)
                    .OrderBy(t => t.Order)
                    .Select(t => new ProblemSampleDto(t.Input, t.ExpectedOutput))
                    .ToList()));
        CreateMap<User, UserDto>();
        CreateMap<TestCaseResult, CaseResultDto>();
        CreateMap<Submission, SubmissionDto>()
            .ForMember(d => d.Code, opt => opt.MapFrom(s => s.Code.Content))
            .ForMember(d => d.Language, opt => opt.MapFrom(s => s.Code.Language))
            .ForMember(d => d.LineCount, opt => opt.MapFrom(s => s.Code.LineCount))
            .ForMember(d => d.PassedCases, opt => opt.MapFrom(s => s.Report.HasValue ? s.Report.Value.PassedCases : 0))
            .ForMember(d => d.TotalCases, opt => opt.MapFrom(s => s.Report.HasValue ? s.Report.Value.TotalCases : 0))
            .ForMember(d => d.ElapsedMs, opt => opt.MapFrom(s => s.Report.HasValue ? s.Report.Value.TotalElapsedMs : 0))
            .ForMember(d => d.Cases, opt => opt.MapFrom(s => s.Report.HasValue
                ? s.Report.Value.Cases.Select(c => new CaseResultDto(c.Index, c.Passed, c.ElapsedMs, c.MemoryKb, c.Expected, c.Actual, c.Error)).ToList()
                : new List<CaseResultDto>()))
            .ForMember(d => d.ProblemCode, opt => opt.Ignore())
            .ForMember(d => d.ProblemTitle, opt => opt.Ignore())
            .ForMember(d => d.Username, opt => opt.Ignore());
    }
}
