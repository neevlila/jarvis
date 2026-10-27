"""
Pytest configuration and environment shims for CI and cross-platform testing.
Ensures headless environments (Linux CI runners, Docker containers) can collect
and execute tests without physical displays or Windows-only C-extensions.
"""
import sys
from unittest.mock import MagicMock

# 1. Provide mock pyautogui if missing (e.g. headless Linux in GitHub Actions)
if "pyautogui" not in sys.modules:
    try:
        import pyautogui
    except Exception:
        mock_pyautogui = MagicMock()
        mock_pyautogui.size.return_value = (1920, 1080)
        mock_pyautogui.screenshot.return_value = True
        sys.modules["pyautogui"] = mock_pyautogui

# 2. Provide mock win32 modules if running on non-Windows platforms
_WIN32_MODULES = [
    "win32gui",
    "win32con",
    "win32process",
    "win32api",
    "win32com",
    "win32com.client",
    "uiautomation",
]

for mod in _WIN32_MODULES:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except Exception:
            mock_mod = MagicMock()
            if mod == "win32con":
                mock_mod.SW_RESTORE = 9
                mock_mod.WM_CLOSE = 0x0010
            elif mod == "win32gui":
                mock_mod.GetForegroundWindow.return_value = 0
                mock_mod.GetWindowText.return_value = ""
                mock_mod.GetWindowRect.return_value = (0, 0, 1920, 1080)
                mock_mod.IsWindowVisible.return_value = False
                mock_mod.EnumWindows.return_value = None
            elif mod == "win32process":
                mock_mod.GetWindowThreadProcessId.return_value = (0, 0)
            elif mod == "win32api":
                mock_mod.GetCurrentThreadId.return_value = 0
            sys.modules[mod] = mock_mod
