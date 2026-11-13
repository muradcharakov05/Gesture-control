import ctypes
from ctypes import wintypes
import threading


class GlobalPauseKey:
    """F8 pauses; control can only be enabled using the application button."""
    def __init__(self, callback):
        self.callback = callback
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.registered = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        user32 = ctypes.windll.user32
        self.registered = bool(user32.RegisterHotKey(None, 1, 0x4000, 0x77))
        self.ready.set()
        if not self.registered:
            return
        try:
            msg = wintypes.MSG()
            while not self.stop_event.is_set():
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == 0x0312 and msg.wParam == 1:
                        self.callback()
                self.stop_event.wait(0.025)
        finally:
            user32.UnregisterHotKey(None, 1)

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=1)
