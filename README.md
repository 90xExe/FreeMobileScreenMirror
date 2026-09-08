# ClearMirror

Windows app for Android screen mirroring, internal audio, recording, and keyboard/mouse controls, powered by [scrcpy](https://github.com/Genymobile/scrcpy).

**Version 1.1.1 · Windows 10/11 · .NET 8 · Tested engine: scrcpy 4.1**

## Features

- Discover Android devices over USB or Wi-Fi; scan and pair through Android Wireless debugging.
- Choose 720p, 1080p, 1440p, or native resolution, with 30–120 FPS caps.
- H.264/H.265 video, Opus/AAC audio, and adjustable bitrate and audio buffering.
- Record mirroring sessions to MKV and use a borderless, always-on-top preview for OBS.
- Optional gaming overlay with editable taps, WASD, fire, mouse look, and saved profiles.
- Route a PC microphone to a selected Windows audio output connected to the phone through suitable audio hardware.
- Input/output meters, send level, mute, and explicit microphone start/stop.
- Android 13+ alternate playback capture mode for games that lose sound when their mic is enabled.

## Compatibility

| Function | Requirement / limit |
| --- | --- |
| USB screen mirroring | Android 5+ and USB debugging |
| Internal phone audio | Android 11+; app/device capture restrictions still apply |
| Six-digit wireless pairing | Android 11+; PC and phone on the same network |
| Android 10 wireless connection | USB-assisted ADB TCP/IP setup; no six-digit pairing |
| Keep audio on phone and PC | Android 13+; some apps block capture |
| Game mic audio mode | Android 13+; alternate playback capture, with no guarantee for every game/call |
| PC mic used by phone apps | Suitable external mic hardware plus a phone/app that accepts that input |

### PC mic: what this feature does

```text
PC microphone → ClearMirror → dedicated PC audio output
              → phone-compatible audio interface/line-to-mic attenuator
              → phone external microphone input → phone app
```

**The ordinary USB/Wi-Fi mirroring connection does not send your PC mic to Android.** A suitable physical audio connection is required. A normal AUX cable is insufficient. Keep game playback on headphones and use a separate PC output for the phone feed.

Android 10 and later can use this external-mic route where the hardware and app support it. WhatsApp, games, and SIM calls must be tested individually. PC meters confirm local audio processing; they do not confirm that the phone has selected the external mic. No all-phone/all-app support is claimed.

See [PC mic setup and limitations](docs/PC-MIC.md) or [বাংলা নির্দেশনা](PC-MIC-SETUP.bn.md).

## Build and run

This repository contains source, documentation, and a sample profile. Download the scrcpy runtime separately; prebuilt executables and personal recordings are excluded.

1. Install the **.NET 8 SDK** on Windows.
2. Download the official **scrcpy 4.1 Windows x64** bundle from [scrcpy releases](https://github.com/Genymobile/scrcpy/releases). Extract its complete contents into `tools/scrcpy` so `scrcpy.exe` and `adb.exe` sit directly there.
3. Open PowerShell at the repository root:

```powershell
dotnet restore ClearMirror.sln
dotnet build ClearMirror.sln -c Release --no-restore
dotnet run --project src/ClearMirror.App -c Release --no-build
```

4. Enable USB debugging on the phone, connect a USB data cable, approve the phone's authorization prompt, select the phone, and press **Start mirroring**.

The optional gaming overlay needs a separate Python build. See [complete build and packaging steps](docs/BUILD.md).

## Documentation

| Guide | Contents |
| --- | --- |
| [User guide](docs/USER-GUIDE.md) | USB/Wi-Fi connection, gaming controls, OBS, settings, troubleshooting |
| [Build guide](docs/BUILD.md) | Dependencies, optional overlay, portable Windows distribution |
| [PC microphone](docs/PC-MIC.md) | Hardware, routing, mute behavior, missing game sound, compatibility |
| [বাংলা PC mic guide](PC-MIC-SETUP.bn.md) | ফোনে PC mic ব্যবহার করার নির্দেশনা |
| [Architecture](docs/ARCHITECTURE.md) | Projects, audio flow, subprocesses, files and extension points |
| [Testing](docs/TESTING.md) | Automated tests, optional hardware checks, manual validation |
| [GitHub upload](docs/GITHUB-UPLOAD.md) | Upload this folder as a repository and share releases |
| [Changelog](CHANGELOG.md) | Changes through 1.1.1 |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | scrcpy, ADB, NAudio, and optional Python/Qt dependencies |

## Repository layout

```text
src/                    C# Core, Audio, and WPF App projects
tests/                  Core, Wi-Fi, audio, and publish checks
control-overlay-src/    Optional Python gaming overlay and example profile
assets/                 App icon and logo
scripts/                Windows publishing script
tools/                  Instructions for separately obtained runtime tools
docs/                   Setup, usage, development, and upload guides
.github/workflows/      Windows build and smoke-test workflow
ClearMirror.sln         .NET solution
```

## Development and license status

See [CONTRIBUTING.md](CONTRIBUTING.md) before changing or reporting behavior. There is no project-wide license selected in this source snapshot. Third-party licenses are listed separately in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
