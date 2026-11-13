import ctypes
from ctypes import wintypes
from dataclasses import dataclass

user32 = ctypes.windll.user32

@dataclass(frozen=True)
class Monitor:
    name: str
    left: int
    top: int
    width: int
    height: int


def monitors():
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    def callback(handle, dc, rect, param):
        r = rect.contents
        found.append(Monitor(f"Экран {len(found)+1} ({r.right-r.left} × {r.bottom-r.top})", r.left, r.top, r.right-r.left, r.bottom-r.top))
        return True
    cb = callback_type(callback)
    user32.EnumDisplayMonitors(None, None, cb, 0)
    return found


def map_point(x, y, bounds, monitor):
    left, top, right, bottom = bounds
    x = max(0., min(1., (x-left) / max(.01, right-left)))
    y = max(0., min(1., (y-top) / max(.01, bottom-top)))
    return (monitor.left + 2 + round(x * max(0, monitor.width-5)),
            monitor.top + 2 + round(y * max(0, monitor.height-5)))


def move(x, y):
    if not user32.SetCursorPos(int(x), int(y)):
        raise OSError('Не удалось переместить курсор')


def mouse_down():
    user32.mouse_event(0x0002, 0, 0, 0, 0)


def mouse_up():
    user32.mouse_event(0x0004, 0, 0, 0, 0)


def left_click():
    mouse_down(); mouse_up()


def right_click():
    user32.mouse_event(0x0008, 0, 0, 0, 0)
    user32.mouse_event(0x0010, 0, 0, 0, 0)


def scroll(steps):
    user32.mouse_event(0x0800, 0, 0, ctypes.c_ulong(int(steps)*120), 0)
