using System;
using System.IO;
using System.Text.RegularExpressions;

namespace IDE.UI
{
    public class HSharpVersionInfo
    {
        public string Version { get; set; } = "unknown";
        public string? PackagePath { get; set; }
        public string? PackageName { get; set; }
        public DateTime? LoadedAt { get; set; }
        public bool IsLoaded { get; set; }
        public string? BootstrapVersion { get; set; }
        public bool VersionMatch { get; set; }

        public static HSharpVersionInfo GetLauncherVersion()
        {
            var info = new HSharpVersionInfo { Version = "2.0" };

            // Try to read VERSION from launcher's own directory
            try
            {
                var baseDir = AppDomain.CurrentDomain.BaseDirectory;
                var versionFile = Path.Combine(baseDir, "VERSION");
                if (File.Exists(versionFile))
                {
                    var ver = File.ReadAllText(versionFile).Trim();
                    if (!string.IsNullOrEmpty(ver))
                        info.Version = ver;
                }
            }
            catch { }

            return info;
        }

        public static HSharpVersionInfo FromPackage(string packageDir, string? hpsPath)
        {
            var info = new HSharpVersionInfo
            {
                PackagePath = hpsPath,
                PackageName = hpsPath != null ? Path.GetFileName(hpsPath) : null,
                LoadedAt = DateTime.Now,
                IsLoaded = true,
                Version = "unknown"
            };

            // Try to read VERSION from the package directory
            try
            {
                var versionFile = Path.Combine(packageDir, "VERSION");
                if (File.Exists(versionFile))
                {
                    var ver = File.ReadAllText(versionFile).Trim();
                    if (!string.IsNullOrEmpty(ver))
                        info.Version = ver;
                }
            }
            catch { }

            // Try to read version from hsharp.py "__version__" or similar
            if (info.Version == "unknown")
            {
                try
                {
                    var hsharpPy = Path.Combine(packageDir, "hsharp.py");
                    if (File.Exists(hsharpPy))
                    {
                        var content = File.ReadAllText(hsharpPy);
                        var match = Regex.Match(content, @"__version__\s*=\s*[""']([^""']+)[""']");
                        if (match.Success)
                            info.Version = match.Groups[1].Value;
                    }
                }
                catch { }
            }

            // Try to read bootstrap version from bootstrap/VERSION or similar
            try
            {
                var bvFile = Path.Combine(packageDir, "bootstrap", "VERSION");
                if (File.Exists(bvFile))
                {
                    info.BootstrapVersion = File.ReadAllText(bvFile).Trim();
                }
            }
            catch { }

            // Compare versions
            try
            {
                var launcherVer = GetLauncherVersion().Version;
                info.VersionMatch = NormalizeVersion(launcherVer) == NormalizeVersion(info.Version);
            }
            catch
            {
                info.VersionMatch = false;
            }

            return info;
        }

        private static string NormalizeVersion(string v)
        {
            // Strip 'v' prefix and take major.minor
            var clean = v.Trim().TrimStart('v', 'V');
            var parts = clean.Split('.');
            if (parts.Length >= 2)
                return parts[0] + "." + parts[1];
            return clean;
        }

        public override string ToString()
        {
            if (!IsLoaded) return "No package loaded";
            var status = VersionMatch ? "✓" : "⚠";
            return $"{status} v{Version} [{PackageName}]";
        }
    }
}