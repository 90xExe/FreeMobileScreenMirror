using NAudio.CoreAudioApi;

namespace ClearMirror.Audio;

public sealed record AudioEndpoint(string Id, string Name, bool IsDefault)
{
    public string DisplayName => IsDefault ? $"{Name} (Windows default)" : Name;
}

public static class AudioDevices
{
    public static IReadOnlyList<AudioEndpoint> GetInputs() => Enumerate(DataFlow.Capture, Role.Communications);
    public static IReadOnlyList<AudioEndpoint> GetOutputs() => Enumerate(DataFlow.Render, Role.Multimedia);

    private static IReadOnlyList<AudioEndpoint> Enumerate(DataFlow flow, Role role)
    {
        using var enumerator = new MMDeviceEnumerator();
        string? defaultId = null;
        if (enumerator.HasDefaultAudioEndpoint(flow, role))
        {
            using var endpoint = enumerator.GetDefaultAudioEndpoint(flow, role);
            defaultId = endpoint.ID;
        }
        var results = new List<AudioEndpoint>();
        foreach (var device in enumerator.EnumerateAudioEndPoints(flow, DeviceState.Active))
        {
            using (device)
                results.Add(new AudioEndpoint(device.ID, device.FriendlyName, device.ID == defaultId));
        }
        return results.OrderByDescending(d => d.IsDefault).ThenBy(d => d.Name).ToArray();
    }
}
