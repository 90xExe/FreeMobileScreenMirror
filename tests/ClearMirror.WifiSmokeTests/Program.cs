using ClearMirror.Core;

var sample = """
List of discovered mdns services
adb-TESTDEVICE01-baXsyV  _adb-tls-connect._tcp  192.0.2.10:43505
adb-TESTDEVICE01-pair123  _adb-tls-pairing._tcp  192.0.2.10:37125
""";

var services = AdbMdnsServiceParser.Parse(sample);
if (services.Count != 2)
    throw new Exception($"Expected 2 services, got {services.Count}.");
if (services[0].Kind != AdbMdnsServiceKind.Pairing || services[0].Address != "192.0.2.10:37125")
    throw new Exception("Pairing service was not parsed and sorted correctly.");
if (services[1].Kind != AdbMdnsServiceKind.Connect || services[1].Address != "192.0.2.10:43505")
    throw new Exception("Connection service was not parsed correctly.");
if (!services[1].DisplayName.Contains("Wireless Android", StringComparison.Ordinal))
    throw new Exception("Connection display label is incorrect.");

Console.WriteLine("All ClearMirror Wi-Fi smoke tests passed.");

