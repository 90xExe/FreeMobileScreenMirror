using ClearMirror.Audio;
using System.ComponentModel;
using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace ClearMirror.App;

public partial class MicrophoneWindow : Window
{
    private readonly Action<string> _log;
    private readonly DispatcherTimer _meterTimer;
    private MicrophoneBridge? _bridge;
    private bool _refreshing;
    private bool _closed;

    public MicrophoneWindow(Action<string> log)
    {
        _log = log;
        InitializeComponent();
        _meterTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(100) };
        _meterTimer.Tick += Meter_Tick;
    }

    private async void Window_Loaded(object sender, RoutedEventArgs e) => await RefreshDevicesAsync();
    private async void Refresh_Click(object sender, RoutedEventArgs e) => await RefreshDevicesAsync();

    private async Task RefreshDevicesAsync()
    {
        if (_refreshing || _bridge is not null) return;
        _refreshing = true;
        SetControls(false);
        RefreshButton.IsEnabled = false;
        var inputId = (InputCombo.SelectedItem as AudioEndpoint)?.Id;
        var outputId = (OutputCombo.SelectedItem as AudioEndpoint)?.Id;
        try
        {
            var devices = await Task.Run(() => (Inputs: AudioDevices.GetInputs(), Outputs: AudioDevices.GetOutputs()));
            if (_closed) return;
            InputCombo.ItemsSource = devices.Inputs;
            InputCombo.SelectedItem = devices.Inputs.FirstOrDefault(d => d.Id == inputId) ?? devices.Inputs.FirstOrDefault();
            OutputCombo.ItemsSource = devices.Outputs;
            // Never silently redirect a missing device to the PC's speakers.
            OutputCombo.SelectedItem = devices.Outputs.FirstOrDefault(d => d.Id == outputId);
            StatusText.Text = devices.Inputs.Count == 0 ? "No PC microphone found" : devices.Outputs.Count == 0 ? "No audio output found" : "PC mic is off · choose the output wired to your phone";
            DetailText.Text = "Connect the audio cable/interface, then start. USB/Wi-Fi screen mirroring alone does not carry this mic signal.";
        }
        catch (Exception ex)
        {
            InputCombo.ItemsSource = null;
            OutputCombo.ItemsSource = null;
            StatusText.Text = "Could not list Windows audio devices";
            DetailText.Text = ex.Message;
            _log($"PC mic device scan failed: {ex.Message}");
        }
        finally
        {
            _refreshing = false;
            if (!_closed) SetControls(false);
        }
    }

    private void SetControls(bool running)
    {
        InputCombo.IsEnabled = OutputCombo.IsEnabled = LatencyCombo.IsEnabled = !running && !_refreshing;
        RefreshButton.IsEnabled = !running && !_refreshing;
        StartButton.IsEnabled = !running && !_refreshing && InputCombo.Items.Count > 0 && OutputCombo.Items.Count > 0;
        StopButton.IsEnabled = MuteCheck.IsEnabled = running;
    }

    private void Start_Click(object sender, RoutedEventArgs e)
    {
        if (_bridge is not null || _refreshing) return;
        if (InputCombo.SelectedItem is not AudioEndpoint input || OutputCombo.SelectedItem is not AudioEndpoint output)
        {
            StatusText.Text = "Select a PC microphone and the output wired to your phone";
            return;
        }

        var bridge = new MicrophoneBridge();
        try
        {
            MuteCheck.IsChecked = false;
            bridge.Buffer.Gain = (float)(GainSlider.Value / 100);
            bridge.Faulted += Bridge_Faulted;
            _bridge = bridge;
            var latency = int.Parse(((ComboBoxItem)LatencyCombo.SelectedItem).Tag.ToString()!, CultureInfo.InvariantCulture);
            bridge.Start(input.Id, output.Id, latency);
            SetControls(true);
            UpdateRunningStatus();
            _meterTimer.Start();
            _log($"PC mic started: {input.Name} → {output.Name}. Audio cable/interface required; phone input has not been verified.");
        }
        catch (Exception ex)
        {
            StopRouting();
            StatusText.Text = "PC mic could not start";
            DetailText.Text = $"{ex.Message} Check Windows microphone privacy access for desktop apps, reconnect the devices, and refresh.";
            _log($"PC mic failed to start: {ex.Message}");
        }
    }

    private void Bridge_Faulted(MicrophoneBridge bridge, string message)
    {
        if (_closed || Dispatcher.HasShutdownStarted) return;
        Dispatcher.BeginInvoke(() =>
        {
            if (_closed || !ReferenceEquals(_bridge, bridge)) return;
            StopRouting();
            StatusText.Text = "PC mic stopped · audio device error";
            DetailText.Text = $"{message} Reconnect and refresh devices before restarting.";
            _log($"PC mic stopped: {message}");
        });
    }

    public void StopRouting(string? reason = null)
    {
        _meterTimer.Stop();
        var bridge = _bridge;
        _bridge = null;
        if (bridge is not null)
        {
            bridge.Faulted -= Bridge_Faulted;
            bridge.Dispose();
            _log(reason ?? "PC mic stopped.");
        }
        InputMeter.Value = OutputMeter.Value = 0;
        InputDbText.Text = OutputDbText.Text = "—";
        MuteCheck.IsChecked = false;
        StatusText.Text = "PC mic is off";
        DetailText.Text = reason ?? "Microphone capture and output have stopped. Start again when you are ready.";
        SetControls(false);
    }

    private void Stop_Click(object sender, RoutedEventArgs e) => StopRouting();

    private void Gain_Changed(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (GainText is not null) GainText.Text = $"Send level: {e.NewValue:0}%";
        if (_bridge is not null) _bridge.Buffer.Gain = (float)(e.NewValue / 100);
    }

    private void Mute_Changed(object sender, RoutedEventArgs e)
    {
        if (_bridge is null) return;
        _bridge.Buffer.Muted = MuteCheck.IsChecked == true;
        UpdateRunningStatus();
        _log(_bridge.Buffer.Muted ? "PC mic output muted." : "PC mic output unmuted.");
    }

    private void UpdateRunningStatus()
    {
        StatusText.Text = _bridge?.Buffer.Muted == true ? "Mic output muted · PC microphone capture is still active" : "Sending mic to selected PC output · phone input not verified";
        DetailText.Text = "Turn on the mic in your phone app and verify it receives your PC voice. Stop mic releases the Windows microphone.";
    }

    private void Meter_Tick(object? sender, EventArgs e)
    {
        if (_bridge is null) return;
        var peaks = _bridge.Buffer.TakePeaks();
        InputMeter.Value = peaks.Input * 100;
        OutputMeter.Value = peaks.Output * 100;
        InputDbText.Text = Decibels(peaks.Input);
        OutputDbText.Text = Decibels(peaks.Output);
    }

    private static string Decibels(float peak) => peak < 0.0001f ? "−∞ dB" : $"{20 * Math.Log10(peak):0} dB";

    private void Output_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (OutputHintText is null) return;
        OutputHintText.Text = OutputCombo.SelectedItem is AudioEndpoint { IsDefault: true }
            ? "This is Windows default playback. PC/game sounds may also reach the phone. Use headphones as default and a separate wired output for the mic."
            : "This output must be physically wired to the phone's mic input. Selecting it does not create a USB/Wi-Fi microphone connection.";
    }

    private void Guide_Click(object sender, RoutedEventArgs e)
    {
        MessageBox.Show(this,
            "1. Keep your microphone connected to the PC.\n\n" +
            "2. Connect a dedicated PC audio output to the phone's external microphone input through a suitable phone-compatible interface or line-to-mic attenuator. A CTIA headset splitter must expose the MIC input. A USB-C audio adapter must support mic input. A normal stereo AUX cable is not a microphone cable.\n\n" +
            "3. Use PC headphones for game/call playback, and keep them as Windows default playback. In ClearMirror, select the separate output wired to the phone.\n\n" +
            "4. Start PC mic at a low send level. Enable the mic inside the game/calling app. First make a short test in a phone voice recorder, then verify in each target app. Do not assume a moving PC meter proves phone reception.\n\n" +
            "Android 10, 11, 12 and later: this audio-cable route relies on the phone/app accepting an external mic. USB audio on the phone may require Wi-Fi mirroring because the phone's USB port is occupied. Android 10 uses USB-assisted ADB TCP/IP setup, not Android 11's six-digit wireless pairing.\n\n" +
            "The bundled scrcpy 4.1 has no PC-to-phone mic injection. Experimental Android 13+ injection is not included. SIM-call routing depends on the phone; no all-phone/all-app guarantee.\n\n" +
            "Mute sends silence while keeping capture active. Stop, closing this window, stopping mirroring, or exiting ClearMirror stops capture. Windows mic privacy settings must allow desktop apps.",
            "PC microphone connection guide", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void Window_Closing(object? sender, CancelEventArgs e)
    {
        _closed = true;
        StopRouting();
        _meterTimer.Tick -= Meter_Tick;
    }
}
