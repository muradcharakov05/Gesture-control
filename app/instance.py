import ctypes
from ctypes import wintypes

APP_TITLE = 'Gesture Control — управление жестами'
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE


def show_existing():
    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    handle = user32.FindWindowW(None, APP_TITLE)
    if handle:
        user32.ShowWindow(handle, 9)
        user32.SetForegroundWindow(handle)
    return bool(handle)


def app_lock():
    handle = kernel32.CreateMutexW(None, False, r'Local\GestureControlApp')
    if not handle: raise OSError("Не удалось проверить запущенный экземпляр")
    duplicate = ctypes.get_last_error() == 183
    return handle, duplicate
