# Changelog

## 1.1.1

- Added **Game mic audio mode (Android 13+)** using alternate playback capture, with an Android API check before startup.
- Added argument checks for that mode and its interaction with disabled audio.
- Documented that apps can block capture and that voice/call downlink is not universally available.
- Prepared a standalone GitHub source snapshot with build/testing documentation, a Windows CI workflow, and a sanitized gaming profile.

## 1.1

- Added a selected PC microphone-to-Windows-output bridge for use with a suitable physical phone audio interface.
- Added input/output meters, send level, mute, bounded live buffering and explicit capture lifecycle controls.
- Added audio buffer, optional hardware and WPF layout smoke checks.
- Fixed the audio smoke-test startup crash and added console exception reporting.
- Updated publishing to preserve existing recordings and controller profiles, with isolated file-preservation checks.
- Added English and Bangla microphone setup guidance and hardware/Android limitations.

## Earlier functionality

- USB and wireless Android mirroring through scrcpy, in-app pairing, quality/audio settings, MKV recording, OBS preview options, and integration with a keyboard/mouse gaming overlay.

This snapshot does not reconstruct an earlier commit history or claim that a GitHub release has already been published.
