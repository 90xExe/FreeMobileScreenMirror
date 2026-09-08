"""Gaming Control Overlay - Windows keyboard-to-touch style mapper.

The app discovers visible desktop application windows, attaches a transparent
overlay to one of them, and maps keyboard keys to mouse/touch-like positions.
Profiles are stored beside main.py, or beside the packaged EXE.
"""

from __future__ import annotations

import copy
import ctypes
import json
import os
import sys
import tempfile
import uuid
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

if sys.platform != "win32":
    raise SystemExit("Gaming Control Overlay currently supports Windows only.")

try:
    from PyQt5.QtCore import QFileInfo, QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
    from PyQt5.QtGui import (
        QColor,
        QCursor,
        QFont,
        QIcon,
        QPainter,
        QPainterPath,
        QPen,
        QPixmap,
    )
    from PyQt5.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileIconProvider,
        QFormLayout,
        QFrame,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSpacerItem,
        QStyle,
        QSystemTrayIcon,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise SystemExit(
        "PyQt5 is required. Run:  python -m pip install -r requirements.txt"
    ) from exc


APP_NAME = "Gaming Control Overlay"
APP_VERSION = "1.1.1"
PROFILE_VERSION = 1

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]
class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]



EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)
LowLevelMouseProc = LowLevelKeyboardProc

user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.ShowCursor.argtypes = [wintypes.BOOL]
user32.ShowCursor.restype = ctypes.c_int
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, LowLevelKeyboardProc, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
GA_ROOT = 2
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
HC_ACTION = 0
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002
LLKHF_INJECTED = 0x00000010
LLMHF_INJECTED = 0x00000001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

GetWindowLongPtr = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
SetWindowLongPtr = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongPtr.restype = ctypes.c_ssize_t
SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
SetWindowLongPtr.restype = ctypes.c_ssize_t


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "GamingControlOverlay"


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def make_lparam(x: int, y: int) -> int:
    return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)


def window_root(hwnd: int) -> int:
    if not hwnd:
        return 0
    return int(user32.GetAncestor(wintypes.HWND(hwnd), GA_ROOT) or hwnd)


def is_target_foreground(hwnd: int) -> bool:
    return bool(hwnd) and window_root(int(user32.GetForegroundWindow() or 0)) == window_root(hwnd)


def process_exe_path(pid: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def client_geometry(hwnd: int) -> Optional[QRect]:
    if not hwnd or not user32.IsWindow(wintypes.HWND(hwnd)):
        return None
    rect = RECT()
    if not user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
        return None
    origin = POINT(0, 0)
    if not user32.ClientToScreen(wintypes.HWND(hwnd), ctypes.byref(origin)):
        return None
    width = max(0, rect.right - rect.left)
    height = max(0, rect.bottom - rect.top)
    if width < 80 or height < 80:
        return None
    return QRect(origin.x, origin.y, width, height)


@dataclass
class WindowInfo:
    hwnd: int
    pid: int
    title: str
    exe_path: str

    @property
    def process_name(self) -> str:
        return Path(self.exe_path).name if self.exe_path else f"PID {self.pid}"


def enumerate_windows() -> List[WindowInfo]:
    windows: List[WindowInfo] = []
    current_pid = os.getpid()

    @EnumWindowsProc
    def callback(hwnd: int, _lparam: int) -> bool:
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            title_buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, length + 1)
            title = title_buffer.value.strip()
            if not title:
                return True
            rect = RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            if rect.right - rect.left < 120 or rect.bottom - rect.top < 80:
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value or pid.value == current_pid:
                return True
            exe = process_exe_path(pid.value)
            windows.append(WindowInfo(int(hwnd), int(pid.value), title, exe))
        except Exception:
            pass
        return True

    if not user32.EnumWindows(callback, 0):
        error = ctypes.get_last_error()
        if error:
            raise ctypes.WinError(error)
    windows.sort(key=lambda item: (item.process_name.lower(), item.title.lower()))
    return windows


KEY_TO_VK: Dict[str, int] = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "SHIFT": 0x10,
    "CTRL": 0x11,
    "ALT": 0x12,
    "ESC": 0x1B,
    "SPACE": 0x20,
    "PAGE UP": 0x21,
    "PAGE DOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
}
KEY_TO_VK.update({chr(code): code for code in range(ord("A"), ord("Z") + 1)})
KEY_TO_VK.update({chr(code): code for code in range(ord("0"), ord("9") + 1)})
KEY_TO_VK.update({f"F{number}": 0x6F + number for number in range(1, 13)})
VK_TO_KEY = {value: key for key, value in KEY_TO_VK.items()}
WHEEL_INPUTS = ("MOUSE WHEEL UP", "MOUSE WHEEL DOWN")
MOUSE_INPUTS = ("MOUSE LEFT", "MOUSE RIGHT", "MOUSE MIDDLE", "MOUSE 4", "MOUSE 5") + WHEEL_INPUTS
MOUSE_DISPLAY = {
    "MOUSE LEFT": "LMB",
    "MOUSE RIGHT": "RMB",
    "MOUSE MIDDLE": "MMB",
    "MOUSE 4": "M4",
    "MOUSE 5": "M5",
    "MOUSE WHEEL UP": "WHEEL↑",
    "MOUSE WHEEL DOWN": "WHEEL↓",
}

COMMON_KEYS = (
    list("WASDQERFZXCV1234567890")
    + ["SPACE", "SHIFT", "CTRL", "ALT", "TAB", "ENTER", "UP", "DOWN", "LEFT", "RIGHT"]
    + [f"F{number}" for number in range(1, 12)]
    + list(MOUSE_INPUTS)
)


def normalize_key_name(value: object, fallback: str = "F") -> str:
    text = str(value or "").strip().upper()
    aliases = {
        "CONTROL": "CTRL", "ESCAPE": "ESC", "RETURN": "ENTER", " ": "SPACE",
        "LMB": "MOUSE LEFT", "RMB": "MOUSE RIGHT", "MMB": "MOUSE MIDDLE",
        "MOUSE4": "MOUSE 4", "MOUSE5": "MOUSE 5",
        "WHEELUP": "MOUSE WHEEL UP", "WHEELDOWN": "MOUSE WHEEL DOWN",
        "MOUSEWHEELUP": "MOUSE WHEEL UP", "MOUSEWHEELDOWN": "MOUSE WHEEL DOWN",
    }
    text = aliases.get(text, text)
    return text if text in KEY_TO_VK or text in MOUSE_INPUTS else fallback


def key_name_from_event(event) -> Optional[str]:
    native = int(event.nativeVirtualKey() or 0)
    if native in VK_TO_KEY:
        return VK_TO_KEY[native]
    text = event.text().upper().strip()
    if text in KEY_TO_VK:
        return text
    qt_map = {
        Qt.Key_Space: "SPACE",
        Qt.Key_Tab: "TAB",
        Qt.Key_Return: "ENTER",
        Qt.Key_Enter: "ENTER",
        Qt.Key_Escape: "ESC",
        Qt.Key_Shift: "SHIFT",
        Qt.Key_Control: "CTRL",
        Qt.Key_Alt: "ALT",
        Qt.Key_Up: "UP",
        Qt.Key_Down: "DOWN",
        Qt.Key_Left: "LEFT",
        Qt.Key_Right: "RIGHT",
        Qt.Key_Delete: "DELETE",
        Qt.Key_Backspace: "BACKSPACE",
    }
    return qt_map.get(event.key())
def mouse_input_from_qt(button: Qt.MouseButton) -> Optional[str]:
    return {
        Qt.LeftButton: "MOUSE LEFT",
        Qt.RightButton: "MOUSE RIGHT",
        Qt.MiddleButton: "MOUSE MIDDLE",
        Qt.XButton1: "MOUSE 4",
        Qt.XButton2: "MOUSE 5",
    }.get(button)


def display_input_name(name: str) -> str:
    return MOUSE_DISPLAY.get(name, name)



def new_control(kind: str, x: float = 0.5, y: float = 0.5) -> dict:
    sizes = {"tap": 0.13, "fire": 0.15, "mouse_look": 0.17, "dpad": 0.19}
    base = {
        "id": uuid.uuid4().hex,
        "kind": kind,
        "x": float(x),
        "y": float(y),
        "size": sizes.get(kind, 0.13),
        "button": "left",
    }
    if kind == "dpad":
        base["keys"] = {"up": "W", "left": "A", "down": "S", "right": "D"}
    elif kind == "fire":
        base["key"] = "MOUSE LEFT"
    elif kind == "mouse_look":
        base["toggle_key"] = "F1"
        base["sensitivity"] = 1.0
    else:
        base["key"] = "F"
    return base


def normalize_control(raw: object) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    kind = raw.get("kind")
    if kind not in {"tap", "fire", "mouse_look", "dpad"}:
        return None
    control = new_control(kind)
    control["id"] = str(raw.get("id") or uuid.uuid4().hex)
    try:
        control["x"] = min(1.0, max(0.0, float(raw.get("x", 0.5))))
        control["y"] = min(1.0, max(0.0, float(raw.get("y", 0.5))))
        control["size"] = min(0.32, max(0.065, float(raw.get("size", control["size"]))))
    except (TypeError, ValueError):
        pass
    control["button"] = "right" if raw.get("button") == "right" else "left"
    if kind in {"tap", "fire"}:
        fallback = "MOUSE LEFT" if kind == "fire" else "F"
        control["key"] = normalize_key_name(raw.get("key"), fallback)
    elif kind == "mouse_look":
        control["toggle_key"] = normalize_key_name(raw.get("toggle_key"), "F1")
        try:
            control["sensitivity"] = min(4.0, max(0.1, float(raw.get("sensitivity", 1.0))))
        except (TypeError, ValueError):
            control["sensitivity"] = 1.0
    else:
        keys = raw.get("keys") if isinstance(raw.get("keys"), dict) else {}
        defaults = {"up": "W", "left": "A", "down": "S", "right": "D"}
        control["keys"] = {
            direction: normalize_key_name(keys.get(direction), default)
            for direction, default in defaults.items()
        }
    return control


