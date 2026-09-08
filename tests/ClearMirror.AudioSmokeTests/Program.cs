using ClearMirror.Audio;
using ClearMirror.App;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

internal static class Program
{
    private static readonly List<string> Failures = [];
    private static int _checks;

    private static void Check(bool condition, string name)
    {
        _checks++;
        if (!condition) Failures.Add(name);
    }

    private static void Throws<T>(Action action, string name) where T : Exception
    {
        try { action(); Check(false, name); }
        catch (T) { Check(true, name); }
    }

    private static byte[] Bytes(params float[] samples) => MemoryMarshal.AsBytes(samples.AsSpan()).ToArray();
    private static float[] Read(LiveMicrophoneBuffer stream, int count)
    {
        var bytes = new byte[count * 4];
        Check(stream.Read(bytes, 0, bytes.Length) == bytes.Length, "live read always pads to requested size");
        return MemoryMarshal.Cast<byte, float>(bytes).ToArray();
    }

    [STAThread]
    private static int Main(string[] args)
    {
        try { return Run(args); }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Audio test setup failed: {ex}");
            return 1;
        }
    }

    private static int Run(string[] args)
    {
        var stream = new LiveMicrophoneBuffer(20) { Gain = 0.5f };
        var speech = Bytes(0.8f, -0.6f, 0.2f);
        stream.Write(speech, speech.Length);
        Check(Read(stream, 5).SequenceEqual(new[] { 0.4f, -0.3f, 0.1f, 0f, 0f }), "gain, sample order and underrun silence");
        var peaks = stream.TakePeaks();
        Check(peaks.Input == 0.8f && peaks.Output == 0.4f, "input and output meters reflect distinct levels");
        Check(stream.TakePeaks() == (0, 0), "meters reset after polling");

        stream.Write(speech, speech.Length);
        stream.Muted = true;
        stream.Write(speech, speech.Length);
        Check(Read(stream, 3).All(s => s == 0), "mute sends silence");
        Check(stream.TakePeaks().Input == 0.8f, "input meter remains live during mute");
        stream.Muted = false;
        Check(Read(stream, 3).All(s => s == 0), "unmute never replays queued or muted speech");
        Check(stream.ReceivedSamples == 9, "capture accounting includes muted frames");

        var overflow = new LiveMicrophoneBuffer(20) { Gain = 1 };
        var first = Bytes(Enumerable.Repeat(0.25f, 900).ToArray());
        var second = Bytes(Enumerable.Repeat(0.75f, 300).ToArray());
        overflow.Write(first, first.Length);
        Check(Read(overflow, 800).All(s => s == 0.25f), "initial circular-buffer read");
        overflow.Write(first, first.Length); // Wrap and discard 40 old samples.
        overflow.Write(second, second.Length); // Discard another 300, retain newest speech.
        var retained = Read(overflow, 960);
        Check(retained.Take(660).All(s => s == 0.25f) && retained.Skip(660).All(s => s == 0.75f), "wraparound retains newest audio in order");
        Check(overflow.DroppedSamples == 340, "overflow drops exactly the oldest frames");

        var oversized = Bytes(Enumerable.Repeat(-0.5f, 2000).Concat(Enumerable.Repeat(0.9f, 960)).ToArray());
        overflow.Write(oversized, oversized.Length);
        Check(overflow.BufferedSamples == 960 && Read(overflow, 960).All(s => s == 0.9f), "oversized packet cannot increase latency beyond capacity");

        var invalid = Bytes(float.NaN, float.PositiveInfinity, 2, -2);
        overflow.Write(invalid, invalid.Length);
        Check(Read(overflow, 4).SequenceEqual(new[] { 0f, 0f, 1f, -1f }), "nonfinite and clipped samples do not corrupt output");
        Throws<ArgumentOutOfRangeException>(() => overflow.Gain = float.NaN, "reject NaN gain");
        Throws<ArgumentOutOfRangeException>(() => overflow.Gain = 2, "reject excessive gain");
        Throws<ArgumentOutOfRangeException>(() => overflow.Write(new byte[5], 5), "reject incomplete samples");
        Throws<ArgumentOutOfRangeException>(() => overflow.Read(new byte[4], 3, 4), "reject invalid read bounds");
        Throws<ArgumentOutOfRangeException>(() => new LiveMicrophoneBuffer(0), "reject zero-length live buffer");

        var concurrent = new LiveMicrophoneBuffer(40) { Gain = 1 };
        Parallel.Invoke(
            () => { for (var i = 0; i < 1000; i++) concurrent.Write(speech, speech.Length); },
            () => { var data = new byte[256]; for (var i = 0; i < 1000; i++) concurrent.Read(data, 0, data.Length); },
            () => { for (var i = 0; i < 1000; i++) { concurrent.Muted = (i % 2 == 0); concurrent.Gain = 0.4f; } });
        concurrent.Muted = true;
        concurrent.Muted = false;
        Check(concurrent.BufferedSamples == 0 && Read(concurrent, 100).All(s => s == 0), "concurrent capture, playback and mute leave no stale speech");

        var disposed = new MicrophoneBridge();
        disposed.Dispose();
        disposed.Dispose();
        Throws<ObjectDisposedException>(() => disposed.Start("input", "output"), "disposed session cannot reopen mic");
        using (var rejected = new MicrophoneBridge())
            Throws<ArgumentException>(() => rejected.Start("input", ""), "no implicit default output");

        if (args.Contains("--devices"))
        {
            var inputs = AudioDevices.GetInputs();
            var outputs = AudioDevices.GetOutputs();
            Console.WriteLine($"Windows devices: {inputs.Count} input(s), {outputs.Count} output(s).");
            foreach (var input in inputs) Console.WriteLine($"  Input: {input.DisplayName}");
            foreach (var output in outputs) Console.WriteLine($"  Output: {output.DisplayName}");
        }
        if (args.Contains("--capture-smoke"))
        {
            var input = AudioDevices.GetInputs().FirstOrDefault();
            var output = AudioDevices.GetOutputs().FirstOrDefault();
            if (input is null || output is null)
                Check(false, "hardware smoke requires a PC microphone and output");
            else
            {
                for (var run = 0; run < 2; run++)
                {
                    using var bridge = new MicrophoneBridge();
                    bridge.Buffer.Muted = true; // Open real devices but emit only silence. No audio is saved.
                    string? error = null;
                    bridge.Faulted += (_, message) => error = message;
                    bridge.Start(input.Id, output.Id);
                    Thread.Sleep(1000);
                    Check(error is null && bridge.Buffer.ReceivedSamples >= 4800, $"real WASAPI capture and muted output, session {run + 1}: {error}");
                    Check(bridge.Buffer.TakePeaks().Output == 0, "hardware smoke emitted silence only");
                    Console.WriteLine($"Muted hardware session {run + 1}: {bridge.Buffer.ReceivedSamples} samples captured, no audio saved.");
                }
            }
        }

        var renderIndex = Array.IndexOf(args, "--render");
        if (renderIndex >= 0)
        {
            var directory = Path.GetFullPath(args[renderIndex + 1]);
            Directory.CreateDirectory(directory);
            var app = new App { ShutdownMode = ShutdownMode.OnExplicitShutdown };
            app.InitializeComponent();
            Render(new MicrophoneWindow(_ => { }), 764, 760, Path.Combine(directory, "microphone.png"));
            Render(new MicrophoneWindow(_ => { }), 634, 580, Path.Combine(directory, "microphone-min.png"));
            Render(new MainWindow(), 1164, 750, Path.Combine(directory, "main.png"));
            Render(new MainWindow(), 1014, 660, Path.Combine(directory, "main-min.png"));
            app.Shutdown();
        }

        foreach (var failure in Failures) Console.Error.WriteLine($"FAIL: {failure}");
        Console.WriteLine($"{_checks - Failures.Count}/{_checks} audio checks passed.");
        return Failures.Count == 0 ? 0 : 1;
    }

    private static void Render(Window window, int width, int height, string path)
    {
        if (window is MicrophoneWindow)
        {
            var input = (ComboBox)window.FindName("InputCombo");
            input.ItemsSource = new[] { new AudioEndpoint("layout-input", "Microphone (layout sample)", true) };
            input.SelectedIndex = 0;
            var output = (ComboBox)window.FindName("OutputCombo");
            output.ItemsSource = new[] { new AudioEndpoint("layout-output", "Wired output (layout sample)", true) };
            output.SelectedIndex = 0; // Exercise the longer default-output warning without starting audio.
        }
        var root = (FrameworkElement)window.Content;
        root.Measure(new Size(width, height));
        root.Arrange(new Rect(0, 0, width, height));
        root.UpdateLayout();
        var bitmap = new RenderTargetBitmap(width, height, 96, 96, PixelFormats.Pbgra32);
        var background = new DrawingVisual();
        using (var drawing = background.RenderOpen())
            drawing.DrawRectangle(window.Background, null, new Rect(0, 0, width, height));
        bitmap.Render(background);
        bitmap.Render(root);
        var png = new PngBitmapEncoder();
        png.Frames.Add(BitmapFrame.Create(bitmap));
        using var file = File.Create(path);
        png.Save(file);
        var start = (Button)window.FindName("StartButton");
        var bounds = start.TransformToAncestor(root).TransformBounds(new Rect(start.RenderSize));
        Check(bounds.Bottom <= root.ActualHeight + 1 && bounds.Right <= root.ActualWidth + 1, $"start button visible at {width} x {height}");
        if (window is MicrophoneWindow)
        {
            var mute = (CheckBox)window.FindName("MuteCheck");
            var muteBounds = mute.TransformToAncestor(root).TransformBounds(new Rect(mute.RenderSize));
            Check(muteBounds.Bottom <= root.ActualHeight + 1 && muteBounds.Right <= root.ActualWidth + 1, $"mute always visible at {width} x {height}");
            if (width == 764)
            {
                var meter = (ProgressBar)window.FindName("OutputMeter");
                var status = (TextBlock)window.FindName("StatusText");
                Check(meter.TransformToAncestor(root).Transform(new Point(0, meter.ActualHeight)).Y < status.TransformToAncestor(root).Transform(new Point()).Y - 20,
                    "both meters visible at the default mic window size");
            }
        }
        window.Close();
    }
}
