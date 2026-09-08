# ClearMirror user guide

ClearMirror is a Windows controller for high-quality Android screen and internal-audio mirroring. It uses the official scrcpy engine for fast USB/TCP transport and hardware video encoding on the phone.

## Features

- USB and wireless ADB device discovery
- In-app Wi-Fi scan using Android mDNS services
- In-app six-digit Wireless debugging pairing
- Automatic connect after successful pairing
- 720p, 1080p, 1440p, or native resolution
- 30, 60, 90, or 120 FPS caps
- H.264 and H.265 video at 8-30 Mbps
- Opus or AAC internal audio at 128-256 kbps
- Tunable audio buffer for latency/stability
- Android 13+ audio duplication (phone + PC)
- MKV video/audio recording
- Borderless always-on-top OBS capture mode
- Phone-screen-off and view-only options
- Integrated keyboard and mouse gaming-control overlay
- Automatic `ClearMirror Preview` targeting and saved-profile activation
- PC microphone capture routed to a selected Windows output for a phone-compatible audio cable/interface
- Live input/output meters, adjustable send level, mute, and explicit start/stop

## PC microphone for phone apps (audio cable/interface required)

Press **PC microphone → phone** in the Clear Audio panel. Keep your microphone
connected to the PC, choose that microphone, and choose the **dedicated PC audio
output physically wired to the phone's external mic input**. Start PC mic, then
enable the mic inside the phone app. Mic routing can run without an ADB session.

This is a real Windows capture-to-output bridge, **not microphone injection over
the screen-mirroring USB/Wi-Fi connection**. The bundled scrcpy 4.1 has no client
mic injection option. Android 10, 11, 12 and later can use this hardware route only
when the phone, connected interface, and target app accept an external microphone.
Game chat, WhatsApp and SIM calls must each be verified; all-phone/all-app support
is not claimed. Experimental Android 13+ scrcpy injection is not included.

Audio path:

`PC microphone → ClearMirror → dedicated PC output → suitable interface/attenuator → phone mic input`

- Use a phone-compatible interface, or a correctly attenuated line-to-mic cable
  with the right CTIA headset microphone connection. A normal stereo AUX cable,
  passive headphone splitter, or USB mirroring cable is insufficient. Do not feed
  full line/headphone level directly into a headset mic input.
- A USB-C audio adapter must **support microphone input**, not only headphones.
  When it occupies the phone's USB port, mirror over Wi-Fi if supported. Android
  10 requires USB-assisted ADB TCP/IP setup; the six-digit Wireless debugging
  pairing flow requires Android 11+.
- Keep game/call playback on PC headphones as the Windows default playback
  device. Use a separate output for the phone feed so PC/game sounds do not mix
  into the microphone path. ClearMirror does not change Windows default devices.
- Start with the 20% send level and 60 ms playback buffer. The level control does
  not replace a suitable hardware attenuator. Increase the buffer if it crackles.
- Enable Windows microphone access for desktop apps. No audio is captured until
  **Start PC mic** is pressed. The PC mic stays active while routing; toggling the
  mic inside a phone app does not start/stop Windows capture automatically.
- **Mute mic output** discards queued speech and sends silence while capture and
  the input meter remain active. **Stop mic**, closing the mic window, stopping
  mirroring, or exiting ClearMirror releases the microphone. Unplugged devices
  stop routing; there is no automatic fallback to a different speaker or mic.
- Check a phone recorder first, with the phone away from the PC microphone, then
  test each target app. The PC meters do not prove that the phone is receiving
  this input. SIM-call routing and call playback capture depend on the device.
- Microphone data is processed live in memory; this feature creates no audio
  recordings or network listener. Existing MKV recording is unchanged and does
  not automatically mix in the PC mic.

Bangla setup instructions: [PC-MIC-SETUP.bn.md](../PC-MIC-SETUP.bn.md).

