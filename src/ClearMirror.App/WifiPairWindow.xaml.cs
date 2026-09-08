using ClearMirror.Core;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace ClearMirror.App;

public partial class WifiPairWindow : Window
{
    private readonly string _adbPath;
    private readonly ObservableCollection<AdbMdnsService> _services = [];
    private bool _connected;

    public string? ConnectedAddress { get; private set; }

    public WifiPairWindow(string adbPath, string? initialAddress)
    {
        InitializeComponent();
        _adbPath = adbPath;
        ServicesList.ItemsSource = _services;

        if (IsAddress(initialAddress))
            ConnectAddressText.Text = initialAddress;
    }

    private async void Window_Loaded(object sender, RoutedEventArgs e) => await ScanAsync();

    private async void Scan_Click(object sender, RoutedEventArgs e) => await ScanAsync();

    private async Task ScanAsync()
    {
        SetBusy(true, "Scanning Wi-Fi…");
        ResultText.Text = "Looking for Android Wireless debugging services on this network…";

        try
        {
            var result = await RunCaptureAsync(_adbPath, ["mdns", "services"], 12_000);
            var services = AdbMdnsServiceParser.Parse(result.Output + Environment.NewLine + result.Error);
            _services.Clear();
            foreach (var service in services)
                _services.Add(service);

            if (_services.Count == 0)
            {
                SetStatus("No devices found", false);
                ResultText.Text = "No discoverable phone found. Keep Wireless debugging on, use the same Wi-Fi, disable VPN, and tap Pair device with pairing code before scanning again.";
                return;
            }

            ServicesList.SelectedIndex = 0;
            var pairingCount = services.Count(service => service.Kind == AdbMdnsServiceKind.Pairing);
            SetStatus($"{services.Count} service{(services.Count == 1 ? string.Empty : "s")} found", true);
            ResultText.Text = pairingCount > 0
                ? "Pairing service found. Select it, type the six-digit phone code, then press Pair & connect."
                : "Phone found. If it is not paired yet, open 'Pair device with pairing code' on the phone and scan again.";
        }
        catch (Exception ex)
        {
            SetStatus("Scan failed", false);
            ResultText.Text = ex.Message;
        }
        finally
        {
            SetBusy(false);
        }
    }

