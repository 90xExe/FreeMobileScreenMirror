# Build and package ClearMirror

Run commands from the repository root in PowerShell unless another location is stated.

## Requirements

- Windows 10/11, x64 for the default portable package.
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0). The runtime alone cannot build source. `global.json` selects an installed stable .NET 8 SDK.
- NuGet access for `NAudio.Wasapi` 2.2.1 and its `NAudio.Core` dependency.
- The complete official Windows scrcpy bundle for actual mirroring. Version 4.1 is the tested engine.
- Optional gaming controls: Python 3 on Windows, PyQt5 from `requirements.txt`, and PyInstaller.

## 1. Add the mirroring engine

Download the Windows x64 archive from [official scrcpy releases](https://github.com/Genymobile/scrcpy/releases). Extract the files *inside* the archive's top-level folder into `tools/scrcpy`:

```text
tools/scrcpy/
  scrcpy.exe
  adb.exe
  scrcpy-server
  ...all other DLLs and files supplied by that release...
```

Do not copy only the two EXEs. Avoid an extra nested `scrcpy-win64-*` directory. The engine's DLLs, server and notices are needed. Engine files are ignored by Git.

## 2. Compile and launch

```powershell
dotnet --version
dotnet restore ClearMirror.sln
dotnet build ClearMirror.sln -c Release --no-restore
dotnet run --project src/ClearMirror.App -c Release --no-build
```

The solution can compile and run its automated tests without scrcpy or an overlay binary. Actual mirroring needs the engine. If you added tools after compiling, build again so the app's output directory receives them.

Visual Studio can also open `ClearMirror.sln`; install its .NET desktop development workload and set `ClearMirror.App` as the startup project.

## 3. Optional gaming controls

Set up an isolated Python environment:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r control-overlay-src\requirements.txt pyinstaller
Copy-Item control-overlay-src\profiles.example.json control-overlay-src\profiles.json
.\.venv\Scripts\python.exe control-overlay-src\main.py --target-title "ClearMirror Preview" --auto-apply
```

Copy the example only on first setup; it replaces a destination file if one already exists. Your edited `profiles.json` is ignored by Git. The example uses **Ctrl** for mouse look and **F12** for editing. Newly added mouse-look controls default to **F1**. Adjust positions to your game's HUD.

To create the EXE, run PyInstaller from the overlay directory so its relative icon path resolves:

```powershell
Push-Location control-overlay-src
try {
    ..\.venv\Scripts\python.exe -m PyInstaller --noconfirm GamingControlOverlay.spec
    if ($LASTEXITCODE -ne 0) { throw "Overlay build failed" }
}
finally { Pop-Location }
Copy-Item control-overlay-src\dist\GamingControlOverlay.exe tools\controls\GamingControlOverlay.exe
Copy-Item control-overlay-src\profiles.example.json tools\controls\profiles.json
```

You can copy your edited source profile instead of the example. See the [overlay guide](../control-overlay-src/README.md) for editing, input modes and hooks.

## 4. Test

Follow [TESTING.md](TESTING.md). The default tests use synthetic data and do not start real microphone capture.

## 5. Publish a portable Windows app

Close the running ClearMirror app and its preview before publishing:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Publish.ps1
Copy-Item -LiteralPath docs -Destination dist\ClearMirror -Recurse -Force
Copy-Item -LiteralPath CHANGELOG.md,CONTRIBUTING.md -Destination dist\ClearMirror -Force
```

The result is `dist/ClearMirror/ClearMirror.exe` with its required sibling files. The default is self-contained `win-x64`, so users do not need to install .NET separately. Share the complete `dist/ClearMirror` directory as a ZIP, not only the EXE. The extra copy commands include the linked documentation in that portable folder.

For a smaller package requiring the .NET 8 **Desktop Runtime** on the destination PC:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Publish.ps1 -FrameworkDependent
```

Publishing builds into a temporary directory before updating `dist`. A compiler failure leaves the previous distribution intact. Existing recordings and an existing `tools/controls/profiles.json` are preserved. Copy-stage interruptions are not an atomic rollback, so keep a backup when replacing a distribution you depend on.

## Troubleshooting builds

| Symptom | Action |
| --- | --- |
| `dotnet` not found / no compatible SDK | Install the .NET 8 SDK and open a new terminal |
| NuGet restore fails | Check connectivity to the configured NuGet source and restore again |
| `scrcpy.exe is missing` during publish | Fix the `tools/scrcpy` layout above |
| Locked EXE/DLL during publish | Close ClearMirror, the preview and gaming overlay, then rerun |
| Gaming Controls executable missing | Build the optional overlay and rebuild/publish the app |