Technical references: [Android USB audio](https://source.android.com/docs/core/audio/usb),
[scrcpy microphone injection proposal](https://github.com/Genymobile/scrcpy/pull/7004),
[NAudio](https://github.com/naudio/NAudio/tree/v2.2.1).

## Phone requirements

- Android 5+ for USB screen mirroring
- Android 11+ for internal audio and modern Wireless debugging pairing
- Developer options enabled
- USB debugging for cable mode, or Wireless debugging for Wi-Fi mode
- PC and phone on the same Wi-Fi for wireless mode

Some apps may block audio capture. Keeping audio on both the phone and PC requires Android 13+ and can also be blocked by an app.

## USB connection

1. On the phone, open **Settings > About phone/device > Version** and tap **Build/Version number** seven times.
2. Open **Developer options**, enable **USB debugging**, and set **Default USB configuration** to **File transfer / Android Auto**.
3. Connect a USB data cable, unlock the phone, and approve the RSA prompt.
4. Start `ClearMirror.exe`, select the detected phone, choose a profile, and press **Start mirroring**.

## Wi-Fi connection inside ClearMirror

1. Connect the PC and phone to the same Wi-Fi (5 GHz recommended).
2. On the phone, enable **Developer options > Wireless debugging**.
3. In ClearMirror, press **Connect over Wi-Fi**. The Wireless setup window scans automatically.
4. On the phone, tap **Pair device with pairing code** and keep that screen open.
5. Press **Scan Wi-Fi** in ClearMirror and select the **Ready to pair** entry.
6. Enter the current six-digit phone code and press **Pair & connect**.
7. ClearMirror sends both the pairing and connection requests. After success, press **Done** and select the phone in the main device list.

Android security requires the phone's current code for the first pairing. After pairing, ClearMirror can normally discover and connect the phone directly while Wireless debugging is enabled. The pairing port and main connection port are usually different.

If scanning returns no devices, keep the pairing-code screen open, disable VPN, avoid guest/public Wi-Fi, and check that the router does not isolate wireless clients. Manual `IP:port` connection remains available in the Wireless setup dialog.

## PC gaming controls

1. Connect the phone and press **Start mirroring**. Leave **View only** disabled.
2. Press **Gaming Controls (keyboard + mouse)**.
3. ClearMirror automatically targets `ClearMirror Preview` and applies the first saved control profile.
4. Click the game preview before playing. Use **W/A/S/D** and the profile's assigned keys.
5. Press **Ctrl** to lock or unlock mouse-look, and **F12** to show/edit the overlay.

Everything remains editable in the Gaming Controls window: target app, profiles, every keyboard or mouse trigger, touch position, control size, W/A/S/D directions, fire button, input mode, mouse-look key and sensitivity, and whether mapped keys are blocked. Create multiple profiles and save them beside the bundled controller EXE.

The optional starter profile is the sanitized `ClearMirror starter` layout in `control-overlay-src/profiles.example.json`. Control positions are proportional to the preview, so use F12 once to adjust any game-specific buttons after changing resolution or HUD layout. Physical-click mode is recommended for games. Do not enable ClearMirror's View-only option while playing.

MSI/BlueStacks `.cfg` files use a different schema and cannot be imported directly. Configure a ClearMirror profile in the editor.

## Recommended quality

For Free Fire/OBS, start with 1080p, 60 FPS, H.265, 20 Mbps, Opus 192 kbps, and a 50 ms audio buffer. If the phone cannot encode H.265, switch to H.264. USB gives the lowest latency; 5 GHz Wi-Fi is the next best option.

## OBS setup

1. Enable **OBS clean window** in ClearMirror.
2. Start mirroring.
3. In OBS, add **Window Capture** and select `ClearMirror Preview`.
4. If OBS does not capture PC audio globally, add **Application Audio Capture** for the scrcpy/ClearMirror preview process.

## Build from source

Requirements: Windows 10/11 and .NET 8 SDK. The optional bundled Gaming Controls component also requires Python, PyQt5 and PyInstaller when rebuilding it.

1. Download the official Windows release from https://github.com/Genymobile/scrcpy/releases.
2. Extract all files into `tools\scrcpy` so that `tools\scrcpy\scrcpy.exe` exists.
3. Put `GamingControlOverlay.exe` and `profiles.json` in `tools\controls`.
4. Run the core tests: `dotnet run --project tests\ClearMirror.SmokeTests\ClearMirror.SmokeTests.csproj -c Release`.
5. Run the Wi-Fi tests: `dotnet run --project tests\ClearMirror.WifiSmokeTests\ClearMirror.WifiSmokeTests.csproj -c Release`.
6. Run the mic tests: `dotnet run --project tests\ClearMirror.AudioSmokeTests -c Release`.
   Optional `-- --devices` enumerates Windows endpoints; `-- --capture-smoke`
   opens a real PC mic and output twice for one second each, with output muted
   and no audio saved. `-- --render <folder>` renders the WPF layouts for inspection.
7. Publish: `powershell -ExecutionPolicy Bypass -File scripts\Publish.ps1`.
   Run `powershell -ExecutionPolicy Bypass -File tests\Test-Publish.ps1` to check
   preservation of existing recordings/profiles and failed-build handling on isolated test files.

The packaged app is written to `dist\ClearMirror`. Publish builds into a temporary
staging directory first, then copies files without deleting existing Recordings
or controller profiles. The PC audio project restores NAudio.Wasapi 2.2.1 and its
NAudio.Core dependency from NuGet.

## Troubleshooting

- **Game audio disappears when enabling the phone's in-game mic:** stop mirroring,
  enable **Game mic audio mode (Android 13+)** in Clear Audio, and start again.
  This selects scrcpy's alternate `playback` capture rather than its default
  remote-submix capture. ClearMirror checks the Android version before starting.
  This is a compatibility workaround, not a guarantee: apps can block capture,
  and voice-communication/call downlink is not universally captured. If sound is
  still missing, turn this mode off to return to the original audio path.
  See [scrcpy audio](https://github.com/Genymobile/scrcpy/blob/master/doc/audio.md).

- **Unauthorized USB device:** unlock the phone, accept the USB debugging prompt, then refresh.
- **USB phone not found:** choose File transfer / Android Auto instead of MIDI or charging-only mode.
- **Wi-Fi phone found but not connected:** tap Pair device with pairing code, scan again, and use the fresh code.
- **No Wi-Fi devices discovered:** use the same network, disable VPN/client isolation, and keep Wireless debugging enabled.
- **No sound:** Android 11+ is required. On Android 11, keep the screen unlocked while starting. Try AAC if the phone lacks an Opus encoder.
- **Black screen/codec error:** switch H.265 to H.264 or reduce resolution/bitrate.
- **Audio crackles:** increase the audio buffer from 50 ms to 100 ms.
- **Gaming keys do nothing:** keep View only disabled, click the preview once, and use Physical click input mode. If needed, run ClearMirror and Gaming Controls at the same Windows privilege level.

