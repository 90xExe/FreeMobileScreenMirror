namespace ClearMirror.Core;

public static class ScrcpyArgumentBuilder
{
    private static readonly HashSet<string> VideoCodecs = new(StringComparer.OrdinalIgnoreCase) { "h264", "h265" };
    private static readonly HashSet<string> AudioCodecs = new(StringComparer.OrdinalIgnoreCase) { "opus", "aac" };

    public static IReadOnlyList<string> Build(MirrorOptions options)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(options.Serial);
        if (!VideoCodecs.Contains(options.VideoCodec))
            throw new ArgumentOutOfRangeException(nameof(options.VideoCodec));
        if (!AudioCodecs.Contains(options.AudioCodec))
            throw new ArgumentOutOfRangeException(nameof(options.AudioCodec));
        if (options.MaxFps is < 1 or > 240)
            throw new ArgumentOutOfRangeException(nameof(options.MaxFps));
        if (options.VideoBitRateMbps is < 1 or > 200)
            throw new ArgumentOutOfRangeException(nameof(options.VideoBitRateMbps));

        var args = new List<string>
        {
            "-s", options.Serial,
            $"--video-codec={options.VideoCodec.ToLowerInvariant()}",
            $"--video-bit-rate={options.VideoBitRateMbps}M",
            $"--max-fps={options.MaxFps}",
            $"--window-title={options.WindowTitle}"
        };

        if (options.MaxSize > 0)
            args.Add($"--max-size={options.MaxSize}");

        if (options.DisableAudio)
        {
            args.Add("--no-audio");
        }
        else
        {
            args.Add($"--audio-codec={options.AudioCodec.ToLowerInvariant()}");
            args.Add($"--audio-bit-rate={options.AudioBitRateKbps}K");
            args.Add($"--audio-buffer={options.AudioBufferMs}");
            if (options.UsePlaybackCapture)
                args.Add("--audio-source=playback");
            if (options.KeepAudioOnPhone)
                args.Add("--audio-dup");
        }

        if (options.ReadOnly)
            args.Add("--no-control");
        if (options.StayAwake)
            args.Add("--stay-awake");
        if (options.TurnScreenOff)
            args.Add("--turn-screen-off");
        if (options.Fullscreen)
            args.Add("--fullscreen");
        if (options.Borderless)
            args.Add("--window-borderless");
        if (options.AlwaysOnTop)
            args.Add("--always-on-top");
        if (!string.IsNullOrWhiteSpace(options.RecordPath))
            args.Add($"--record={options.RecordPath}");

        return args;
    }
}
