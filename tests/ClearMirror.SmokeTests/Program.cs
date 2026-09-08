using ClearMirror.Core;

var failures = new List<string>();

void Check(bool condition, string name)
{
    if (!condition)
        failures.Add(name);
}

var adbOutput = """
List of devices attached
R58M123ABC             device product:beyond2lte model:SM_G975F device:beyond2 transport_id:1
192.168.1.25:5555      unauthorized product:foo model:Pixel_8 device:bar transport_id:2
""";

var devices = AdbDeviceParser.Parse(adbOutput);
Check(devices.Count == 2, "ADB parser count");
Check(devices[0].IsReady, "ADB ready state");
Check(devices[0].Model == "SM_G975F", "ADB model");
Check(!devices[1].IsReady, "ADB unauthorized state");

var argsList = ScrcpyArgumentBuilder.Build(new MirrorOptions
{
    Serial = "R58M123ABC",
    MaxSize = 1920,
    MaxFps = 60,
    VideoCodec = "h265",
    VideoBitRateMbps = 20,
    AudioCodec = "opus",
    AudioBitRateKbps = 192,
    AudioBufferMs = 50,
    KeepAudioOnPhone = true,
    Borderless = true,
    AlwaysOnTop = true,
    RecordPath = @"C:\Records\test capture.mkv"
});

Check(argsList.Contains("--max-size=1920"), "resolution argument");
Check(argsList.Contains("--video-codec=h265"), "video codec argument");
Check(argsList.Contains("--audio-codec=opus"), "audio codec argument");
Check(argsList.Contains("--audio-dup"), "audio duplication argument");
Check(argsList.Contains(@"--record=C:\Records\test capture.mkv"), "record path argument");
Check(argsList.Contains("--window-borderless") && argsList.Contains("--always-on-top"), "OBS arguments");

var gameMicAudio = ScrcpyArgumentBuilder.Build(new MirrorOptions { Serial = "test", UsePlaybackCapture = true });
Check(gameMicAudio.Contains("--audio-source=playback"), "game mic mode uses alternate playback capture");
Check(!gameMicAudio.Contains("--no-audio") && gameMicAudio.Contains("--audio-codec=opus"), "game mic mode retains phone audio forwarding");
Check(!gameMicAudio.Any(a => a.StartsWith("--audio-source=mic")), "game mic mode does not substitute phone microphone for game audio");
var mutedGameMic = ScrcpyArgumentBuilder.Build(new MirrorOptions { Serial = "test", UsePlaybackCapture = true, DisableAudio = true });
Check(mutedGameMic.Contains("--no-audio") && !mutedGameMic.Contains("--audio-source=playback"), "explicit no-audio overrides alternate capture");
var standardAudio = ScrcpyArgumentBuilder.Build(new MirrorOptions { Serial = "test" });
Check(!standardAudio.Contains("--audio-source=playback"), "standard audio mode remains available for older Android");
var duplicatedGameMic = ScrcpyArgumentBuilder.Build(new MirrorOptions { Serial = "test", UsePlaybackCapture = true, KeepAudioOnPhone = true });
Check(duplicatedGameMic.Contains("--audio-dup") && duplicatedGameMic.Count(a => a == "--audio-source=playback") == 1, "phone playback duplication works with game mic mode");

if (failures.Count > 0)
{
    Console.Error.WriteLine("Smoke tests failed:");
    foreach (var failure in failures)
        Console.Error.WriteLine($" - {failure}");
    return 1;
}

Console.WriteLine("All ClearMirror smoke tests passed.");
return 0;
