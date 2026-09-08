# Architecture

ClearMirror is a Windows launcher/controller around external scrcpy and ADB processes. It is not an Android firmware, driver, emulator or replacement scrcpy server.

## Projects and responsibilities

| Location | Responsibility |
| --- | --- |
| `src/ClearMirror.Core` | Mirror options, scrcpy argument construction, ADB device and mDNS parsing; targets `net8.0` |
| `src/ClearMirror.Audio` | WASAPI endpoint discovery, capture/playback bridge, bounded live audio buffer; targets `net8.0-windows` |
| `src/ClearMirror.App` | WPF main window, wireless pairing dialog, microphone window, process lifecycle; targets `net8.0-windows` |
| `control-overlay-src` | Optional PyQt5 overlay, keyboard/mouse hooks, saved control profiles and PyInstaller spec |
| `tests` | Console smoke checks and isolated PowerShell publishing tests |
| `scripts/Publish.ps1` | Build staging and portable distribution copy |

## Mirroring and pairing

`MainWindow` locates tools relative to the app executable. ADB discovers/selects devices, while `ScrcpyArgumentBuilder` maps UI options to command arguments. scrcpy owns the video/audio transport, phone encoding, preview and MKV recording. The preview title is `ClearMirror Preview`.

`WifiPairWindow` scans ADB mDNS services, accepts the phone's current pairing code, pairs, and connects to the device's connection endpoint. Pairing and connection ports can differ. The Core parser tests use synthetic device IDs and example addresses.

The game-mic audio option checks `ro.build.version.sdk` through ADB with an eight-second timeout. It requires API 33 (Android 13) and selects playback capture. Older or unreadable API levels are reported to the user instead of starting that mode.

## PC audio bridge

`AudioDevices` lists active Windows input/output endpoints. `MicrophoneBridge` opens the selected endpoints using NAudio WASAPI in shared mode. Audio goes through `LiveMicrophoneBuffer`, a bounded 48 kHz mono float buffer, before rendering to the chosen output.

The default buffer retains at most 120 ms of microphone samples. Overflow drops the oldest audio, underrun supplies silence, gain controls the send level, and peak values feed the input/output meters. Muting clears retained speech and suppresses outgoing speech while input monitoring stays active. Errors stop/dispose the session instead of silently switching outputs.

The bridge ends at the Windows output device. External hardware supplies the remaining route to Android. See [PC-MIC.md](PC-MIC.md).

## Gaming overlay

The C# app starts `tools/controls/GamingControlOverlay.exe` with `--target-title "ClearMirror Preview" --auto-apply`. The independent Python process discovers the target window and applies an editable profile. Coordinates are proportional to the target window; each game/HUD still needs calibration.

Profiles live beside `main.py` in source mode or beside the EXE in packaged mode. If no local file exists, the overlay can copy an old `%APPDATA%/GamingControlOverlay/profiles.json` into its local location. The repository includes only a sanitized `profiles.example.json`.

## Runtime files

```text
ClearMirror.exe
... .NET app files ...
tools/scrcpy/                 Complete official engine bundle
tools/controls/              Optional overlay EXE and local profiles.json
Recordings/                  User-created MKV recordings
```

The PC mic feature processes live audio without saving it. Recordings are created by the separate, explicitly enabled scrcpy recording option. Pairing communicates through ADB; the project adds no cloud service or account requirement.

## Where to make changes

- Add a mirroring option in Core, expose it in WPF, and test the resulting arguments.
- Change endpoint/session behavior in Audio; verify buffer semantics and separately test real hardware.
- Change wireless parsing in Core and exercise malformed, pairing and connection entries.
- Change key mapping or editor behavior in the Python overlay and test against a real target window.
- Keep Android compatibility and hardware limitations synchronized with the user guides.
