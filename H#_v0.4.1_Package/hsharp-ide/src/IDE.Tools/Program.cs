using System;
using System.IO;
using System.Diagnostics;
using System.Threading.Tasks;

namespace IDE.Tools
{
    class Program
    {
        static async Task<int> Main(string[] args)
        {
            var python = Environment.GetEnvironmentVariable("HSHARP_PYTHON") ?? "python3";
            var hsharp = FindHSharpPy();
            if (hsharp == null)
            {
                Console.Error.WriteLine("Error: 在当前目录及父目录中未找到 hsharp.py。请设置环境变量 HSHARP_PYTHON 指向 Python 可执行文件，或将本程序放到仓库目录下运行。");
                return 1;
            }

            if (args.Length == 0)
            {
                Console.WriteLine("IDE.Tools - helper for H# IDE");
                Console.WriteLine("Usage: dotnet run --project src/IDE.Tools -- [repl|run|emit-bc|run-bc] <file>");
                return 0;
            }

            var cmd = args[0];
            switch (cmd)
            {
                case "repl":
                    return await RunInteractive(python, hsharp);
                case "run":
                    if (args.Length < 2) { Console.Error.WriteLine("Usage: run <file.hto>"); return 1; }
                    return RunProcess(python, Quote(hsharp) + " " + Quote(args[1]));
                case "emit-bc":
                    if (args.Length < 2) { Console.Error.WriteLine("Usage: emit-bc <file.hto>"); return 1; }
                    return RunProcess(python, Quote(hsharp) + " --emit-bc " + Quote(args[1]));
                case "run-bc":
                    if (args.Length < 2) { Console.Error.WriteLine("Usage: run-bc <file.hbc>"); return 1; }
                    return RunProcess(python, Quote(hsharp) + " --run-bc " + Quote(args[1]));
                default:
                    Console.Error.WriteLine($"Unknown command: {cmd}");
                    return 1;
            }
        }

        static string? FindHSharpPy()
        {
            var dir = Directory.GetCurrentDirectory();
            for (int i = 0; i < 12; i++)
            {
                var candidate = Path.Combine(dir, "hsharp.py");
                if (File.Exists(candidate)) return Path.GetFullPath(candidate);
                dir = Path.GetDirectoryName(dir) ?? string.Empty;
                if (string.IsNullOrEmpty(dir)) break;
            }
            return null;
        }

        static int RunProcess(string fileName, string arguments)
        {
            var psi = new ProcessStartInfo
            {
                FileName = fileName,
                Arguments = arguments,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = false
            };
            using var p = Process.Start(psi) ?? throw new Exception("Failed to start process");
            p.OutputDataReceived += (s, e) => { if (e.Data != null) Console.WriteLine(e.Data); };
            p.ErrorDataReceived += (s, e) => { if (e.Data != null) Console.Error.WriteLine(e.Data); };
            p.BeginOutputReadLine();
            p.BeginErrorReadLine();
            p.WaitForExit();
            return p.ExitCode;
        }

        static async Task<int> RunInteractive(string python, string hsharp)
        {
            var psi = new ProcessStartInfo
            {
                FileName = python,
                Arguments = Quote(hsharp),
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = false
            };
            using var p = Process.Start(psi) ?? throw new Exception("Failed to start process");

            // forward stdout
            _ = Task.Run(async () =>
            {
                var s = p.StandardOutput;
                string? line;
                while ((line = await s.ReadLineAsync()) != null)
                {
                    Console.WriteLine(line);
                }
            });

            // forward stderr
            _ = Task.Run(async () =>
            {
                var s = p.StandardError;
                string? line;
                while ((line = await s.ReadLineAsync()) != null)
                {
                    Console.Error.WriteLine(line);
                }
            });

            // forward stdin
            string? input;
            while ((input = Console.ReadLine()) != null)
            {
                await p.StandardInput.WriteLineAsync(input);
                await p.StandardInput.FlushAsync();
            }

            p.WaitForExit();
            return p.ExitCode;
        }

        static string Quote(string s) => s.Contains(' ') ? '"' + s + '"' : s;
    }
}
