using System.Runtime.InteropServices;
using NAudio.Wave;

namespace ClearMirror.Audio;

/// <summary>A bounded live stream. Overflow drops old speech instead of accumulating delay.</summary>
public sealed class LiveMicrophoneBuffer : IWaveProvider
{
    private readonly object _gate = new();
    private readonly float[] _samples;
    private int _head;
    private int _count;
    private float _gain = 0.2f;
    private bool _muted;
    private float _inputPeak;
    private float _outputPeak;
    private long _receivedSamples;
    private long _droppedSamples;

    public LiveMicrophoneBuffer(int bufferMilliseconds = 120)
    {
        if (bufferMilliseconds is < 20 or > 500)
            throw new ArgumentOutOfRangeException(nameof(bufferMilliseconds));
        _samples = new float[48 * bufferMilliseconds];
    }

    public WaveFormat WaveFormat { get; } = WaveFormat.CreateIeeeFloatWaveFormat(48000, 1);
    public int BufferedSamples { get { lock (_gate) return _count; } }
    public long ReceivedSamples { get { lock (_gate) return _receivedSamples; } }
    public long DroppedSamples { get { lock (_gate) return _droppedSamples; } }

    public float Gain
    {
        get { lock (_gate) return _gain; }
        set
        {
            if (!float.IsFinite(value) || value is < 0 or > 1)
                throw new ArgumentOutOfRangeException(nameof(value));
            lock (_gate) _gain = value;
        }
    }

    public bool Muted
    {
        get { lock (_gate) return _muted; }
        set
        {
            lock (_gate)
            {
                _muted = value;
                // Never replay speech captured before or during mute after unmuting.
                _head = _count = 0;
                _outputPeak = 0;
            }
        }
    }

    public void Write(byte[] data, int count)
    {
        ArgumentNullException.ThrowIfNull(data);
        if (count < 0 || count > data.Length || count % sizeof(float) != 0)
            throw new ArgumentOutOfRangeException(nameof(count));
        var incoming = MemoryMarshal.Cast<byte, float>(data.AsSpan(0, count));
        lock (_gate)
        {
            _receivedSamples += incoming.Length;
            foreach (var raw in incoming)
            {
                var sample = float.IsFinite(raw) ? Math.Clamp(raw, -1f, 1f) : 0f;
                _inputPeak = Math.Max(_inputPeak, Math.Abs(sample));
                if (_muted) continue;
                if (_count == _samples.Length)
                {
                    _head = (_head + 1) % _samples.Length;
                    _count--;
                    _droppedSamples++;
                }
                _samples[(_head + _count) % _samples.Length] = sample;
                _count++;
            }
        }
    }

    public int Read(byte[] buffer, int offset, int count)
    {
        ArgumentNullException.ThrowIfNull(buffer);
        if (offset < 0 || count < 0 || offset > buffer.Length - count || count % sizeof(float) != 0)
            throw new ArgumentOutOfRangeException(nameof(count));
        var destination = MemoryMarshal.Cast<byte, float>(buffer.AsSpan(offset, count));
        lock (_gate)
        {
            destination.Clear();
            if (_muted) return count;
            var available = Math.Min(destination.Length, _count);
            for (var i = 0; i < available; i++)
            {
                var sample = _samples[_head] * _gain;
                _head = (_head + 1) % _samples.Length;
                _count--;
                destination[i] = sample;
                _outputPeak = Math.Max(_outputPeak, Math.Abs(sample));
            }
            return count; // An underrun is silence, never end-of-stream.
        }
    }

    public (float Input, float Output) TakePeaks()
    {
        lock (_gate)
        {
            var peaks = (_inputPeak, _outputPeak);
            _inputPeak = _outputPeak = 0;
            return peaks;
        }
    }
}
