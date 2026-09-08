# Tests and validation

Use Windows with the .NET 8 SDK. Commands below run at the repository root. Console smoke tests return a nonzero exit code on failure; they are executable projects, not `dotnet test` framework suites.

## Automated checks

```powershell
dotnet restore ClearMirror.sln
dotnet build ClearMirror.sln -c Release --no-restore
dotnet run --project tests/ClearMirror.SmokeTests -c Release --no-build
dotnet run --project tests/ClearMirror.WifiSmokeTests -c Release --no-build
dotnet run --project tests/ClearMirror.AudioSmokeTests -c Release --no-build
powershell -ExecutionPolicy Bypass -File tests\Test-Publish.ps1
```

| Suite | Coverage |
| --- | --- |
| Core | Device parsing and generated scrcpy options, including playback capture and disabled audio |
| Wi-Fi | mDNS discovery/parsing and pairing-versus-connection endpoint handling |
| Audio | Gain, peaks, mute/unmute, silence, overflow/order, invalid data, concurrency and disposal |
| Publish | Isolated fake compiler; preservation of existing recordings/profiles, successful copy, build failure and staging cleanup |

These checks do not require a phone, scrcpy binaries or an active microphone. `Test-Publish.ps1` tests file handling with disposable synthetic files; it does not compile a real portable app.

The included [GitHub Actions workflow](../.github/workflows/build.yml) runs these same checks on Windows for pushes and pull requests. It does not access a phone/mic, package an overlay, publish a release or deploy anything. Its setup follows the official [setup-dotnet action](https://github.com/actions/setup-dotnet).

## Optional local checks

List real Windows endpoints without starting capture:

```powershell
dotnet run --project tests/ClearMirror.AudioSmokeTests -c Release --no-build -- --devices
```

Explicit hardware smoke test:

```powershell
dotnet run --project tests/ClearMirror.AudioSmokeTests -c Release --no-build -- --capture-smoke
```

This opens the first available PC microphone/output twice for one second each. Output stays muted, and no audio file is saved. It verifies local capture and teardown, not phone reception. Do not use it as a CI requirement.

Render WPF layouts:

```powershell
dotnet run --project tests/ClearMirror.AudioSmokeTests -c Release --no-build -- --render work\layout-check
```

Generated PNGs use labeled sample endpoints for layout inspection. They are not evidence of an active phone connection or working microphone route.

For the optional overlay, after installing its dependencies:

```powershell
.\.venv\Scripts\python.exe control-overlay-src\main.py --smoke-test
```

This briefly initializes the UI/window discovery and keyboard/mouse hooks, then exits with `SMOKE_TEST_OK`. Actual input compatibility still needs a target-window test.

## Manual release checks

1. Start/stop USB mirroring and verify the selected resolution, audio and preview behavior.
2. Pair/connect an Android 11+ phone over Wi-Fi; exercise wrong codes and manual addresses.
3. Make an MKV recording and verify the file plays back.
4. On Android 13+, compare default audio capture with Game mic audio mode while enabling a game's mic. Check failure feedback on an older device.
5. Follow [PC-MIC.md](PC-MIC.md) with real audio hardware; compare mute/unmute in a phone recorder and then each intended app.
6. Stop the mic, close its window, stop mirroring, and disconnect the selected device; verify capture ends as expected.
7. Calibrate the optional gaming profile and check controls, mouse unlock, F12 editing and focus changes.

Report exact phone/Android version, app version, connection type and audio hardware when sharing compatibility results. Redact device serials, pairing codes and personal paths from public logs. Passing the automated suites does not establish universal phone, call or game compatibility.
