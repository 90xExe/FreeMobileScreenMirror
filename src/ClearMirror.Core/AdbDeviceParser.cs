namespace ClearMirror.Core;

public static class AdbDeviceParser
{
    public static IReadOnlyList<AdbDevice> Parse(string? output)
    {
        if (string.IsNullOrWhiteSpace(output))
            return Array.Empty<AdbDevice>();

        var devices = new List<AdbDevice>();
        var lines = output.Replace("\r", string.Empty).Split('\n');

        foreach (var rawLine in lines)
        {
            var line = rawLine.Trim();
            if (line.Length == 0 || line.StartsWith("List of devices", StringComparison.OrdinalIgnoreCase) || line.StartsWith('*'))
                continue;

            var parts = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2)
                continue;

            var serial = parts[0];
            var state = parts[1];
            var model = ReadValue(parts, "model:");
            var product = ReadValue(parts, "product:");
            devices.Add(new AdbDevice(serial, state, model, product));
        }

        return devices;
    }

    private static string ReadValue(IEnumerable<string> parts, string prefix)
    {
        var match = parts.FirstOrDefault(p => p.StartsWith(prefix, StringComparison.OrdinalIgnoreCase));
        return match is null ? string.Empty : match[prefix.Length..];
    }
}
