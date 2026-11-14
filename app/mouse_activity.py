"""Observe physical mouse input, ignoring all events injected by software."""
import ctypes
from ctypes import wintypes
import threading
import time

class MouseActivity:
    def __init__(self):
        self.last_activity=0.; self.available=False
        self.event_count=0;self.last_flags=None
        self.ready=threading.Event();self.stop=threading.Event()
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def _run(self):
        u=ctypes.WinDLL('user32',use_last_error=True)
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        class MouseInfo(ctypes.Structure):
            _fields_=[('pt',wintypes.POINT),('mouseData',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        callback_type=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM)
        u.SetWindowsHookExW.argtypes=[ctypes.c_int,callback_type,wintypes.HINSTANCE,wintypes.DWORD];u.SetWindowsHookExW.restype=wintypes.HANDLE
        u.CallNextHookEx.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM];u.CallNextHookEx.restype=ctypes.c_ssize_t
        u.UnhookWindowsHookEx.argtypes=[wintypes.HANDLE]
        k.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];k.GetModuleHandleW.restype=wintypes.HMODULE
        def callback(code,wparam,lparam):
            if code>=0:
                info=ctypes.cast(lparam,ctypes.POINTER(MouseInfo)).contents
                self.record_input(info.flags,time.monotonic())
            return u.CallNextHookEx(None,code,wparam,lparam)
        self.callback=callback_type(callback)
        handle=u.SetWindowsHookExW(14,self.callback,k.GetModuleHandleW(None),0)
        self.available=bool(handle);self.ready.set()
        if not handle:return
        try:
            msg=wintypes.MSG()
            while not self.stop.is_set():
                while u.PeekMessageW(ctypes.byref(msg),None,0,0,1):
                    u.TranslateMessage(ctypes.byref(msg));u.DispatchMessageW(ctypes.byref(msg))
                self.stop.wait(.01)
        finally:u.UnhookWindowsHookEx(handle)
    def record_input(self,flags,now):
        self.event_count+=1;self.last_flags=flags
        if not flags & 1:self.last_activity=now
    def close(self):self.stop.set();self.thread.join(timeout=1)
