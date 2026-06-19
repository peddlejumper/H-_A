using System;
using System.IO;
using System.Text.Json;

namespace IDE.UI
{
    internal class LauncherConfigData
    {
        public string? HSharpCompiler { get; set; }
    }

    public static class LauncherConfig
    {
        private static string GetConfigFilePath()
        {
            string baseDir;
            try
            {
                baseDir = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                if (string.IsNullOrEmpty(baseDir))
                    baseDir = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile) ?? ".";
            }
            catch
            {
                baseDir = ".";
            }

            var cfgDir = Path.Combine(baseDir, "HSharpLauncher");
            try { Directory.CreateDirectory(cfgDir); } catch { }
            return Path.Combine(cfgDir, "config.json");
        }

        public static string? GetSelectedCompilerPath()
        {
            // Prefer explicit environment variable first
            var env = Environment.GetEnvironmentVariable("HSHARP_COMPILER");
            if (!string.IsNullOrEmpty(env) && File.Exists(env))
                return Path.GetFullPath(env);

            try
            {
                var path = GetConfigFilePath();
                if (!File.Exists(path)) return null;
                var txt = File.ReadAllText(path);
                var cfg = JsonSerializer.Deserialize<LauncherConfigData>(txt);
                if (cfg == null || string.IsNullOrEmpty(cfg.HSharpCompiler)) return null;
                if (File.Exists(cfg.HSharpCompiler)) return Path.GetFullPath(cfg.HSharpCompiler);
                return null;
            }
            catch
            {
                return null;
            }
        }

        public static void SetSelectedCompilerPath(string compilerPath)
        {
            try
            {
                var cfgPath = GetConfigFilePath();
                var cfg = new LauncherConfigData { HSharpCompiler = compilerPath };
                var txt = JsonSerializer.Serialize(cfg);
                File.WriteAllText(cfgPath, txt);
                // Set for current process so changes take effect immediately
                Environment.SetEnvironmentVariable("HSHARP_COMPILER", compilerPath);
            }
            catch
            {
                // ignore failures
            }
        }
    }
}
