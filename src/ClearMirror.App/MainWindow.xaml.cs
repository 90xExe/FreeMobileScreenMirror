using ClearMirror.Core;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace ClearMirror.App;

public partial class MainWindow : Window
{
    private readonly string _scrcpyPath;
    private readonly string _adbPath;
    private readonly string _controlsExePath;
    private Process? _mirrorProcess;
    private Process? _controlsProcess;
    private MicrophoneWindow? _microphoneWindow;
    private bool _isClosing;

    public MainWindow()
    {
        InitializeComponent();
        _scrcpyPath = Path.Combine(AppContext.BaseDirectory, "tools", "scrcpy", "scrcpy.exe");
        _adbPath = Path.Combine(AppContext.BaseDirectory, "tools", "scrcpy", "adb.exe");
        _controlsExePath = Path.Combine(AppContext.BaseDirectory, "tools", "controls", "GamingControlOverlay.exe");
    }

    private async void Window_Loaded(object sender, RoutedEventArgs e)
    {
        AppendLog("ClearMirror started.");
        if (!File.Exists(_scrcpyPath) || !File.Exists(_adbPath))
        {
            SetStatus("Engine missing", false);
            FooterStatusText.Text = "Engine: scrcpy/adb not found in tools\\scrcpy";
            AppendLog("ERROR: Mirroring engine is missing. Re-run Publish.ps1 or copy the official scrcpy bundle into tools\\scrcpy.");
            StartButton.IsEnabled = false;
            return;
        }

        FooterStatusText.Text = "Engine: ready  ·  USB + paired Wi-Fi supported";
        await RefreshDevicesAsync();
    }

    private async void RefreshDevices_Click(object sender, RoutedEventArgs e) => await RefreshDevicesAsync();

    private async Task RefreshDevicesAsync()
    {
        if (!File.Exists(_adbPath))
            return;

        try
        {
            SetStatus("Scanning devices…", true);
            var result = await RunCaptureAsync(_adbPath, ["devices", "-l"]);
            var devices = AdbDeviceParser.Parse(result.Output);
            DeviceCombo.ItemsSource = devices;
            DeviceCombo.SelectedIndex = devices.Count > 0 ? 0 : -1;

            if (devices.Count == 0)
            {
                SetStatus("No phone connected", false);
                AppendLog("No Android device found. For USB, enable USB debugging and allow the phone prompt. For Wi-Fi, open Wireless setup and pair the phone.");
            }
            else
            {
                var ready = devices.Count(d => d.IsReady);
                SetStatus(ready > 0 ? $"{ready} device ready" : "Authorize phone", ready > 0);
                AppendLog($"Found {devices.Count} device(s). Ready: {ready}.");
            }
        }
        catch (Exception ex)
        {
            SetStatus("ADB error", false);
            AppendLog($"ADB error: {ex.Message}");
        }
    }

