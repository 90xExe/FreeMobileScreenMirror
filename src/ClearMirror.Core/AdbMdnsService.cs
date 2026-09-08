using System.Text.RegularExpressions;

namespace ClearMirror.Core;

public enum AdbMdnsServiceKind
{
    Unknown,
    Legacy,
    Pairing,
    Connect
}

public sealed record AdbMdnsService(string InstanceName, string ServiceType, string Address)
{
    public AdbMdnsServiceKind Kind => ServiceType switch
    {
        "_adb._tcp" => AdbMdnsServiceKind.Legacy,
        "_adb-tls-pairing._tcp" => AdbMdnsServiceKind.Pairing,
        "_adb-tls-connect._tcp" => AdbMdnsServiceKind.Connect,
        _ => AdbMdnsServiceKind.Unknown
    };

    public string DisplayName => Kind switch
    {
        AdbMdnsServiceKind.Pairing => $"Ready to pair  ·  {Address}",
        AdbMdnsServiceKind.Connect => $"Wireless Android  ·  {Address}",
        AdbMdnsServiceKind.Legacy => $"Legacy Android  ·  {Address}",
        _ => $"Android service  ·  {Address}"
    };
}

public static partial class AdbMdnsServiceParser
{
    [GeneratedRegex("^(?<name>\\S+)\\s+(?<type>_adb(?:-tls-(?:pairing|connect))?\\._tcp)\\s+(?<address>(?:\\d{1,3}\\.){3}\\d{1,3}:\\d+)$", RegexOptions.IgnoreCase)]
    private static partial Regex ServiceLineRegex();

    public static IReadOnlyList<AdbMdnsService> Parse(string? output)
    {
        if (string.IsNullOrWhiteSpace(output))
            return Array.Empty<AdbMdnsService>();

        var services = new List<AdbMdnsService>();
        foreach (var rawLine in output.Replace("\r", string.Empty).Split('\n'))
        {
            var match = ServiceLineRegex().Match(rawLine.Trim());
            if (!match.Success)
                continue;

            services.Add(new AdbMdnsService(
                match.Groups["name"].Value,
                match.Groups["type"].Value.ToLowerInvariant(),
                match.Groups["address"].Value));
        }

        return services
            .GroupBy(service => (service.ServiceType, service.Address))
            .Select(group => group.First())
            .OrderBy(service => service.Kind)
            .ThenBy(service => service.Address, StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }
}
