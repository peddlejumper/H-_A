using System;
using System.IO;
using System.Text.Json;

namespace IDE.UI
{
    public class LauncherConfigData
    {
        public string? HSharpCompiler { get; set; }
        // 版本追踪
        public string? LastPackagePath { get; set; }
        public string? LastPackageVersion { get; set; }
        public string? LastPackageName { get; set; }
        public string? LastLoadTime { get; set; }
        public string? LauncherVersion { get; set; }
        // 版本历史 (最多保留 10 条)
        public PackageHistoryEntry[]? PackageHistory { get; set; }
    }

    public class PackageHistoryEntry
    {
        public string? Path { get; set; }
        public string? Version { get; set; }
        public string? Name { get; set; }
        public string? LoadedAt { get; set; }
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

        public static LauncherConfigData Load()
        {
            try
            {
                var path = GetConfigFilePath();
                if (!File.Exists(path)) return new LauncherConfigData();
                var txt = File.ReadAllText(path);
                return JsonSerializer.Deserialize<LauncherConfigData>(txt) ?? new LauncherConfigData();
            }
            catch
            {
                return new LauncherConfigData();
            }
        }

        private static void Save(LauncherConfigData cfg)
        {
            try
            {
                var cfgPath = GetConfigFilePath();
                var txt = JsonSerializer.Serialize(cfg);
                File.WriteAllText(cfgPath, txt);
            }
            catch { }
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
                var cfg = Load();
                cfg.HSharpCompiler = compilerPath;
                Save(cfg);
                // Set for current process so changes take effect immediately
                Environment.SetEnvironmentVariable("HSHARP_COMPILER", compilerPath);
            }
            catch
            {
                // ignore failures
            }
        }

        // ──────────── 版本追踪 ────────────

        public static string GetLauncherVersion()
        {
            // First check config
            var cfg = Load();
            if (!string.IsNullOrEmpty(cfg.LauncherVersion))
                return cfg.LauncherVersion;

            // Then check VERSION file
            try
            {
                var versionFile = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "VERSION");
                if (File.Exists(versionFile))
                {
                    var ver = File.ReadAllText(versionFile).Trim();
                    if (!string.IsNullOrEmpty(ver))
                    {
                        cfg.LauncherVersion = ver;
                        Save(cfg);
                        return ver;
                    }
                }
            }
            catch { }

            return "2.0"; // default
        }

        public static void RecordPackageLoaded(string? hpsPath, string? version, string? name)
        {
            try
            {
                var cfg = Load();
                var now = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");

                cfg.LastPackagePath = hpsPath;
                cfg.LastPackageVersion = version;
                cfg.LastPackageName = name;
                cfg.LastLoadTime = now;

                // Add to history
                var history = cfg.PackageHistory != null
                    ? new List<PackageHistoryEntry>(cfg.PackageHistory)
                    : new List<PackageHistoryEntry>();

                history.Insert(0, new PackageHistoryEntry
                {
                    Path = hpsPath,
                    Version = version,
                    Name = name,
                    LoadedAt = now
                });

                // Keep only last 10
                if (history.Count > 10)
                    history = history.Take(10).ToList();

                cfg.PackageHistory = history.ToArray();
                Save(cfg);
            }
            catch { }
        }

        public static PackageHistoryEntry? GetLastPackage()
        {
            var cfg = Load();
            if (string.IsNullOrEmpty(cfg.LastPackageName))
                return null;

            return new PackageHistoryEntry
            {
                Path = cfg.LastPackagePath,
                Version = cfg.LastPackageVersion,
                Name = cfg.LastPackageName,
                LoadedAt = cfg.LastLoadTime
            };
        }

        public static PackageHistoryEntry[] GetPackageHistory()
        {
            var cfg = Load();
            return cfg.PackageHistory ?? Array.Empty<PackageHistoryEntry>();
        }
    }
}