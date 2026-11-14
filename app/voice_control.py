import ctypes
from ctypes import wintypes
from app.instance import kernel32, show_existing

STOP_EVENT = r'Local\GestureControlJarvisStop'
kernel32.CreateEventW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.BOOL,wintypes.LPCWSTR]
kernel32.CreateEventW.restype=wintypes.HANDLE
kernel32.OpenEventW.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.LPCWSTR]
kernel32.OpenEventW.restype=wintypes.HANDLE
kernel32.SetEvent.argtypes=[wintypes.HANDLE]
kernel32.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]


def listener_running():
    handle=kernel32.OpenEventW(0x00100000,False,STOP_EVENT)
    if handle:kernel32.CloseHandle(handle)
    return bool(handle)


def stop_listener():
    handle=kernel32.OpenEventW(0x0002,False,STOP_EVENT)
    if handle:
        kernel32.SetEvent(handle);kernel32.CloseHandle(handle)