class ProfileStore:
    def __init__(self) -> None:
        self.directory = application_dir()
        self.path = self.directory / "profiles.json"
        self.legacy_path = app_data_dir() / "profiles.json"
        self.profiles: List[dict] = []
        self._migrate_legacy_profile()
        self.load()

    def _migrate_legacy_profile(self) -> None:
        if self.path.exists() or not self.legacy_path.exists():
            return
        try:
            raw = self.legacy_path.read_bytes()
            payload = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(payload, dict):
                return
            self.directory.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(
                prefix="profiles-migrate-", suffix=".tmp", dir=str(self.directory)
            )
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass

    def load(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.profiles = []
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            raw_profiles = payload.get("profiles", []) if isinstance(payload, dict) else []
            self.profiles = [self._normalize_profile(item) for item in raw_profiles if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError, TypeError):
            backup = self.directory / f"profiles.corrupt-{datetime.now():%Y%m%d-%H%M%S}.json"
            try:
                self.path.replace(backup)
            except OSError:
                pass
            self.profiles = []

    def _normalize_profile(self, raw: dict) -> dict:
        controls = [normalize_control(item) for item in raw.get("controls", [])]
        return {
            "id": str(raw.get("id") or uuid.uuid4().hex),
            "name": str(raw.get("name") or "Untitled profile")[:80],
            "target_exe": str(raw.get("target_exe") or ""),
            "target_title_hint": str(raw.get("target_title_hint") or "")[:160],
            "input_mode": "physical" if raw.get("input_mode") == "physical" else "message",
            "block_keys": bool(raw.get("block_keys", True)),
            "controls": [item for item in controls if item],
            "created_at": str(raw.get("created_at") or utc_now()),
            "updated_at": str(raw.get("updated_at") or utc_now()),
        }

    def save(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {"version": PROFILE_VERSION, "profiles": self.profiles}
        fd, temporary = tempfile.mkstemp(prefix="profiles-", suffix=".tmp", dir=str(self.directory))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def get(self, profile_id: str) -> Optional[dict]:
        return next((item for item in self.profiles if item["id"] == profile_id), None)

    def upsert(self, profile: dict) -> dict:
        normalized = self._normalize_profile(profile)
        normalized["updated_at"] = utc_now()
        existing = self.get(normalized["id"])
        if existing:
            existing.clear()
            existing.update(normalized)
            result = existing
        else:
            self.profiles.append(normalized)
            result = normalized
        self.save()
        return result

    def remove(self, profile_id: str) -> None:
        self.profiles = [item for item in self.profiles if item["id"] != profile_id]
        self.save()


class GlobalKeyboardHook(QWidget):
    key_event = pyqtSignal(int, bool)

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        self._hook = None
        self._callback = None
        self.blocked_vks: Set[int] = set()
        self.target_hwnd = 0
        self.blocking_enabled = False

    def start(self) -> bool:
        if self._hook:
            return True

        @LowLevelKeyboardProc
        def callback(code: int, message: int, data_ptr: int) -> int:
            should_block = False
            if code == HC_ACTION:
                data = ctypes.cast(data_ptr, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if not data.flags & LLKHF_INJECTED:
                    down = message in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    up = message in (WM_KEYUP, WM_SYSKEYUP)
                    if down or up:
                        vk = int(data.vkCode)
                        self.key_event.emit(vk, down)
                        if vk == KEY_TO_VK["F12"]:
                            should_block = True
                        elif (
                            self.blocking_enabled
                            and vk in self.blocked_vks
                            and is_target_foreground(self.target_hwnd)
                        ):
                            should_block = True
            if should_block:
                return 1
            return int(user32.CallNextHookEx(self._hook, code, message, data_ptr))

        self._callback = callback
        module = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, callback, module, 0)
        return bool(self._hook)

    def configure_blocking(self, keys: Iterable[str], target_hwnd: int, enabled: bool) -> None:
        self.blocked_vks = {KEY_TO_VK[name] for name in keys if name in KEY_TO_VK}
        self.target_hwnd = int(target_hwnd or 0)
        self.blocking_enabled = bool(enabled and target_hwnd)

    def stop(self) -> None:
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        self._callback = None
class GlobalMouseHook(QWidget):
    button_event = pyqtSignal(str, bool)
    movement = pyqtSignal(int, int)
    lock_cancelled = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        self._hook = None
        self._callback = None
        self.blocked_inputs: Set[str] = set()
        self.target_hwnd = 0
        self.blocking_enabled = False
        self.lock_enabled = False
        self.lock_target_hwnd = 0
        self._cursor_hidden = False

    @staticmethod
    def _message_input(message: int, mouse_data: int) -> Optional[Tuple[str, bool]]:
        direct = {
            WM_LBUTTONDOWN: ("MOUSE LEFT", True),
            WM_LBUTTONUP: ("MOUSE LEFT", False),
            WM_RBUTTONDOWN: ("MOUSE RIGHT", True),
            WM_RBUTTONUP: ("MOUSE RIGHT", False),
            WM_MBUTTONDOWN: ("MOUSE MIDDLE", True),
            WM_MBUTTONUP: ("MOUSE MIDDLE", False),
        }
        if message in direct:
            return direct[message]
        if message == WM_MOUSEWHEEL:
            delta = ctypes.c_short((int(mouse_data) >> 16) & 0xFFFF).value
            if delta:
                return ("MOUSE WHEEL UP" if delta > 0 else "MOUSE WHEEL DOWN"), True
        if message in (WM_XBUTTONDOWN, WM_XBUTTONUP):
            button = (int(mouse_data) >> 16) & 0xFFFF
            name = "MOUSE 4" if button == 1 else "MOUSE 5"
            return name, message == WM_XBUTTONDOWN
        return None

    def start(self) -> bool:
        if self._hook:
            return True

        @LowLevelMouseProc
        def callback(code: int, message: int, data_ptr: int) -> int:
            should_block = False
            if code == HC_ACTION:
                data = ctypes.cast(data_ptr, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                if not data.flags & LLMHF_INJECTED:
                    if int(message) == WM_MOUSEMOVE and self.lock_enabled:
                        if is_target_foreground(self.lock_target_hwnd):
                            geometry = client_geometry(self.lock_target_hwnd)
                            if geometry:
                                center_x = geometry.x() + geometry.width() // 2
                                center_y = geometry.y() + geometry.height() // 2
                                dx = int(data.pt.x) - center_x
                                dy = int(data.pt.y) - center_y
                                if dx or dy:
                                    self.movement.emit(dx, dy)
                                    user32.SetCursorPos(center_x, center_y)
                                should_block = True
                        else:
                            self.set_cursor_lock(False, 0)
                            self.lock_cancelled.emit()
                    mapped = self._message_input(int(message), int(data.mouseData))
                    if mapped:
                        name, down = mapped
                        if name in WHEEL_INPUTS:
                            self.button_event.emit(name, True)
                            self.button_event.emit(name, False)
                        else:
                            self.button_event.emit(name, down)
                        if (
                            self.blocking_enabled
                            and name in self.blocked_inputs
                            and is_target_foreground(self.target_hwnd)
                        ):
                            should_block = True
            if should_block:
                return 1
            return int(user32.CallNextHookEx(self._hook, code, message, data_ptr))

        self._callback = callback
        module = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_MOUSE_LL, callback, module, 0)
        return bool(self._hook)

    def configure_blocking(self, inputs: Iterable[str], target_hwnd: int, enabled: bool) -> None:
        self.blocked_inputs = {name for name in inputs if name in MOUSE_INPUTS}
        self.target_hwnd = int(target_hwnd or 0)
        self.blocking_enabled = bool(enabled and target_hwnd)

    def set_cursor_lock(self, enabled: bool, target_hwnd: int) -> None:
        enabled = bool(enabled and target_hwnd and user32.IsWindow(wintypes.HWND(target_hwnd)))
        self.lock_enabled = enabled
        self.lock_target_hwnd = int(target_hwnd if enabled else 0)
        if enabled:
            geometry = client_geometry(self.lock_target_hwnd)
            if geometry:
                user32.SetCursorPos(
                    geometry.x() + geometry.width() // 2,
                    geometry.y() + geometry.height() // 2,
                )
            if not self._cursor_hidden:
                for _attempt in range(32):
                    if user32.ShowCursor(False) < 0:
                        break
                self._cursor_hidden = True
        elif self._cursor_hidden:
            for _attempt in range(32):
                if user32.ShowCursor(True) >= 0:
                    break
            self._cursor_hidden = False

    def stop(self) -> None:
        self.set_cursor_lock(False, 0)
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        self._callback = None



class InputDispatcher:
    def __init__(self) -> None:
        self.target_hwnd = 0
        self.mode = "message"
        self.sessions: Dict[str, dict] = {}

    def configure(self, target_hwnd: int, mode: str) -> None:
        self.release_all()
        self.target_hwnd = int(target_hwnd or 0)
        self.mode = "physical" if mode == "physical" else "message"

    def _target_point(self, normalized: Tuple[float, float]) -> Optional[Tuple[int, int]]:
        geometry = client_geometry(self.target_hwnd)
        if not geometry:
            return None
        x = geometry.x() + round(min(1.0, max(0.0, normalized[0])) * max(1, geometry.width() - 1))
        y = geometry.y() + round(min(1.0, max(0.0, normalized[1])) * max(1, geometry.height() - 1))
        return x, y

    def _post(self, hwnd: int, message: int, flags: int, screen_xy: Tuple[int, int]) -> None:
        point = POINT(*screen_xy)
        user32.ScreenToClient(wintypes.HWND(hwnd), ctypes.byref(point))
        user32.PostMessageW(wintypes.HWND(hwnd), message, flags, make_lparam(point.x, point.y))

    def begin(self, session_id: str, normalized: Tuple[float, float], button: str = "left") -> None:
        if session_id in self.sessions:
            return
        screen_xy = self._target_point(normalized)
        if not screen_xy:
            return
        button = "right" if button == "right" else "left"
        if self.mode == "physical":
            old = POINT()
            user32.GetCursorPos(ctypes.byref(old))
            user32.SetCursorPos(*screen_xy)
            flag = MOUSEEVENTF_RIGHTDOWN if button == "right" else MOUSEEVENTF_LEFTDOWN
            user32.mouse_event(flag, 0, 0, 0, None)
            self.sessions[session_id] = {"button": button, "old": (old.x, old.y), "screen": screen_xy}
        else:
            point = POINT(*screen_xy)
            receiver = int(user32.WindowFromPoint(point) or self.target_hwnd)
            move_flags = MK_RBUTTON if button == "right" else MK_LBUTTON
            down_message = WM_RBUTTONDOWN if button == "right" else WM_LBUTTONDOWN
            self._post(receiver, WM_MOUSEMOVE, 0, screen_xy)
            self._post(receiver, down_message, move_flags, screen_xy)
            self.sessions[session_id] = {"button": button, "receiver": receiver, "screen": screen_xy}

    def move(self, session_id: str, normalized: Tuple[float, float]) -> None:
        session = self.sessions.get(session_id)
        screen_xy = self._target_point(normalized)
        if not session or not screen_xy:
            return
        session["screen"] = screen_xy
        if self.mode == "physical":
            user32.SetCursorPos(*screen_xy)
        else:
            flags = MK_RBUTTON if session["button"] == "right" else MK_LBUTTON
            self._post(session["receiver"], WM_MOUSEMOVE, flags, screen_xy)

    def end(self, session_id: str) -> None:
        session = self.sessions.pop(session_id, None)
        if not session:
            return
        if self.mode == "physical":
            flag = MOUSEEVENTF_RIGHTUP if session["button"] == "right" else MOUSEEVENTF_LEFTUP
            user32.SetCursorPos(*session["screen"])
            user32.mouse_event(flag, 0, 0, 0, None)
            user32.SetCursorPos(*session["old"])
        else:
            message = WM_RBUTTONUP if session["button"] == "right" else WM_LBUTTONUP
            self._post(session["receiver"], message, 0, session["screen"])

    def swipe(self, anchor: Tuple[float, float], dx: int, dy: int, sensitivity: float) -> None:
        geometry = client_geometry(self.target_hwnd)
        start = self._target_point(anchor)
        if not geometry or not start:
            return
        delta_x = max(-180, min(180, round(-dx * sensitivity)))
        delta_y = max(-180, min(180, round(-dy * sensitivity)))
        end = (
            min(geometry.right() - 2, max(geometry.left() + 1, start[0] + delta_x)),
            min(geometry.bottom() - 2, max(geometry.top() + 1, start[1] + delta_y)),
        )
        receiver = int(user32.WindowFromPoint(POINT(*start)) or self.target_hwnd)
        self._post(receiver, WM_MOUSEMOVE, 0, start)
        self._post(receiver, WM_LBUTTONDOWN, MK_LBUTTON, start)
        self._post(receiver, WM_MOUSEMOVE, MK_LBUTTON, end)
        self._post(receiver, WM_LBUTTONUP, 0, end)

    def release_all(self) -> None:
        for session_id in list(self.sessions):
            self.end(session_id)


class _LegacyMappingEngine:
    def __init__(self) -> None:
        self.dispatcher = InputDispatcher()
        self.target_hwnd = 0
        self.controls: List[dict] = []
        self.enabled = False
        self.pressed_vks: Set[int] = set()
        self.active_dpads: Dict[str, Set[str]] = {}

    def configure(self, hwnd: int, controls: List[dict], input_mode: str) -> None:
        self.disable()
        self.target_hwnd = int(hwnd or 0)
        self.controls = copy.deepcopy(controls)
        self.dispatcher.configure(self.target_hwnd, input_mode)

    def mapped_key_names(self) -> Set[str]:
        result: Set[str] = set()
        for control in self.controls:
            if control["kind"] == "tap":
                result.add(control["key"])
            else:
                result.update(control["keys"].values())
        return result

    def enable(self) -> None:
        self.enabled = bool(self.target_hwnd and self.controls)

    def disable(self) -> None:
        self.dispatcher.release_all()
        self.pressed_vks.clear()
        self.active_dpads.clear()
        self.enabled = False

    def handle_key(self, vk: int, down: bool) -> None:
        if not self.enabled:
            return
        if not user32.IsWindow(wintypes.HWND(self.target_hwnd)):
            self.disable()
            return
        if not is_target_foreground(self.target_hwnd):
            if not down:
                self._release_vk(vk)
            return
        if down:
            if vk in self.pressed_vks:
                return
            self.pressed_vks.add(vk)
            self._press_vk(vk)
        else:
            self.pressed_vks.discard(vk)
            self._release_vk(vk)

    def _press_vk(self, vk: int) -> None:
        for control in self.controls:
            if control["kind"] == "tap" and KEY_TO_VK.get(control["key"]) == vk:
                self.dispatcher.begin(control["id"], (control["x"], control["y"]), control["button"])
            elif control["kind"] == "dpad":
                for direction, name in control["keys"].items():
                    if KEY_TO_VK.get(name) == vk:
                        active = self.active_dpads.setdefault(control["id"], set())
                        if not active:
                            self.dispatcher.begin(control["id"], (control["x"], control["y"]), "left")
                        active.add(direction)
                        self.dispatcher.move(control["id"], self._dpad_position(control, active))

    def _release_vk(self, vk: int) -> None:
        for control in self.controls:
            if control["kind"] == "tap" and KEY_TO_VK.get(control["key"]) == vk:
                self.dispatcher.end(control["id"])
            elif control["kind"] == "dpad":
                active = self.active_dpads.get(control["id"], set())
                for direction, name in control["keys"].items():
                    if KEY_TO_VK.get(name) == vk and direction in active:
                        active.discard(direction)
                if active:
                    self.dispatcher.move(control["id"], self._dpad_position(control, active))
                else:
                    self.dispatcher.end(control["id"])
                    self.active_dpads.pop(control["id"], None)

    @staticmethod
    def _dpad_position(control: dict, active: Set[str]) -> Tuple[float, float]:
        dx = int("right" in active) - int("left" in active)
        dy = int("down" in active) - int("up" in active)
        reach = control["size"] * 0.42
        if dx and dy:
            reach *= 0.7071
        return (
            min(1.0, max(0.0, control["x"] + dx * reach)),
            min(1.0, max(0.0, control["y"] + dy * reach)),
        )


class MappingEngine:
    def __init__(self) -> None:
        self.dispatcher = InputDispatcher()
        self.target_hwnd = 0
        self.controls: List[dict] = []
        self.enabled = False
        self.pressed_inputs: Set[str] = set()
        self.active_dpads: Dict[str, Set[str]] = {}
        self.mouse_locked = False
        self.on_lock_changed = None

    def configure(self, hwnd: int, controls: List[dict], input_mode: str) -> None:
        self.disable()
        self.target_hwnd = int(hwnd or 0)
        self.controls = copy.deepcopy(controls)
        self.dispatcher.configure(self.target_hwnd, input_mode)

    def mapped_key_names(self) -> Set[str]:
        result: Set[str] = set()
        for control in self.controls:
            if control["kind"] in {"tap", "fire"}:
                result.add(control["key"])
            elif control["kind"] == "dpad":
                result.update(control["keys"].values())
            elif control["kind"] == "mouse_look":
                result.add(control["toggle_key"])
        return result

    def enable(self) -> None:
        self.enabled = bool(self.target_hwnd and self.controls)

    def disable(self) -> None:
        self._set_mouse_locked(False)
        self.dispatcher.release_all()
        self.pressed_inputs.clear()
        self.active_dpads.clear()
        self.enabled = False

    def _set_mouse_locked(self, enabled: bool) -> None:
        enabled = bool(enabled and self.enabled and any(c["kind"] == "mouse_look" for c in self.controls))
        if self.mouse_locked == enabled:
            return
        self.mouse_locked = enabled
        if self.on_lock_changed:
            self.on_lock_changed(enabled)

    def cancel_mouse_lock(self) -> None:
        self._set_mouse_locked(False)

    def handle_key(self, vk: int, down: bool) -> None:
        name = VK_TO_KEY.get(vk)
        if name:
            self.handle_input(name, down)

    def handle_input(self, name: str, down: bool) -> None:
        if not self.enabled:
            return
        if not user32.IsWindow(wintypes.HWND(self.target_hwnd)):
            self.disable()
            return
        if not is_target_foreground(self.target_hwnd):
            if not down:
                self._release_input(name)
            self._set_mouse_locked(False)
            return
        if down:
            if name in self.pressed_inputs:
                return
            self.pressed_inputs.add(name)
            self._press_input(name)
        else:
            self.pressed_inputs.discard(name)
            self._release_input(name)

    def _press_input(self, name: str) -> None:
        for control in self.controls:
            if control["kind"] == "mouse_look" and control["toggle_key"] == name:
                self._set_mouse_locked(not self.mouse_locked)
                return
        for control in self.controls:
            if control["kind"] in {"tap", "fire"} and control["key"] == name:
                self.dispatcher.begin(control["id"], (control["x"], control["y"]), control["button"])
            elif control["kind"] == "dpad":
                for direction, mapped_name in control["keys"].items():
                    if mapped_name == name:
                        active = self.active_dpads.setdefault(control["id"], set())
                        if not active:
                            self.dispatcher.begin(control["id"], (control["x"], control["y"]), "left")
                        active.add(direction)
                        self.dispatcher.move(control["id"], self._dpad_position(control, active))

    def _release_input(self, name: str) -> None:
        for control in self.controls:
            if control["kind"] in {"tap", "fire"} and control["key"] == name:
                self.dispatcher.end(control["id"])
            elif control["kind"] == "dpad":
                active = self.active_dpads.get(control["id"], set())
                for direction, mapped_name in control["keys"].items():
                    if mapped_name == name and direction in active:
                        active.discard(direction)
                if active:
                    self.dispatcher.move(control["id"], self._dpad_position(control, active))
                else:
                    self.dispatcher.end(control["id"])
                    self.active_dpads.pop(control["id"], None)

    def handle_mouse_move(self, dx: int, dy: int) -> None:
        if not self.enabled or not self.mouse_locked or not is_target_foreground(self.target_hwnd):
            return
        control = next((item for item in self.controls if item["kind"] == "mouse_look"), None)
        if control:
            self.dispatcher.swipe(
                (control["x"], control["y"]), dx, dy, float(control.get("sensitivity", 1.0))
            )

    @staticmethod
    def _dpad_position(control: dict, active: Set[str]) -> Tuple[float, float]:
        dx = int("right" in active) - int("left" in active)
        dy = int("down" in active) - int("up" in active)
        reach = control["size"] * 0.42
        if dx and dy:
            reach *= 0.7071
        return (
            min(1.0, max(0.0, control["x"] + dx * reach)),
            min(1.0, max(0.0, control["y"] + dy * reach)),
        )


class KeyCombo(QComboBox):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.setEditable(True)
        self.addItems(COMMON_KEYS)
        self.setCurrentText(value)

    def value(self, fallback: str) -> str:
        return normalize_key_name(self.currentText(), fallback)

    def keyPressEvent(self, event) -> None:
        name = key_name_from_event(event)
        if name:
            self.setCurrentText(name)
            event.accept()
            return
        super().keyPressEvent(event)


class ControlSettingsDialog(QDialog):
    def __init__(self, control: dict, parent=None) -> None:
        super().__init__(parent)
        self.control = control
        self.setWindowTitle("Control settings")
        self.setModal(True)
        self.setMinimumWidth(330)
        form = QFormLayout(self)
        self.inputs: Dict[str, KeyCombo] = {}
        if control["kind"] in {"tap", "fire"}:
            self.inputs["key"] = KeyCombo(control["key"])
            form.addRow("Trigger input", self.inputs["key"])
            self.button_combo = QComboBox()
            self.button_combo.addItem("Left click / touch", "left")
            self.button_combo.addItem("Right click", "right")
            self.button_combo.setCurrentIndex(1 if control.get("button") == "right" else 0)
            form.addRow("Output action", self.button_combo)
        elif control["kind"] == "mouse_look":
            self.inputs["toggle_key"] = KeyCombo(control["toggle_key"])
            form.addRow("Lock / unlock key", self.inputs["toggle_key"])
            self.sensitivity_combo = QComboBox()
            self.sensitivity_combo.setEditable(True)
            self.sensitivity_combo.addItems(["0.5", "0.75", "1.0", "1.25", "1.5", "2.0", "3.0"])
            self.sensitivity_combo.setCurrentText(str(control.get("sensitivity", 1.0)))
            form.addRow("Mouse sensitivity", self.sensitivity_combo)
        else:
            for direction, label in (("up", "Up"), ("left", "Left"), ("down", "Down"), ("right", "Right")):
                self.inputs[direction] = KeyCombo(control["keys"][direction])
                form.addRow(label, self.inputs[direction])
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def apply_to_control(self) -> None:
        if self.control["kind"] in {"tap", "fire"}:
            fallback = "MOUSE LEFT" if self.control["kind"] == "fire" else "F"
            self.control["key"] = self.inputs["key"].value(fallback)
            self.control["button"] = str(self.button_combo.currentData())
        elif self.control["kind"] == "mouse_look":
            self.control["toggle_key"] = self.inputs["toggle_key"].value("F1")
            try:
                sensitivity = float(self.sensitivity_combo.currentText())
            except ValueError:
                sensitivity = 1.0
            self.control["sensitivity"] = min(4.0, max(0.1, sensitivity))
        else:
            defaults = {"up": "W", "left": "A", "down": "S", "right": "D"}
            self.control["keys"] = {
                direction: combo.value(defaults[direction])
                for direction, combo in self.inputs.items()
            }


class OverlayControl(QWidget):
    changed = pyqtSignal()
    delete_requested = pyqtSignal(str)
    duplicate_requested = pyqtSignal(str)

    def __init__(self, control: dict, parent: "OverlayWindow") -> None:
        super().__init__(parent)
        self.control = control
        self.drag_offset: Optional[QPoint] = None
        self.setCursor(Qt.SizeAllCursor)
        self.setMouseTracking(True)
        self.setToolTip("Drag to move • double-click to edit • mouse wheel to resize")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)
        self.sync_geometry()

    def sync_geometry(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        minimum = max(1, min(parent.width(), parent.height()))
        pixels = max(58, round(self.control["size"] * minimum))
        self.resize(pixels, pixels)
        center_x = round(self.control["x"] * parent.width())
        center_y = round(self.control["y"] * parent.height())
        self.move(center_x - pixels // 2, center_y - pixels // 2)

    def remove_button_rect(self) -> QRect:
        size = max(18, min(26, self.width() // 4))
        return QRect(self.width() - size, 0, size, size)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        accent = QColor("#ff4d67") if self.control["kind"] == "tap" else QColor("#36d1dc")
        fill = QColor(accent)
        fill.setAlpha(50)
        painter.setPen(QPen(accent, 2))
        painter.setBrush(fill)
        rect = self.rect().adjusted(4, 4, -4, -4)
        if self.control["kind"] == "tap":
            painter.drawEllipse(rect)
            painter.setPen(Qt.white)
            font = QFont("Segoe UI", max(9, self.width() // 5), QFont.Bold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, self.control["key"])
            button = "R" if self.control.get("button") == "right" else "L"
            painter.setFont(QFont("Segoe UI", max(7, self.width() // 10)))
            painter.drawText(rect.adjusted(0, 0, -7, -5), Qt.AlignRight | Qt.AlignBottom, button)
        else:
            third = self.width() / 3.0
            cells = {
                "up": QRect(round(third), 0, round(third), round(third)),
                "left": QRect(0, round(third), round(third), round(third)),
                "down": QRect(round(third), round(2 * third), round(third), round(third)),
                "right": QRect(round(2 * third), round(third), round(third), round(third)),
            }
            for direction, cell in cells.items():
                painter.drawRoundedRect(cell.adjusted(2, 2, -2, -2), 8, 8)
                painter.setPen(Qt.white)
                painter.setFont(QFont("Segoe UI", max(8, self.width() // 10), QFont.Bold))
                painter.drawText(cell, Qt.AlignCenter, self.control["keys"][direction])
                painter.setPen(QPen(accent, 2))
            painter.drawEllipse(self.rect().center(), max(3, self.width() // 30), max(3, self.width() // 30))

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        kind = self.control["kind"]
        accent = {"tap": "#ff4d67", "fire": "#ff355d", "mouse_look": "#f2bf42"}.get(kind, "#36d1dc")
        accent_color = QColor(accent)
        fill = QColor(accent_color)
        fill.setAlpha(55)
        painter.setPen(QPen(accent_color, 2))
        painter.setBrush(fill)
        rect = self.rect().adjusted(4, 4, -4, -4)
        parent = self.parentWidget()
        pending = bool(parent and getattr(parent, "pending_control_id", None) == self.control["id"])
        if kind in {"tap", "fire"}:
            painter.drawEllipse(rect)
            if kind == "fire":
                center = rect.center()
                radius = max(9, rect.width() // 4)
                painter.drawEllipse(center, radius, radius)
                painter.drawLine(center.x() - radius - 6, center.y(), center.x() + radius + 6, center.y())
                painter.drawLine(center.x(), center.y() - radius - 6, center.x(), center.y() + radius + 6)
            painter.setPen(Qt.white)
            label = "?" if pending else display_input_name(self.control["key"])
            painter.setFont(QFont("Segoe UI", max(8, self.width() // 7), QFont.Bold))
            align = Qt.AlignCenter if kind == "tap" else Qt.AlignHCenter | Qt.AlignBottom
            painter.drawText(rect.adjusted(3, 3, -3, -6), align, label)
        elif kind == "mouse_look":
            painter.drawEllipse(rect)
            center = rect.center()
            reach = max(10, rect.width() // 4)
            painter.drawLine(center.x() - reach, center.y(), center.x() + reach, center.y())
            painter.drawLine(center.x(), center.y() - reach, center.x(), center.y() + reach)
            painter.drawEllipse(center, max(4, rect.width() // 18), max(4, rect.width() // 18))
            painter.setPen(Qt.white)
            painter.setFont(QFont("Segoe UI", max(7, self.width() // 10), QFont.Bold))
            painter.drawText(rect.adjusted(2, 2, -2, -5), Qt.AlignHCenter | Qt.AlignBottom,
                             f"{display_input_name(self.control['toggle_key'])} LOCK")
        else:
            painter.drawEllipse(rect)
            inner = rect.adjusted(max(9, rect.width() // 7), max(9, rect.height() // 7),
                                  -max(9, rect.width() // 7), -max(9, rect.height() // 7))
            inner_fill = QColor(accent_color)
            inner_fill.setAlpha(35)
            painter.setBrush(inner_fill)
            painter.drawEllipse(inner)
            center = rect.center()
            reach = max(14, rect.width() // 3)
            key_radius = max(11, rect.width() // 10)
            positions = {
                "up": QPoint(center.x(), center.y() - reach),
                "left": QPoint(center.x() - reach, center.y()),
                "down": QPoint(center.x(), center.y() + reach),
                "right": QPoint(center.x() + reach, center.y()),
            }
            painter.setPen(QPen(accent_color, 2))
            for point in positions.values():
                painter.drawLine(center, point)
            for direction, point in positions.items():
                bubble = QRect(point.x() - key_radius, point.y() - key_radius,
                               key_radius * 2, key_radius * 2)
                painter.setBrush(QColor(9, 16, 31, 220))
                painter.setPen(QPen(accent_color, 2))
                painter.drawEllipse(bubble)
                painter.setPen(Qt.white)
                painter.setFont(QFont("Segoe UI", max(8, key_radius), QFont.Bold))
                painter.drawText(bubble, Qt.AlignCenter, display_input_name(self.control["keys"][direction]))
            painter.setBrush(accent_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, max(4, rect.width() // 24), max(4, rect.width() // 24))
        remove_rect = self.remove_button_rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QColor("#e83f58"))
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawEllipse(remove_rect)
        inset = max(5, remove_rect.width() // 4)
        painter.drawLine(remove_rect.left() + inset, remove_rect.top() + inset,
                         remove_rect.right() - inset, remove_rect.bottom() - inset)
        painter.drawLine(remove_rect.right() - inset, remove_rect.top() + inset,
                         remove_rect.left() + inset, remove_rect.bottom() - inset)

    def mousePressEvent(self, event) -> None:
        parent = self.parentWidget()
        if event.button() == Qt.LeftButton and self.remove_button_rect().contains(event.pos()):
            self.delete_requested.emit(self.control["id"])
            event.accept()
            return
        if getattr(parent, "pending_control_id", None):
            name = mouse_input_from_qt(event.button())
            if name:
                parent.complete_pending(name)
                event.accept()
                return
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.pos()
            self.raise_()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_offset is None or not event.buttons() & Qt.LeftButton:
            cursor = Qt.PointingHandCursor if self.remove_button_rect().contains(event.pos()) else Qt.SizeAllCursor
            self.setCursor(cursor)
            return
        parent = self.parentWidget()
        new_pos = self.mapToParent(event.pos() - self.drag_offset)
        x = min(max(0, new_pos.x()), max(0, parent.width() - self.width()))
        y = min(max(0, new_pos.y()), max(0, parent.height() - self.height()))
        self.move(x, y)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.drag_offset is not None:
            self.drag_offset = None
            self._update_normalized_position()
            self.changed.emit()
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.edit_settings()
            event.accept()

    def wheelEvent(self, event) -> None:
        parent = self.parentWidget()
        if getattr(parent, "pending_control_id", None):
            delta = event.angleDelta().y()
            if delta:
                parent.complete_pending("MOUSE WHEEL UP" if delta > 0 else "MOUSE WHEEL DOWN")
                event.accept()
                return
        step = 0.012 if event.angleDelta().y() > 0 else -0.012
        self.control["size"] = min(0.32, max(0.065, self.control["size"] + step))
        self.sync_geometry()
        self._update_normalized_position()
        self.changed.emit()
        event.accept()

    def _update_normalized_position(self) -> None:
        parent = self.parentWidget()
        center = self.geometry().center()
        self.control["x"] = min(1.0, max(0.0, center.x() / max(1, parent.width())))
        self.control["y"] = min(1.0, max(0.0, center.y() / max(1, parent.height())))

    def edit_settings(self) -> None:
        parent = self.parentWidget()
        if self.control["kind"] in {"tap", "fire"}:
            parent.begin_capture(self.control["id"], is_new=False)
            return
        self.advanced_settings()

    def advanced_settings(self) -> None:
        dialog = ControlSettingsDialog(self.control, self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.apply_to_control()
            self.update()
            self.changed.emit()

    def open_menu(self, point: QPoint) -> None:
        menu = QMenu(self)
        capture_action = None
        if self.control["kind"] in {"tap", "fire"}:
            capture_action = menu.addAction("Capture new keyboard / mouse input")
        advanced_action = menu.addAction("Advanced settings")
        duplicate_action = menu.addAction("Duplicate")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        selected = menu.exec_(self.mapToGlobal(point))
        if selected == capture_action:
            self.edit_settings()
        elif selected == advanced_action:
            self.advanced_settings()
        elif selected == duplicate_action:
            self.duplicate_requested.emit(self.control["id"])
        elif selected == delete_action:
            self.delete_requested.emit(self.control["id"])


class OverlayWindow(QWidget):
    save_requested = pyqtSignal(bool)
    applied = pyqtSignal()
    editor_closed = pyqtSignal()
    target_lost = pyqtSignal()
    controls_changed = pyqtSignal()

    def __init__(self, target: WindowInfo) -> None:
        super().__init__(None)
        self.target = target
        self.controls: List[dict] = []
        self.control_widgets: List[OverlayControl] = []
        self.edit_mode = True
        self.suspended = False
        self.dirty = False
        self.pending_control_id: Optional[str] = None
        self.pending_is_new = False
        self.placement_mode: Optional[str] = None
        self._target_lost_emitted = False
        self.setWindowTitle(f"{APP_NAME} Editor")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.toolbar = self._build_toolbar()
        self.help_card = self._build_help_card()
        self.follow_timer = QTimer(self)
        self.follow_timer.setInterval(80)
        self.follow_timer.timeout.connect(self.follow_target)
        self.follow_timer.start()
        self.follow_target()

    def _build_toolbar(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("overlayToolbar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 8, 10, 8)
        title = QLabel("CONTROLS EDITOR")
        title.setObjectName("overlayTitle")
        layout.addWidget(title)
        layout.addStretch(1)
        quick_label = QLabel("CLICK SCREEN = NEW TAP")
        quick_label.setObjectName("quickBadge")
        layout.addWidget(quick_label)
        for label, callback in (
            ("+ WASD Joystick", lambda: self.arm_placement("dpad")),
            ("+ Fire", lambda: self.arm_placement("fire")),
            ("+ Mouse look", lambda: self.arm_placement("mouse_look")),
            ("Save", lambda: self.request_save(False)),
            ("Save as", lambda: self.request_save(True)),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            layout.addWidget(button)
        apply_button = QPushButton("Apply & hide  F12")
        apply_button.setObjectName("accentButton")
        apply_button.clicked.connect(self.apply_overlay)
        layout.addWidget(apply_button)
        close_button = QPushButton("×")
        close_button.setFixedWidth(38)
        close_button.clicked.connect(self.close_editor)
        layout.addWidget(close_button)
        return frame

    def _build_help_card(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("overlayHelp")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 9, 12, 9)
        self.help_title = QLabel("QUICK ADD MODE")
        self.help_title.setObjectName("helpTitle")
        self.help_info = QLabel("Click any empty game position, then press a keyboard key, mouse button, or wheel.")
        self.help_info.setWordWrap(True)
        layout.addWidget(self.help_title)
        layout.addWidget(self.help_info)
        return frame

    def load_controls(self, controls: List[dict]) -> None:
        self.cancel_pending(delete_new=True)
        self.placement_mode = None
        self.controls = [copy.deepcopy(item) for item in controls]
        for widget in self.control_widgets:
            widget.deleteLater()
        self.control_widgets = []
        for control in self.controls:
            self._create_control_widget(control)
        self.dirty = False

    def export_controls(self) -> List[dict]:
        return copy.deepcopy(self.controls)

    def add_control(self, kind: str) -> None:
        self.arm_placement(kind)

    def arm_placement(self, kind: str) -> None:
        if kind == "mouse_look" and any(item["kind"] == "mouse_look" for item in self.controls):
            QMessageBox.information(self, APP_NAME, "Only one Mouse Look control is needed per profile.")
            return
        self.cancel_pending(delete_new=True)
        self.placement_mode = kind
        self.setCursor(Qt.CrossCursor)
        label = {
            "dpad": "WASD JOYSTICK",
            "fire": "FIRE button",
            "mouse_look": "MOUSE LOOK anchor",
        }.get(kind, "control")
        self.help_title.setText(f"PLACE {label.upper()}")
        self.help_info.setText(f"Click the exact in-game position for the {label}. Press Esc to cancel.")

    def add_tap_at(self, point: QPoint) -> None:
        control = new_control(
            "tap",
            min(1.0, max(0.0, point.x() / max(1, self.width()))),
            min(1.0, max(0.0, point.y() / max(1, self.height()))),
        )
        self.controls.append(control)
        self._create_control_widget(control)
        self.mark_dirty()
        self.begin_capture(control["id"], is_new=True)

    def place_special(self, kind: str, point: QPoint) -> None:
        control = new_control(
            kind,
            min(1.0, max(0.0, point.x() / max(1, self.width()))),
            min(1.0, max(0.0, point.y() / max(1, self.height()))),
        )
        self.controls.append(control)
        self._create_control_widget(control)
        self.placement_mode = None
        self.setCursor(Qt.CrossCursor)
        self.reset_help()
        self.mark_dirty()

    def begin_capture(self, control_id: str, is_new: bool) -> None:
        self.cancel_pending(delete_new=True)
        self.placement_mode = None
        self.pending_control_id = control_id
        self.pending_is_new = is_new
        self.grabKeyboard()
        self.help_title.setText("PRESS AN INPUT")
        self.help_info.setText("Press a key, LMB/RMB/MMB, Mouse 4/5, or scroll Wheel Up/Down. Esc cancels.")
        for widget in self.control_widgets:
            widget.update()

    def complete_pending(self, name: str) -> None:
        control = next((item for item in self.controls if item["id"] == self.pending_control_id), None)
        if not control or control["kind"] not in {"tap", "fire"}:
            return
        control["key"] = normalize_key_name(name, "MOUSE LEFT" if control["kind"] == "fire" else "F")
        self.pending_control_id = None
        self.pending_is_new = False
        self.releaseKeyboard()
        self.reset_help()
        for widget in self.control_widgets:
            widget.update()
        self.mark_dirty()

    def cancel_pending(self, delete_new: bool) -> None:
        control_id = self.pending_control_id
        was_new = self.pending_is_new
        self.pending_control_id = None
        self.pending_is_new = False
        if control_id:
            self.releaseKeyboard()
        if control_id and delete_new and was_new:
            self.delete_control(control_id)
        else:
            for widget in self.control_widgets:
                widget.update()
        if hasattr(self, "help_title"):
            self.reset_help()

    def reset_help(self) -> None:
        self.help_title.setText("QUICK ADD MODE")
        self.help_info.setText("Click any empty game position, then press a keyboard key, mouse button, or wheel.")

    def request_save(self, save_as: bool) -> None:
        if self.pending_control_id:
            QMessageBox.information(self, APP_NAME, "Press a keyboard key, mouse button, or scroll the wheel to finish the pending Tap.")
            return
        self.save_requested.emit(save_as)

    def _create_control_widget(self, control: dict) -> OverlayControl:
        widget = OverlayControl(control, self)
        widget.changed.connect(self.mark_dirty)
        widget.delete_requested.connect(self.delete_control)
        widget.duplicate_requested.connect(self.duplicate_control)
        widget.setVisible(self.edit_mode)
        widget.raise_()
        self.control_widgets.append(widget)
        return widget

    def delete_control(self, control_id: str) -> None:
        if self.pending_control_id == control_id:
            self.cancel_pending(delete_new=False)
        self.controls = [item for item in self.controls if item["id"] != control_id]
        remaining = []
        for widget in self.control_widgets:
            if widget.control["id"] == control_id:
                widget.deleteLater()
            else:
                remaining.append(widget)
        self.control_widgets = remaining
        self.mark_dirty()

    def duplicate_control(self, control_id: str) -> None:
        source = next((item for item in self.controls if item["id"] == control_id), None)
        if not source:
            return
        duplicate = copy.deepcopy(source)
        duplicate["id"] = uuid.uuid4().hex
        duplicate["x"] = min(0.95, duplicate["x"] + 0.04)
        duplicate["y"] = min(0.95, duplicate["y"] + 0.04)
        self.controls.append(duplicate)
        self._create_control_widget(duplicate)
        self.mark_dirty()

    def mark_dirty(self) -> None:
        self.dirty = True
        self.controls_changed.emit()

    def mousePressEvent(self, event) -> None:
        if not self.edit_mode:
            return
        if self.pending_control_id:
            name = mouse_input_from_qt(event.button())
            if name:
                self.complete_pending(name)
                event.accept()
            return
        if event.button() != Qt.LeftButton:
            return
        if self.toolbar.geometry().contains(event.pos()) or self.help_card.geometry().contains(event.pos()):
            return
        if self.placement_mode:
            self.place_special(self.placement_mode, event.pos())
        else:
            self.add_tap_at(event.pos())
        event.accept()

    def wheelEvent(self, event) -> None:
        if self.pending_control_id:
            delta = event.angleDelta().y()
            if delta:
                self.complete_pending("MOUSE WHEEL UP" if delta > 0 else "MOUSE WHEEL DOWN")
                event.accept()
                return
        super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:
        if self.pending_control_id:
            if event.key() == Qt.Key_Escape:
                self.cancel_pending(delete_new=True)
            else:
                name = key_name_from_event(event)
                if name:
                    self.complete_pending(name)
            event.accept()
            return
        if self.placement_mode and event.key() == Qt.Key_Escape:
            self.placement_mode = None
            self.reset_help()
            event.accept()
            return
        super().keyPressEvent(event)

    def follow_target(self) -> None:
        geometry = client_geometry(self.target.hwnd)
        if not geometry:
            self.hide()
            if not self._target_lost_emitted:
                self._target_lost_emitted = True
                self.target_lost.emit()
            return
        self._target_lost_emitted = False
        if self.geometry() != geometry:
            self.setGeometry(geometry)
            self._layout_children()
        if not self.isVisible() and not self.suspended:
            self.show()

    def _layout_children(self) -> None:
        margin = 12
        self.toolbar.setGeometry(margin, margin, max(300, self.width() - margin * 2), 52)
        help_width = min(360, max(230, self.width() // 3))
        self.help_card.setGeometry(self.width() - help_width - margin, 75, help_width, 70)
        for widget in self.control_widgets:
            widget.sync_geometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_children()

    def paintEvent(self, _event) -> None:
        if not self.edit_mode:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(5, 9, 21, 126))
        painter.setPen(QPen(QColor(255, 255, 255, 22), 1))
        grid = 42
        for x in range(0, self.width(), grid):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid):
            painter.drawLine(0, y, self.width(), y)

    def set_edit_mode(self, editing: bool) -> None:
        self.edit_mode = bool(editing)
        if not editing:
            self.cancel_pending(delete_new=True)
            self.placement_mode = None
        self.suspended = False
        hwnd = int(self.winId())
        style = int(GetWindowLongPtr(wintypes.HWND(hwnd), GWL_EXSTYLE))
        if editing:
            style &= ~(WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
        else:
            style |= WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_LAYERED | WS_EX_TOOLWINDOW
        SetWindowLongPtr(wintypes.HWND(hwnd), GWL_EXSTYLE, style)
        self.toolbar.setVisible(editing)
        self.help_card.setVisible(editing)
        for widget in self.control_widgets:
            widget.setVisible(editing)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not editing)
        self.update()
        self.show()
        if editing:
            self.raise_()
            self.activateWindow()

    def apply_overlay(self) -> None:
        if self.pending_control_id:
            QMessageBox.information(self, APP_NAME, "Finish the pending Tap with a keyboard key, mouse button, or wheel direction first.")
            return
        if not self.controls:
            QMessageBox.information(self, APP_NAME, "Add at least one Tap or D-pad control first.")
            return
        self.set_edit_mode(False)
        self.applied.emit()
        user32.SetForegroundWindow(wintypes.HWND(self.target.hwnd))

    def close_editor(self) -> None:
        self.cancel_pending(delete_new=True)
        self.placement_mode = None
        self.suspended = True
        self.hide()
        self.editor_closed.emit()


def build_app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#101a35"))
    painter.drawRoundedRect(3, 3, 58, 58, 15, 15)
    painter.setBrush(QColor("#36d1dc"))
    painter.drawRoundedRect(12, 18, 40, 29, 12, 12)
    painter.setBrush(QColor("#09101f"))
    painter.drawRect(19, 29, 13, 4)
    painter.drawRect(23, 25, 4, 13)
    painter.setBrush(QColor("#ff4d67"))
    painter.drawEllipse(39, 25, 6, 6)
    painter.drawEllipse(45, 33, 6, 6)
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.store = ProfileStore()
        self.icon_provider = QFileIconProvider()
        self.app_icon = build_app_icon()
        self.overlay: Optional[OverlayWindow] = None
        self.active_target: Optional[WindowInfo] = None
        self.current_profile_id: Optional[str] = None
        self.mapping = MappingEngine()
        self.keyboard_hook = GlobalKeyboardHook()
        self.keyboard_hook.key_event.connect(self.on_global_key)
        self.mouse_hook = GlobalMouseHook()
        self.mouse_hook.button_event.connect(self.on_global_mouse)
        self.mouse_hook.movement.connect(self.on_mouse_movement)
        self.mouse_hook.lock_cancelled.connect(self.on_mouse_lock_cancelled)
        self.mapping.on_lock_changed = self.on_mouse_lock_changed
        self.master_enabled = False
        self._f12_down = False
        self.setWindowIcon(self.app_icon)
        self.setWindowTitle(f"{APP_NAME}  {APP_VERSION}")
        self.resize(1180, 730)
        self.setMinimumSize(960, 620)
        self._build_ui()
        self._build_tray()
        self.refresh_profiles()
        QTimer.singleShot(100, self.refresh_apps)
        keyboard_ok = self.keyboard_hook.start()
        mouse_ok = self.mouse_hook.start()
        if not keyboard_ok or not mouse_ok:
            self.set_status("A global input hook could not start. Try running as administrator.", error=True)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 22, 24, 22)
        outer.setSpacing(18)

        header = QHBoxLayout()
        brand_icon = QLabel()
        brand_icon.setPixmap(self.app_icon.pixmap(46, 46))
        header.addWidget(brand_icon)
        titles = QVBoxLayout()
        title = QLabel("GAMING CONTROL OVERLAY")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Select a running app, place emulator-style controls, then apply an invisible overlay.")
        subtitle.setObjectName("subtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch(1)
        shortcut = QLabel("F12  EDIT / APPLY")
        shortcut.setObjectName("shortcutBadge")
        header.addWidget(shortcut)
        outer.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(18)
        apps_card = self._card("1  RUNNING APPLICATIONS", "Choose the emulator or any visible app window.")
        apps_layout = apps_card.layout()
        refresh_row = QHBoxLayout()
        self.app_count = QLabel("0 apps")
        refresh_row.addWidget(self.app_count)
        refresh_row.addStretch(1)
        refresh_button = QPushButton("↻  Refresh")
        refresh_button.clicked.connect(self.refresh_apps)
        refresh_row.addWidget(refresh_button)
        apps_layout.addLayout(refresh_row)
        self.apps_list = QListWidget()
        self.apps_list.setIconSize(QSize(34, 34))
        self.apps_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.apps_list.itemSelectionChanged.connect(self.on_app_selected)
        self.apps_list.itemDoubleClicked.connect(lambda _item: self.new_editor())
        apps_layout.addWidget(self.apps_list, 1)
        content.addWidget(apps_card, 5)

        setup_card = self._card("2  OVERLAY SETUP", "Create a new layout or edit the active one.")
        setup_layout = setup_card.layout()
        self.selected_app_label = QLabel("No application selected")
        self.selected_app_label.setObjectName("selectedTarget")
        self.selected_app_label.setWordWrap(True)
        setup_layout.addWidget(self.selected_app_label)
        mode_label = QLabel("Input delivery")
        mode_label.setObjectName("fieldLabel")
        setup_layout.addWidget(mode_label)
        self.input_mode = QComboBox()
        self.input_mode.addItem("Window message — cursor stays free", "message")
        self.input_mode.addItem("Physical click — better game compatibility", "physical")
        setup_layout.addWidget(self.input_mode)
        self.block_keys = QCheckBox("Block mapped keys from also reaching the target app")
        self.block_keys.setChecked(True)
        setup_layout.addWidget(self.block_keys)
        hint = QLabel(
            "Window message works quietly in the background of the selected window. "
            "If an emulator ignores it, switch to Physical click."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        setup_layout.addWidget(hint)
        self.master_toggle = QPushButton("CONTROL SYSTEM: OFF")
        self.master_toggle.setObjectName("masterToggle")
        self.master_toggle.setCheckable(True)
        self.master_toggle.setProperty("state", "off")
        self.master_toggle.setToolTip("Turn every keyboard, mouse, fire, wheel, and mouse-lock mapping on or off.")
        self.master_toggle.toggled.connect(self.set_master_enabled)
        setup_layout.addWidget(self.master_toggle)
        setup_layout.addStretch(1)
        self.new_button = QPushButton("Create new overlay")
        self.new_button.setObjectName("accentButton")
        self.new_button.clicked.connect(self.new_editor)
        setup_layout.addWidget(self.new_button)
        self.edit_active_button = QPushButton("Edit active overlay")
        self.edit_active_button.clicked.connect(self.edit_active)
        self.edit_active_button.setEnabled(False)
        setup_layout.addWidget(self.edit_active_button)
        self.disable_button = QPushButton("Turn system OFF")
        self.disable_button.clicked.connect(self.disable_mapping)
        self.disable_button.setEnabled(False)
        setup_layout.addWidget(self.disable_button)
        content.addWidget(setup_card, 4)

        profiles_card = self._card("3  SAVED PROFILES", "Saved layouts can be renamed and applied to any selected app.")
        profiles_layout = profiles_card.layout()
        self.profiles_list = QListWidget()
        self.profiles_list.itemDoubleClicked.connect(lambda _item: self.apply_selected_profile())
        profiles_layout.addWidget(self.profiles_list, 1)
        self.apply_profile_button = QPushButton("Apply selected profile")
        self.apply_profile_button.setObjectName("accentButton")
        self.apply_profile_button.clicked.connect(self.apply_selected_profile)
        profiles_layout.addWidget(self.apply_profile_button)
        row = QHBoxLayout()
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self.edit_selected_profile)
        rename_button = QPushButton("Rename")
        rename_button.clicked.connect(self.rename_profile)
        delete_button = QPushButton("Delete")
        delete_button.setObjectName("dangerButton")
        delete_button.clicked.connect(self.delete_profile)
        row.addWidget(edit_button)
        row.addWidget(rename_button)
        row.addWidget(delete_button)
        profiles_layout.addLayout(row)
        content.addWidget(profiles_card, 5)
        outer.addLayout(content, 1)

        status_row = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        self.status_label = QLabel("Ready. Select a running application.")
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        data_location = QLabel(f"Profiles: {self.store.path}")
        data_location.setObjectName("hint")
        status_row.addWidget(data_location)
        outer.addLayout(status_row)

    @staticmethod
    def _card(title_text: str, subtitle_text: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(11)
        title = QLabel(title_text)
        title.setObjectName("cardTitle")
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("hint")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return frame

    def _build_tray(self) -> None:
        self.tray: Optional[QSystemTrayIcon] = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(self.app_icon, self)
        menu = QMenu()
        show_action = menu.addAction("Show control center")
        show_action.triggered.connect(self.show_main)
        edit_action = menu.addAction("Edit / apply active overlay (F12)")
        edit_action.triggered.connect(self.toggle_edit_mode)
        disable_action = menu.addAction("Disable active mapping")
        disable_action.triggered.connect(self.disable_mapping)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.instance().quit)
        tray.setContextMenu(menu)
        tray.setToolTip(APP_NAME)
        tray.activated.connect(lambda reason: self.show_main() if reason == QSystemTrayIcon.DoubleClick else None)
        tray.show()
        self.tray = tray

    def refresh_apps(self) -> None:
        selected_hwnd = self.selected_target().hwnd if self.selected_target() else 0
        self.apps_list.clear()
        try:
            windows = enumerate_windows()
        except OSError as exc:
            self.set_status(f"Could not enumerate applications: {exc}", error=True)
            return
        selected_item = None
        for info in windows:
            icon = self.app_icon
            if info.exe_path and Path(info.exe_path).exists():
                icon = self.icon_provider.icon(QFileInfo(info.exe_path))
            item = QListWidgetItem(icon, f"{info.title}\n{info.process_name}  •  PID {info.pid}")
            item.setData(Qt.UserRole, info)
            item.setSizeHint(QSize(0, 62))
            self.apps_list.addItem(item)
            if info.hwnd == selected_hwnd:
                selected_item = item
        self.app_count.setText(f"{len(windows)} apps")
        if selected_item:
            self.apps_list.setCurrentItem(selected_item)
        self.set_status(f"Found {len(windows)} visible application windows.")

    def select_target_by_title(
        self, title_hint: str, auto_apply: bool = False, attempts_left: int = 16
    ) -> None:
        """Select a matching window, with retries for a newly started scrcpy preview."""
        title_hint = title_hint.strip()
        if not title_hint:
            return

        self.refresh_apps()
        lowered_hint = title_hint.casefold()
        for index in range(self.apps_list.count()):
            item = self.apps_list.item(index)
            info = item.data(Qt.UserRole)
            if info and lowered_hint in info.title.casefold():
                self.apps_list.setCurrentItem(item)
                self.apps_list.scrollToItem(item)
                self.on_app_selected()

                if self.profiles_list.currentItem() is None and self.profiles_list.count() > 0:
                    self.profiles_list.setCurrentRow(0)

                self.show_main()
                self.set_status(f"Connected to {info.title}.")
                if auto_apply:
                    if self.profiles_list.currentItem() is None:
                        self.set_status("ClearMirror was found, but no control profile is available.", error=True)
                    else:
                        QTimer.singleShot(250, self.apply_selected_profile)
                return

        if attempts_left > 1:
            self.set_status(f"Waiting for {title_hint} to open...")
            QTimer.singleShot(
                500,
                lambda: self.select_target_by_title(title_hint, auto_apply, attempts_left - 1),
            )
        else:
            self.set_status(
                f"Could not find {title_hint}. Start mirroring, then open Gaming Controls again.",
                error=True,
            )

    def selected_target(self) -> Optional[WindowInfo]:
        items = self.apps_list.selectedItems()
        return items[0].data(Qt.UserRole) if items else None

    def selected_profile(self) -> Optional[dict]:
        items = self.profiles_list.selectedItems()
        if not items:
            return None
        return self.store.get(str(items[0].data(Qt.UserRole)))

    def on_app_selected(self) -> None:
        target = self.selected_target()
        if target:
            self.selected_app_label.setText(f"{target.title}\n{target.process_name}  •  PID {target.pid}")
            self.set_status(f"Selected {target.process_name}.")
        else:
            self.selected_app_label.setText("No application selected")

    def refresh_profiles(self, select_id: Optional[str] = None) -> None:
        self.profiles_list.clear()
        chosen = None
        for profile in sorted(self.store.profiles, key=lambda item: item["updated_at"], reverse=True):
            target = Path(profile["target_exe"]).name if profile["target_exe"] else "Any app"
            item = QListWidgetItem(self.app_icon, f"{profile['name']}\n{len(profile['controls'])} controls  •  {target}")
            item.setData(Qt.UserRole, profile["id"])
            item.setSizeHint(QSize(0, 61))
            self.profiles_list.addItem(item)
            if profile["id"] == select_id:
                chosen = item
        if chosen:
            self.profiles_list.setCurrentItem(chosen)

    def require_target(self) -> Optional[WindowInfo]:
        target = self.selected_target()
        if not target:
            QMessageBox.information(self, APP_NAME, "Select a running application first.")
            return None
        if not user32.IsWindow(wintypes.HWND(target.hwnd)):
            QMessageBox.warning(self, APP_NAME, "That application window has closed. Refresh and select it again.")
            return None
        return target

    def update_master_toggle(self, enabled: bool) -> None:
        self.master_enabled = bool(enabled)
        if not hasattr(self, "master_toggle"):
            return
        self.master_toggle.blockSignals(True)
        self.master_toggle.setChecked(self.master_enabled)
        self.master_toggle.setText(f"CONTROL SYSTEM: {'ON' if self.master_enabled else 'OFF'}")
        self.master_toggle.setProperty("state", "on" if self.master_enabled else "off")
        self.master_toggle.setToolTip(
            "All configured keyboard and mouse controls are active. Click to turn everything off."
            if self.master_enabled
            else "Mappings are disabled and the mouse is unlocked. Click to activate the current overlay or selected profile."
        )
        style = self.master_toggle.style()
        style.unpolish(self.master_toggle)
        style.polish(self.master_toggle)
        self.master_toggle.update()
        self.master_toggle.blockSignals(False)

    def set_master_enabled(self, enabled: bool) -> None:
        if not enabled:
            self.disable_mapping()
            return

        if self.overlay and self.active_target:
            if not user32.IsWindow(wintypes.HWND(self.active_target.hwnd)):
                self.update_master_toggle(False)
                self.set_status("The selected application is no longer available.", error=True)
                return
            if self.overlay.pending_control_id:
                self.update_master_toggle(False)
                QMessageBox.information(
                    self,
                    APP_NAME,
                    "Finish the pending Tap with a keyboard key, mouse button, or wheel direction first.",
                )
                return
            if not self.overlay.controls:
                self.update_master_toggle(False)
                QMessageBox.information(self, APP_NAME, "Add at least one Tap or D-pad control first.")
                return

            self.overlay.suspended = False
            if self.overlay.edit_mode:
                self.overlay.apply_overlay()
            else:
                self.overlay.set_edit_mode(False)
                self.activate_mapping()
            if self.mapping.enabled:
                user32.SetForegroundWindow(wintypes.HWND(self.active_target.hwnd))
            else:
                self.update_master_toggle(False)
            return

        self.apply_selected_profile()
        if not self.mapping.enabled:
            self.update_master_toggle(False)

    def open_overlay(self, target: WindowInfo, controls: List[dict], profile_id: Optional[str]) -> None:
        self.disable_mapping(close_overlay=True)
        self.active_target = target
        self.current_profile_id = profile_id
        self.overlay = OverlayWindow(target)
        self.overlay.load_controls(controls)
        self.overlay.save_requested.connect(self.save_overlay)
        self.overlay.applied.connect(self.activate_mapping)
        self.overlay.editor_closed.connect(self.on_editor_closed)
        self.overlay.target_lost.connect(self.on_target_lost)
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()
        self.edit_active_button.setEnabled(True)
        self.disable_button.setEnabled(False)
        self.set_status("Editor opened over the selected application. Add or move controls, then Apply.")

    def new_editor(self) -> None:
        target = self.require_target()
        if target:
            self.open_overlay(target, [], None)

    def edit_selected_profile(self) -> None:
        target = self.require_target()
        profile = self.selected_profile()
        if not target:
            return
        if not profile:
            QMessageBox.information(self, APP_NAME, "Select a saved profile first.")
            return
        self.input_mode.setCurrentIndex(1 if profile["input_mode"] == "physical" else 0)
        self.block_keys.setChecked(profile["block_keys"])
        self.open_overlay(target, profile["controls"], profile["id"])

    def edit_active(self) -> None:
        if not self.overlay:
            return
        self.mapping.disable()
        self.keyboard_hook.configure_blocking([], 0, False)
        self.mouse_hook.configure_blocking([], 0, False)
        self.mouse_hook.set_cursor_lock(False, 0)
        self.update_master_toggle(False)
        self.disable_button.setEnabled(False)
        self.overlay.set_edit_mode(True)
        self.set_status("Edit mode active. Controls are visible again.")

    def apply_selected_profile(self) -> None:
        target = self.require_target()
        profile = self.selected_profile()
        if not target:
            return
        if not profile:
            QMessageBox.information(self, APP_NAME, "Select a saved profile first.")
            return
        if not profile["controls"]:
            QMessageBox.information(self, APP_NAME, "This profile does not contain any controls.")
            return
        self.input_mode.setCurrentIndex(1 if profile["input_mode"] == "physical" else 0)
        self.block_keys.setChecked(profile["block_keys"])
        self.open_overlay(target, profile["controls"], profile["id"])
        self.overlay.set_edit_mode(False)
        self.activate_mapping()
        user32.SetForegroundWindow(wintypes.HWND(target.hwnd))

    def save_overlay(self, save_as: bool) -> None:
        if not self.overlay or not self.active_target:
            return
        profile = self.store.get(self.current_profile_id or "")
        if save_as or not profile:
            suggested = profile["name"] if profile else f"{self.active_target.process_name} controls"
            name, accepted = QInputDialog.getText(self, "Save overlay profile", "Profile name", text=suggested)
            name = name.strip()
            if not accepted or not name:
                return
            profile = {
                "id": uuid.uuid4().hex,
                "name": name,
                "created_at": utc_now(),
            }
        profile.update(
            {
                "target_exe": self.active_target.exe_path,
                "target_title_hint": self.active_target.title,
                "input_mode": str(self.input_mode.currentData()),
                "block_keys": self.block_keys.isChecked(),
                "controls": self.overlay.export_controls(),
                "updated_at": utc_now(),
            }
        )
        saved = self.store.upsert(profile)
        self.current_profile_id = saved["id"]
        self.overlay.dirty = False
        self.refresh_profiles(saved["id"])
        self.set_status(f"Saved profile: {saved['name']}")

    def rename_profile(self) -> None:
        profile = self.selected_profile()
        if not profile:
            QMessageBox.information(self, APP_NAME, "Select a saved profile first.")
            return
        name, accepted = QInputDialog.getText(self, "Rename profile", "New name", text=profile["name"])
        name = name.strip()
        if accepted and name:
            profile["name"] = name
            saved = self.store.upsert(profile)
            self.refresh_profiles(saved["id"])
            self.set_status(f"Renamed profile to {name}.")

    def delete_profile(self) -> None:
        profile = self.selected_profile()
        if not profile:
            QMessageBox.information(self, APP_NAME, "Select a saved profile first.")
            return
        answer = QMessageBox.question(
            self,
            "Delete profile",
            f"Delete ‘{profile['name']}’? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.store.remove(profile["id"])
            if self.current_profile_id == profile["id"]:
                self.current_profile_id = None
            self.refresh_profiles()
            self.set_status(f"Deleted profile: {profile['name']}")

    def activate_mapping(self) -> None:
        if not self.overlay or not self.active_target:
            return
        controls = self.overlay.export_controls()
        mode = str(self.input_mode.currentData())
        self.mapping.configure(self.active_target.hwnd, controls, mode)
        self.mapping.enable()
        self.keyboard_hook.configure_blocking(
            self.mapping.mapped_key_names(), self.active_target.hwnd, self.block_keys.isChecked()
        )
        self.mouse_hook.configure_blocking(
            self.mapping.mapped_key_names(), self.active_target.hwnd, self.block_keys.isChecked()
        )
        self.edit_active_button.setEnabled(True)
        self.update_master_toggle(self.mapping.enabled)
        self.disable_button.setEnabled(self.mapping.enabled)
        if self.mapping.enabled:
            self.set_status(
                f"Mapping active on {self.active_target.process_name}. Overlay is transparent; press F12 to edit."
            )
        else:
            self.set_status("No controls are available to activate.", error=True)

    def disable_mapping(self, close_overlay: bool = False) -> None:
        self.mapping.disable()
        self.keyboard_hook.configure_blocking([], 0, False)
        self.mouse_hook.configure_blocking([], 0, False)
        self.mouse_hook.set_cursor_lock(False, 0)
        self.update_master_toggle(False)
        if close_overlay and self.overlay:
            self.overlay.follow_timer.stop()
            self.overlay.hide()
            self.overlay.deleteLater()
            self.overlay = None
        elif self.overlay:
            self.overlay.suspended = True
            self.overlay.hide()
        self.disable_button.setEnabled(False)
        if not close_overlay:
            self.set_status("Active mapping disabled.")

    def on_editor_closed(self) -> None:
        self.mapping.disable()
        self.keyboard_hook.configure_blocking([], 0, False)
        self.mouse_hook.configure_blocking([], 0, False)
        self.mouse_hook.set_cursor_lock(False, 0)
        self.update_master_toggle(False)
        self.disable_button.setEnabled(False)
        self.set_status("Editor hidden. Re-open it from Edit active overlay.")

    def on_target_lost(self) -> None:
        self.mapping.disable()
        self.keyboard_hook.configure_blocking([], 0, False)
        self.mouse_hook.configure_blocking([], 0, False)
        self.mouse_hook.set_cursor_lock(False, 0)
        self.update_master_toggle(False)
        self.disable_button.setEnabled(False)
        self.set_status("The selected application closed or its window is unavailable.", error=True)

    def on_global_key(self, vk: int, down: bool) -> None:
        if self.overlay and self.overlay.edit_mode and self.overlay.pending_control_id:
            return
        if vk == KEY_TO_VK["F12"]:
            if down and not self._f12_down:
                self._f12_down = True
                self.toggle_edit_mode()
            elif not down:
                self._f12_down = False
            return
        self.mapping.handle_key(vk, down)

    def on_global_mouse(self, name: str, down: bool) -> None:
        self.mapping.handle_input(name, down)

    def on_mouse_movement(self, dx: int, dy: int) -> None:
        self.mapping.handle_mouse_move(dx, dy)

    def on_mouse_lock_changed(self, enabled: bool) -> None:
        hwnd = self.active_target.hwnd if enabled and self.active_target else 0
        self.mouse_hook.set_cursor_lock(enabled, hwnd)
        if enabled:
            self.set_status("Mouse locked. Move to aim; press the configured lock key again to release.")
        elif self.mapping.enabled:
            self.set_status("Mouse unlocked. Mapping remains active.")

    def on_mouse_lock_cancelled(self) -> None:
        self.mapping.cancel_mouse_lock()
        if self.mapping.enabled:
            self.set_status("Mouse unlocked because the target application lost focus.")

    def toggle_edit_mode(self) -> None:
        if not self.overlay:
            self.show_main()
            self.set_status("No active overlay. Select an application and create or apply a profile.", error=True)
            return
        if self.overlay.edit_mode:
            self.overlay.apply_overlay()
        else:
            self.edit_active()

    def set_status(self, message: str, error: bool = False) -> None:
        self.status_label.setText(message)
        self.status_dot.setStyleSheet(f"color: {'#ff5b71' if error else '#45e0a8'};")

    def show_main(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:
        if self.tray and self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                APP_NAME,
                "Still running in the system tray. Press F12 to edit/apply the active overlay.",
                QSystemTrayIcon.Information,
                2500,
            )
        else:
            event.accept()

    def shutdown(self) -> None:
        self.mapping.disable()
        self.keyboard_hook.stop()
        self.mouse_hook.stop()
        if self.overlay:
            self.overlay.follow_timer.stop()
            self.overlay.close()


STYLE = """
QWidget {
    background: #09101f;
    color: #eaf0ff;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow { background: #080e1c; }
QLabel#pageTitle { font-size: 21pt; font-weight: 800; letter-spacing: 1px; }
QLabel#subtitle, QLabel#hint { color: #8492ad; }
QLabel#shortcutBadge {
    color: #36d1dc; background: #102238; border: 1px solid #244964;
    border-radius: 8px; padding: 8px 13px; font-weight: 700;
}
QLabel#quickBadge {
    color: #45e0a8; background: #10291f; border: 1px solid #27694f;
    border-radius: 7px; padding: 6px 9px; font-weight: 800;
}
QFrame#card {
    background: #0d172a; border: 1px solid #1c2a43; border-radius: 13px;
}
QLabel#cardTitle { color: #f6f8ff; font-weight: 800; font-size: 11pt; }
QLabel#fieldLabel { color: #aeb9cf; font-weight: 700; margin-top: 4px; }
QLabel#selectedTarget {
    background: #111f35; border: 1px solid #263b59; border-radius: 9px;
    padding: 12px; color: #dfe7f8; font-weight: 600;
}
QListWidget {
    background: #091222; border: 1px solid #1b2b44; border-radius: 9px;
    outline: none; padding: 5px;
}
QListWidget::item { border-radius: 7px; padding: 7px; margin: 2px; color: #cfd8eb; }
QListWidget::item:selected { background: #173450; color: white; border: 1px solid #2e6687; }
QPushButton {
    background: #17243a; border: 1px solid #293c59; border-radius: 7px;
    padding: 8px 12px; color: #e5eaf5; font-weight: 600;
}
QPushButton:hover { background: #20324d; border-color: #3c587e; }
QPushButton:disabled { color: #536079; background: #111a2b; border-color: #1b2639; }
QPushButton#accentButton {
    color: #06131d; background: #36d1dc; border-color: #36d1dc; font-weight: 800;
}
QPushButton#accentButton:hover { background: #5de1e9; }
QPushButton#dangerButton { color: #ff8b9b; }
QPushButton#masterToggle {
    min-height: 36px; font-size: 11pt; font-weight: 900; letter-spacing: 1px;
}
QPushButton#masterToggle[state="off"] {
    color: #ff9aaa; background: #321523; border: 1px solid #8b3049;
}
QPushButton#masterToggle[state="off"]:hover { background: #462031; border-color: #d34c6c; }
QPushButton#masterToggle[state="on"] {
    color: #06150f; background: #45e0a8; border: 1px solid #45e0a8;
}
QPushButton#masterToggle[state="on"]:hover { background: #6aefbd; border-color: #6aefbd; }
QComboBox {
    background: #111d31; border: 1px solid #2a3d5c; border-radius: 7px;
    padding: 8px 10px; min-height: 20px;
}
QComboBox QAbstractItemView { background: #111d31; selection-background-color: #1d4967; }
QCheckBox { color: #b7c2d7; spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QFrame#overlayToolbar {
    background: rgba(9, 16, 31, 242); border: 1px solid #31455f; border-radius: 10px;
}
QLabel#overlayTitle { background: transparent; font-weight: 900; color: #ffffff; }
QFrame#overlayHelp {
    background: rgba(9, 16, 31, 230); border: 1px solid #31455f; border-radius: 9px;
}
QFrame#overlayToolbar QLabel, QFrame#overlayHelp QLabel { background-color: transparent; }
QLabel#helpTitle { color: #36d1dc; font-weight: 800; }
QDialog { background: #0d172a; }
QMenu { background: #101a2c; border: 1px solid #2d405d; padding: 5px; }
QMenu::item { padding: 7px 25px; border-radius: 5px; }
QMenu::item:selected { background: #1d4967; }
"""


def enable_dpi_awareness() -> None:
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def command_line_value(name: str) -> Optional[str]:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return None
    return sys.argv[index + 1] if index + 1 < len(sys.argv) else None


def qt_arguments() -> List[str]:
    custom_flags = {"--smoke-test", "--auto-apply"}
    custom_values = {"--target-title"}
    result: List[str] = []
    skip_next = False
    for argument in sys.argv:
        if skip_next:
            skip_next = False
            continue
        if argument in custom_flags:
            continue
        if argument in custom_values:
            skip_next = True
            continue
        result.append(argument)
    return result


def main() -> int:
    enable_dpi_awareness()
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling, True)
    smoke_test = "--smoke-test" in sys.argv
    target_title = command_line_value("--target-title")
    auto_apply = "--auto-apply" in sys.argv
    qt_argv = qt_arguments()
    app = QApplication(qt_argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(build_app_icon())
    window = MainWindow()
    app.aboutToQuit.connect(window.shutdown)
    window.show()
    if target_title:
        QTimer.singleShot(350, lambda: window.select_target_by_title(target_title, auto_apply))
    if smoke_test:
        QTimer.singleShot(1200, app.quit)
    result = app.exec_()
    if smoke_test:
        print("SMOKE_TEST_OK")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
