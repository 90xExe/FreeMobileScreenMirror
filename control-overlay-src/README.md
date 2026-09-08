# Gaming Control Overlay

A Windows emulator-style keyboard and mouse control editor. It attaches to a
selected running application, shows MSI/BlueStacks-style editable controls,
then hides the editor and runs the saved mapping.

## Run for testing

Open PowerShell in this folder and run:

```powershell
python -m pip install -r requirements.txt
python main.py
```

This source snapshot excludes prebuilt EXEs. Follow the [ClearMirror build
guide](../docs/BUILD.md) to compile the optional controller. Before first use,
copy `profiles.example.json` to `profiles.json` for a starter layout targeting
`ClearMirror Preview`. The example uses **Ctrl** for mouse look; newly created
mouse-look controls use **F1**. Local profiles are ignored by Git.

## Quick-add workflow

1. Open the emulator/game, start `main.py`, click **Refresh**, and select its
   visible window.
2. Click **Create new overlay**.
3. Click any empty game position. A `?` Tap appears at that exact location.
4. Press any key, LMB/RMB/MMB, Mouse 4/5, or scroll Wheel Up/Down.
   The pending Tap binds immediately; no dropdown selection is required.
5. Drag controls to move them. Use the mouse wheel over a control to resize it.
   Double-click a Tap/Fire control to capture a different input.
6. Save or rename the profile, then click **Apply & hide**.
7. Use **CONTROL SYSTEM: ON / OFF** in the main window to enable or immediately
   disable every keyboard/mouse mapping, Fire, wheel action, and Mouse Look.
   Turning it OFF also unlocks the cursor. Turning it ON restores the current
   overlay, or applies the selected saved profile when no overlay is open.
8. Press **F12** to return to edit mode. Edit mode automatically turns the
   control system OFF until the overlay is applied again.

## Special controls

- **WASD Joystick**: click **+ WASD Joystick**, then click the exact center of
  the game's movement joystick. A circular W/A/S/D control is placed there.
- **Fire**: click **+ Fire**, then click the exact in-game fire button. It is
  automatically bound to LMB. Double-click it if you want another trigger.
- **Mouse look**: click **+ Mouse look**, then click a clear aim/camera anchor
  near the center of the game view. After applying, press **F1** to lock the
  cursor. Mouse movement produces relative left/right/up/down camera swipes.
  Press F1 again, press F12, turn the Control System OFF, change focus, or quit
  to unlock.
- Right-click a control and choose **Advanced settings** to change output click,
  D-pad keys, mouse-lock toggle key, or look sensitivity.

Saved profiles are kept beside the app:

```text
Source mode:  <main.py folder>\profiles.json
EXE mode:     <EXE folder>\profiles.json
```

On the first run after this change, an existing
`%APPDATA%\GamingControlOverlay\profiles.json` is copied to the new local path
when no local profile file exists. The old AppData copy is left untouched as a
backup.

## Input modes

- **Window message**: sends input without moving the real cursor. Mouse Look
  always uses short window-message swipes from its anchor.
- **Physical click**: more compatible with some emulator buttons, but regular
  Tap/Fire actions temporarily use the real cursor while held.

For reliable mouse lock, keep the emulator as the foreground window. If the
emulator runs as administrator, run this app as administrator too. Some
anti-cheat protected games may reject synthetic input; the app does not bypass
anti-cheat or security controls.

## Developer smoke test

```powershell
python main.py --smoke-test
```

The app briefly initializes application discovery plus keyboard/mouse hooks,
exits automatically, and prints `SMOKE_TEST_OK`.

