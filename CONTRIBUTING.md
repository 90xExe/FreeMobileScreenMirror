# Contributing

Use Windows and the .NET 8 SDK; follow [BUILD.md](docs/BUILD.md) and run the relevant checks in [TESTING.md](docs/TESTING.md).

Keep changes focused and describe the behavior before and after the change. Changes to scrcpy arguments, wireless parsing or audio buffering should include meaningful tests in the corresponding smoke-test project. UI and device-routing changes need manual verification as well.

For bug reports, include the ClearMirror version, Windows version, phone model/Android version, USB or Wi-Fi connection, steps to reproduce, expected result and actual result. Audio reports should distinguish missing phone playback from missing PC microphone input, and identify the selected devices and connected interface. Remove personal identifiers and pairing codes from shared logs.

Keep generated binaries, recordings, local `profiles.json`, credentials and machine-specific paths out of commits. Do not claim every phone/game/call is supported based on a local buffer test. Document the exact combinations tested.

This snapshot has no selected project-wide license. See [third-party notices](THIRD_PARTY_NOTICES.md) for the dependencies' existing licenses.