    private void DeviceCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (DeviceCombo.SelectedItem is AdbDevice device)
            AppendLog($"Selected: {device.DisplayName}");
    }

    private async void WifiConnect_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new WifiPairWindow(_adbPath, WifiAddressText.Text.Trim())
        {
            Owner = this
        };

        AppendLog("Opened Wireless setup: scan, pair, and connect Android devices inside ClearMirror.");
        if (dialog.ShowDialog() == true)
        {
            if (!string.IsNullOrWhiteSpace(dialog.ConnectedAddress))
                WifiAddressText.Text = dialog.ConnectedAddress;
            AppendLog($"Wireless connection ready: {dialog.ConnectedAddress ?? "paired device"}.");
            await RefreshDevicesAsync();
        }
    }

    private async void StartMirror_Click(object sender, RoutedEventArgs e)
    {
        if (_mirrorProcess is { HasExited: false })
            return;
        if (DeviceCombo.SelectedItem is not AdbDevice device)
        {
            MessageBox.Show(this, "Connect and select an Android phone first.", "No device", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }
        if (!device.IsReady)
        {
            MessageBox.Show(this, "Unlock the phone and allow the USB debugging permission, then refresh devices.", "Device not authorized", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        var usePlaybackCapture = GameMicAudioCheck.IsChecked == true && MuteCheck.IsChecked != true;
        if (usePlaybackCapture)
        {
            StartButton.IsEnabled = false;
            try
            {
                using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(8));
                var version = await RunCaptureAsync(_adbPath, ["-s", device.Serial, "shell", "getprop", "ro.build.version.sdk"], timeout.Token);
                if (_isClosing) return;
                if (version.ExitCode != 0 || !int.TryParse(version.Output.Trim(), out var sdk))
                    throw new InvalidOperationException("Could not read the phone's Android version. Reconnect the phone and try again.");
                if (sdk < 33)
                {
                    AppendLog("Game mic audio mode needs Android 13+. Turn it off to use standard audio capture on this phone.");
                    MessageBox.Show(this, "Game mic audio mode requires Android 13 or later. Turn it off and start again for standard capture.", "Audio mode not supported", MessageBoxButton.OK, MessageBoxImage.Information);
                    return;
                }
            }
            catch (Exception ex)
            {
                AppendLog(ex is OperationCanceledException ? "Audio compatibility check timed out. Reconnect the phone and try again." : ex.Message);
                return;
            }
            finally
            {
                if (!_isClosing) StartButton.IsEnabled = true;
            }
        }

        string? recordPath = null;
        if (RecordCheck.IsChecked == true)
        {
            var recordings = Path.Combine(AppContext.BaseDirectory, "Recordings");
            Directory.CreateDirectory(recordings);
            recordPath = Path.Combine(recordings, $"ClearMirror_{DateTime.Now:yyyy-MM-dd_HH-mm-ss}.mkv");
        }

        var options = new MirrorOptions
        {
            Serial = device.Serial,
            MaxSize = TagInt(ResolutionCombo),
            MaxFps = TagInt(FpsCombo),
            VideoCodec = TagString(VideoCodecCombo),
            VideoBitRateMbps = TagInt(VideoBitrateCombo),
            AudioCodec = TagString(AudioCodecCombo),
            AudioBitRateKbps = TagInt(AudioBitrateCombo),
            AudioBufferMs = TagInt(AudioBufferCombo),
            DisableAudio = MuteCheck.IsChecked == true,
            KeepAudioOnPhone = KeepPhoneAudioCheck.IsChecked == true,
            UsePlaybackCapture = usePlaybackCapture,
            ReadOnly = ReadOnlyCheck.IsChecked == true,
            StayAwake = true,
            TurnScreenOff = ScreenOffCheck.IsChecked == true,
            Borderless = ObsModeCheck.IsChecked == true,
            AlwaysOnTop = ObsModeCheck.IsChecked == true,
            RecordPath = recordPath
        };

        try
        {
            var arguments = ScrcpyArgumentBuilder.Build(options);
            var startInfo = new ProcessStartInfo
            {
                FileName = _scrcpyPath,
                WorkingDirectory = Path.GetDirectoryName(_scrcpyPath)!,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            foreach (var argument in arguments)
                startInfo.ArgumentList.Add(argument);

            _mirrorProcess = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
            _mirrorProcess.OutputDataReceived += (_, eventArgs) => AppendLogFromWorker(eventArgs.Data);
            _mirrorProcess.ErrorDataReceived += (_, eventArgs) => AppendLogFromWorker(eventArgs.Data);
            _mirrorProcess.Exited += MirrorProcess_Exited;

            AppendLog($"Starting {options.MaxSize switch { 0 => "native", _ => options.MaxSize + "px" }} / {options.MaxFps} FPS / {options.VideoCodec.ToUpperInvariant()}…");
            if (usePlaybackCapture)
                AppendLog("Game mic audio mode: using Android playback capture. App capture restrictions and voice-call audio may still limit what is heard.");
            _mirrorProcess.Start();
            _mirrorProcess.BeginOutputReadLine();
            _mirrorProcess.BeginErrorReadLine();

            StartButton.IsEnabled = false;
            StopButton.IsEnabled = true;
            SetStatus("Mirroring live", true);
            if (recordPath is not null)
                AppendLog($"Recording: {recordPath}");
        }
        catch (Exception ex)
        {
            SetStatus("Start failed", false);
            AppendLog($"Could not start mirroring: {ex.Message}");
            StartButton.IsEnabled = true;
            StopButton.IsEnabled = false;
        }
    }

    private void StopMirror_Click(object sender, RoutedEventArgs e) => StopMirror();

    private void StopMirror()
    {
        _microphoneWindow?.StopRouting("PC mic stopped with mirroring.");
        try
        {
            if (_mirrorProcess is { HasExited: false })
            {
                AppendLog("Stopping mirror…");
                _mirrorProcess.Kill(entireProcessTree: true);
            }
        }
        catch (Exception ex)
        {
            AppendLog($"Stop warning: {ex.Message}");
        }
    }

    private void MirrorProcess_Exited(object? sender, EventArgs e)
    {
        if (_isClosing)
            return;

        Dispatcher.Invoke(() =>
        {
            if (!ReferenceEquals(sender, _mirrorProcess)) return;
            var exitCode = _mirrorProcess?.ExitCode ?? -1;
            _microphoneWindow?.StopRouting("PC mic stopped because mirroring ended.");
            StopControls();
            AppendLog($"Mirror closed (exit code {exitCode}).");
            StartButton.IsEnabled = true;
            StopButton.IsEnabled = false;
            SetStatus("Ready", true);
        });
    }

    private void ObsModeCheck_Changed(object sender, RoutedEventArgs e)
    {
        if (ObsModeCheck.IsChecked == true)
            AppendLog("OBS clean window enabled. Add 'ClearMirror Preview' as Window Capture in OBS.");
    }

    private void GamingControls_Click(object sender, RoutedEventArgs e)
    {
        if (_mirrorProcess is not { HasExited: false })
        {
            MessageBox.Show(this, "Start mirroring first, then press Gaming Controls.", "Mirror is not running", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }
        if (ReadOnlyCheck.IsChecked == true)
        {
            MessageBox.Show(this, "Turn off 'View only' and restart mirroring. View-only mode blocks PC control.", "PC control is disabled", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        if (!File.Exists(_controlsExePath))
        {
            MessageBox.Show(this, "The Gaming Controls component is missing. Reinstall or republish ClearMirror.", "Gaming Controls missing", MessageBoxButton.OK, MessageBoxImage.Error);
            AppendLog("ERROR: tools\\controls\\GamingControlOverlay.exe was not found.");
            return;
        }
        if (_controlsProcess is { HasExited: false })
        {
            AppendLog("Gaming Controls is already open. Press F12 to show/edit the active overlay.");
            return;
        }

        try
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = _controlsExePath,
                WorkingDirectory = Path.GetDirectoryName(_controlsExePath)!,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            startInfo.ArgumentList.Add("--target-title");
            startInfo.ArgumentList.Add("ClearMirror Preview");
            startInfo.ArgumentList.Add("--auto-apply");

            _controlsProcess = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
            _controlsProcess.Exited += (_, _) =>
            {
                if (!_isClosing)
                    Dispatcher.BeginInvoke(() => AppendLog("Gaming Controls closed."));
            };
            _controlsProcess.Start();
            AppendLog("Gaming Controls opened. ClearMirror Preview and the first saved profile will be selected automatically.");
        }
        catch (Exception ex)
        {
            AppendLog($"Could not open Gaming Controls: {ex.Message}");
            MessageBox.Show(this, ex.Message, "Could not open Gaming Controls", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void StopControls()
    {
        try
        {
            if (_controlsProcess is { HasExited: false })
                _controlsProcess.Kill(entireProcessTree: true);
        }
        catch (Exception ex)
        {
            AppendLog($"Gaming Controls stop warning: {ex.Message}");
        }
    }

    private void AdbHelp_Click(object sender, RoutedEventArgs e)
    {
        MessageBox.Show(this,
            "USB:\n1. Enable Developer options and USB debugging.\n2. Select File transfer / Android Auto.\n3. Connect a data cable, unlock the phone, and tap Allow.\n\nWi-Fi:\n1. Use the same Wi-Fi network.\n2. Enable Wireless debugging.\n3. Press Connect over Wi-Fi to scan and pair inside ClearMirror.",
            "Connect Android", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void ClearLog_Click(object sender, RoutedEventArgs e) => LogText.Clear();

    private void Microphone_Click(object sender, RoutedEventArgs e)
    {
        if (_microphoneWindow is not null)
        {
            if (_microphoneWindow.WindowState == WindowState.Minimized)
                _microphoneWindow.WindowState = WindowState.Normal;
            _microphoneWindow.Activate();
            return;
        }
        _microphoneWindow = new MicrophoneWindow(AppendLog) { Owner = this };
        _microphoneWindow.Closed += (_, _) => _microphoneWindow = null;
        _microphoneWindow.Show();
    }

    private void Window_Closing(object? sender, CancelEventArgs e)
    {
        _isClosing = true;
        _microphoneWindow?.Close();
        StopMirror();
        StopControls();
    }

    private void SetStatus(string text, bool healthy)
    {
        HeaderStatusText.Text = text;
        HeaderStatusDot.Fill = healthy ? (Brush)FindResource("AccentBrush") : new SolidColorBrush(Color.FromRgb(216, 75, 100));
    }

    private void AppendLog(string message)
    {
        if (string.IsNullOrWhiteSpace(message))
            return;
        LogText.AppendText($"[{DateTime.Now:HH:mm:ss}] {message.Trim()}{Environment.NewLine}");
        LogText.ScrollToEnd();
    }

    private void AppendLogFromWorker(string? message)
    {
        if (!string.IsNullOrWhiteSpace(message))
            Dispatcher.BeginInvoke(() => AppendLog(message));
    }

    private static int TagInt(ComboBox comboBox) => int.Parse(TagString(comboBox));

    private static string TagString(ComboBox comboBox)
    {
        if (comboBox.SelectedItem is ComboBoxItem item && item.Tag is not null)
            return item.Tag.ToString()!;
        throw new InvalidOperationException($"A value is not selected for {comboBox.Name}.");
    }

    private static async Task<(int ExitCode, string Output, string Error)> RunCaptureAsync(string fileName, IReadOnlyList<string> args, CancellationToken cancellationToken = default)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = fileName,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        foreach (var arg in args)
            startInfo.ArgumentList.Add(arg);

        using var process = Process.Start(startInfo) ?? throw new InvalidOperationException($"Could not start {Path.GetFileName(fileName)}.");
        var outputTask = process.StandardOutput.ReadToEndAsync();
        var errorTask = process.StandardError.ReadToEndAsync();
        try { await process.WaitForExitAsync(cancellationToken); }
        catch (OperationCanceledException)
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
            catch (InvalidOperationException) { }
            throw;
        }
        return (process.ExitCode, await outputTask, await errorTask);
    }
}
