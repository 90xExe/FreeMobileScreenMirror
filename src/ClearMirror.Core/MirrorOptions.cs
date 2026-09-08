namespace ClearMirror.Core;

public sealed record MirrorOptions
{
    public required string Serial { get; init; }
    public int MaxSize { get; init; } = 1920;
    public int MaxFps { get; init; } = 60;
    public string VideoCodec { get; init; } = "h265";
    public int VideoBitRateMbps { get; init; } = 20;
    public string AudioCodec { get; init; } = "opus";
    public int AudioBitRateKbps { get; init; } = 192;
    public int AudioBufferMs { get; init; } = 50;
    public bool DisableAudio { get; init; }
    public bool KeepAudioOnPhone { get; init; }
    public bool UsePlaybackCapture { get; init; }
    public bool ReadOnly { get; init; }
    public bool StayAwake { get; init; } = true;
    public bool TurnScreenOff { get; init; }
    public bool Fullscreen { get; init; }
    public bool Borderless { get; init; }
    public bool AlwaysOnTop { get; init; }
    public string? RecordPath { get; init; }
    public string WindowTitle { get; init; } = "ClearMirror Preview";
}
