using NAudio.CoreAudioApi;
using NAudio.Wave;

namespace ClearMirror.Audio;

/// <summary>One explicit PC capture endpoint to one explicit PC playback endpoint.</summary>
/// <remarks>Start/Dispose on the owner thread. A Faulted handler must marshal back there
/// before disposal; WASAPI teardown joins its audio threads.</remarks>
public sealed class MicrophoneBridge : IDisposable
{
    private MMDevice? _inputDevice;
    private MMDevice? _outputDevice;
    private WasapiCapture? _capture;
    private WasapiOut? _output;
    private int _disposed;
    private int _failed;
    private bool _started;

    public LiveMicrophoneBuffer Buffer { get; } = new();
    public event Action<MicrophoneBridge, string>? Faulted;

    public void Start(string inputId, string outputId, int latencyMilliseconds = 60)
    {
        ObjectDisposedException.ThrowIf(_disposed != 0, this);
        if (_started) throw new InvalidOperationException("Create a new microphone session to restart.");
        ArgumentException.ThrowIfNullOrWhiteSpace(inputId);
        ArgumentException.ThrowIfNullOrWhiteSpace(outputId);
        if (latencyMilliseconds is < 30 or > 150)
            throw new ArgumentOutOfRangeException(nameof(latencyMilliseconds));
        _started = true;

        try
        {
            using var enumerator = new MMDeviceEnumerator();
            _inputDevice = enumerator.GetDevice(inputId);
            _outputDevice = enumerator.GetDevice(outputId);
            if (_inputDevice.State != DeviceState.Active || _inputDevice.DataFlow != DataFlow.Capture)
                throw new InvalidOperationException("The selected microphone is no longer available. Refresh devices.");
            if (_outputDevice.State != DeviceState.Active || _outputDevice.DataFlow != DataFlow.Render)
                throw new InvalidOperationException("The selected output is no longer available. Refresh devices.");

            _capture = new WasapiCapture(_inputDevice, false, 20) { WaveFormat = Buffer.WaveFormat };
            _output = new WasapiOut(_outputDevice, AudioClientShareMode.Shared, true, latencyMilliseconds);
            _capture.DataAvailable += Capture_DataAvailable;
            _capture.RecordingStopped += Capture_Stopped;
            _output.PlaybackStopped += Output_Stopped;
            _output.Init(Buffer);
            _capture.StartRecording();
            _output.Play();
        }
        catch
        {
            Dispose();
            throw;
        }
    }

    private void Capture_DataAvailable(object? sender, WaveInEventArgs args)
    {
        if (_disposed != 0 || _failed != 0) return;
        try { Buffer.Write(args.Buffer, args.BytesRecorded); }
        catch (Exception ex) { Fail($"Microphone stream failed: {ex.Message}"); }
    }

    private void Capture_Stopped(object? sender, StoppedEventArgs args)
    {
        if (_disposed == 0)
            Fail(args.Exception is null ? "Microphone capture stopped." : $"Microphone disconnected or unavailable: {args.Exception.Message}");
    }

    private void Output_Stopped(object? sender, StoppedEventArgs args)
    {
        if (_disposed == 0)
            Fail(args.Exception is null ? "Audio output stopped." : $"Audio output disconnected or unavailable: {args.Exception.Message}");
    }

    private void Fail(string message)
    {
        if (Interlocked.Exchange(ref _failed, 1) != 0 || _disposed != 0) return;
        Buffer.Muted = true;
        Faulted?.Invoke(this, message);
    }

    public void Dispose()
    {
        if (Interlocked.Exchange(ref _disposed, 1) != 0) return;
        Buffer.Muted = true;
        if (_capture is not null)
        {
            _capture.DataAvailable -= Capture_DataAvailable;
            _capture.RecordingStopped -= Capture_Stopped;
        }
        if (_output is not null) _output.PlaybackStopped -= Output_Stopped;
        // Attempt every cleanup even when a removed device throws during teardown.
        try { _capture?.Dispose(); }
        catch (Exception ex) { System.Diagnostics.Trace.WriteLine($"Microphone cleanup: {ex}"); }
        finally
        {
            try { _output?.Dispose(); }
            catch (Exception ex) { System.Diagnostics.Trace.WriteLine($"Output cleanup: {ex}"); }
            finally
            {
                _inputDevice?.Dispose();
                _outputDevice?.Dispose();
                _capture = null;
                _output = null;
                _inputDevice = null;
                _outputDevice = null;
            }
        }
    }
}