    private void ServicesList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ServicesList.SelectedItem is not AdbMdnsService service)
            return;

        if (service.Kind == AdbMdnsServiceKind.Pairing)
        {
            PairAddressText.Text = service.Address;
            ResultText.Text = "Enter the six-digit code currently shown on the phone. The code expires quickly.";
        }
        else
        {
            ConnectAddressText.Text = service.Address;
            ResultText.Text = "This is the phone's connection service. Previously paired phones can connect directly.";
        }
    }

    private async void Pair_Click(object sender, RoutedEventArgs e)
    {
        var address = PairAddressText.Text.Trim();
        var code = PairCodeText.Password.Trim();
        if (!IsAddress(address))
        {
            ShowValidation("Select a 'Ready to pair' device or enter the pairing IP:port shown on the phone.");
            return;
        }
        if (!Regex.IsMatch(code, "^[0-9]{6}$"))
        {
            ShowValidation("Enter the current six-digit pairing code from the phone.");
            return;
        }

        SetBusy(true, "Pairing…");
        ResultText.Text = $"Pairing with {address}…";
        try
        {
            var result = await RunCaptureAsync(_adbPath, ["pair", address, code], 20_000);
            var message = (result.Output + Environment.NewLine + result.Error).Trim();
            if (result.ExitCode != 0 || !message.Contains("success", StringComparison.OrdinalIgnoreCase))
            {
                SetStatus("Pairing failed", false);
                ResultText.Text = string.IsNullOrWhiteSpace(message) ? "Pairing failed. Generate a new phone code and try again." : message;
                return;
            }

            SetStatus("Paired successfully", true);
            ResultText.Text = "Pairing succeeded. Finding the phone's connection port…";
            PairCodeText.Clear();
            await Task.Delay(800);
            await ScanAsync();

            var pairingIp = address.Split(':')[0];
            var connectService = _services.FirstOrDefault(service =>
                service.Kind == AdbMdnsServiceKind.Connect && service.Address.StartsWith(pairingIp + ":", StringComparison.OrdinalIgnoreCase));

            if (connectService is not null)
            {
                ConnectAddressText.Text = connectService.Address;
                await ConnectAsync(connectService.Address);
            }
            else
            {
                ResultText.Text = "Paired. Select the main IP address & Port from the Wireless debugging page, then press Connect selected device.";
            }
        }
        catch (Exception ex)
        {
            SetStatus("Pairing failed", false);
            ResultText.Text = ex.Message;
        }
        finally
        {
            SetBusy(false);
        }
    }

    private async void Connect_Click(object sender, RoutedEventArgs e)
    {
        var address = ConnectAddressText.Text.Trim();
        if (!IsAddress(address))
        {
            ShowValidation("Select a wireless Android service or enter the main Wireless debugging IP:port.");
            return;
        }

        await ConnectAsync(address);
    }

    private async Task ConnectAsync(string address)
    {
        SetBusy(true, "Connecting…");
        ResultText.Text = $"Connecting to {address}…";
        try
        {
            var result = await RunCaptureAsync(_adbPath, ["connect", address], 15_000);
            var message = (result.Output + Environment.NewLine + result.Error).Trim();
            var success = result.ExitCode == 0 &&
                          (message.Contains("connected to", StringComparison.OrdinalIgnoreCase) ||
                           message.Contains("already connected", StringComparison.OrdinalIgnoreCase));

            if (!success)
            {
                SetStatus("Connection failed", false);
                ResultText.Text = string.IsNullOrWhiteSpace(message)
                    ? "Connection failed. Pair this PC first, then try the main connection port."
                    : message;
                return;
            }

            _connected = true;
            ConnectedAddress = address;
            SetStatus("Phone connected", true);
            ResultText.Text = $"Connected successfully: {address}. Press Done; the phone will appear in ClearMirror's device list.";
        }
        catch (Exception ex)
        {
            SetStatus("Connection failed", false);
            ResultText.Text = ex.Message;
        }
        finally
        {
            SetBusy(false);
        }
    }

    private void Done_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = _connected || !string.IsNullOrWhiteSpace(ConnectedAddress);
        Close();
    }

    private void Cancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }

    private void ShowValidation(string message)
    {
        SetStatus("Check details", false);
        ResultText.Text = message;
    }

    private void SetBusy(bool busy, string? status = null)
    {
        ScanButton.IsEnabled = !busy;
        PairButton.IsEnabled = !busy;
        ConnectButton.IsEnabled = !busy;
        if (!string.IsNullOrWhiteSpace(status))
            SetStatus(status, true);
    }

    private void SetStatus(string text, bool healthy)
    {
        StatusText.Text = text;
        StatusDot.Fill = healthy ? (Brush)FindResource("AccentBrush") : new SolidColorBrush(Color.FromRgb(216, 75, 100));
    }

    private static bool IsAddress(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return false;
        return Regex.IsMatch(value.Trim(), "^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}:[0-9]{1,5}$");
    }

    private static async Task<(int ExitCode, string Output, string Error)> RunCaptureAsync(string fileName, IReadOnlyList<string> args, int timeoutMs)
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
        using var timeout = new CancellationTokenSource(timeoutMs);

        try
        {
            await process.WaitForExitAsync(timeout.Token);
        }
        catch (OperationCanceledException)
        {
            if (!process.HasExited)
                process.Kill(entireProcessTree: true);
            throw new TimeoutException("ADB operation timed out. Check Wi-Fi, firewall, and the phone's Wireless debugging screen.");
        }

        return (process.ExitCode, await outputTask, await errorTask);
    }
}
