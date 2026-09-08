# PC microphone and phone audio

ClearMirror captures a selected Windows microphone and plays that stream through a selected Windows output. To make a phone use it, connect that output to a supported external microphone input on the phone.

## Required audio path

```text
PC mic → ClearMirror → dedicated PC output → suitable audio interface
                                          → phone external mic input

Phone playback → scrcpy → Windows default playback device → PC headphones
```

Use a phone-compatible interface or correctly attenuated line-to-mic connection with the correct CTIA microphone wiring. A plain stereo AUX cable, passive headphone splitter, or the USB mirroring cable does not provide this route. A USB-C adapter must support microphone input. The send-level slider does not replace a hardware attenuator.

Choose headphones as the Windows default playback device, then choose a *different* output for the phone feed. Sending game playback and mic audio to the same phone-feed output mixes those sounds. A PC with only one usable output may need another suitable audio device for separate playback and microphone routing.

Android USB audio support depends on the device and connected accessory; see [Android USB audio documentation](https://source.android.com/docs/core/audio/usb). If the phone's USB port is occupied by the audio interface, use Wi-Fi mirroring where available.

## Start and verify

1. Connect the hardware and enable Windows microphone access for desktop apps.
2. Open **Clear Audio → PC microphone → phone**.
3. Select **PC microphone** and **Output wired to phone**. The latter is a Windows output, not the phone's ADB device entry.
4. Begin with 20% send level and the 60 ms buffer. Press **Start PC mic**.
5. Enable the mic in the phone app. Its mic switch does not automatically start/stop ClearMirror capture.
6. Place the phone away from the PC microphone and test with a phone voice recorder. Compare speech with **Mute mic output** on and off. Then test the actual game or calling app.

Input/output meters show the local stream. They do not prove that the phone is using that stream. If the phone keeps using its built-in mic, inspect the interface, mic-input support and app's selected audio route.

## Controls and lifecycle

| Action | Effect |
| --- | --- |
| Start PC mic | Opens the explicitly selected Windows capture/output devices |
| Send level | Changes the outgoing microphone level |
| Mute mic output | Discards queued speech and sends silence; capture/input meter remain active |
| Unmute | Resumes current audio without replaying old speech |
| Stop mic | Releases capture and playback |
| Close mic window, stop mirroring, or exit app | Stops the microphone bridge |
| Audio device disconnect/failure | Stops routing; no automatic switch to another mic/speaker |

Mic routing can run without an ADB session. It processes audio in memory, creates no microphone recording and opens no network audio listener. It does not mix the PC microphone into the existing MKV recorder.

## Sound disappears when a game enables its mic

On **Android 13+**, stop mirroring, select **Game mic audio mode (Android 13+)** in Clear Audio, and start again. Version 1.1.1 selects scrcpy's alternate `--audio-source=playback` capture. ClearMirror checks the connected phone's Android API level before starting this mode.

This is a capture compatibility workaround. Apps can reject playback capture, and game chat/call downlink may remain unavailable. If it does not help, turn it off and restart mirroring to return to normal capture. **Disable audio** disables capture regardless of this setting. See [scrcpy audio documentation](https://github.com/Genymobile/scrcpy/blob/master/doc/audio.md).

If PC microphone routing itself causes playback trouble, also check that headphones remain the Windows default output and that the phone feed uses a separate device. ClearMirror does not change Windows defaults.

## Compatibility limits

- Android 10 and later can use an external mic where the hardware, phone and app accept it. This is not universal WhatsApp, game or SIM-call compatibility.
- Phone internal-audio mirroring still needs Android 11+; the hardware mic route does not add internal capture to Android 10.
- The bundled/tested scrcpy 4.1 does not provide this app with PC mic injection over USB/Wi-Fi. The experimental [scrcpy microphone injection proposal](https://github.com/Genymobile/scrcpy/pull/7004) is not part of this project.
- No phone APK, root module, universal virtual Android mic, or automatic phone-mic-switch detection is included.
- Build and buffer tests cannot establish compatibility with a particular phone, accessory, game, WhatsApp call or SIM call. Each needs a real test.

[বাংলা setup guide](../PC-MIC-SETUP.bn.md) · [Testing](TESTING.md)
