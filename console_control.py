"""Control only this program's dedicated classic Windows console window."""
import ctypes
from ctypes import wintypes as w
class ConsoleWindow:
    def __init__(self,icon_path):
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.kernel.GetConsoleWindow.restype=w.HWND
        self.hwnd=self.kernel.GetConsoleWindow()
        if not self.hwnd:raise RuntimeError('Use the MGC YFC Operations Server Console shortcut to open a dedicated console.')
        self.kernel.SetConsoleTitleW.argtypes=[w.LPCWSTR]
        self.kernel.SetConsoleTitleW('MGC YFC Operations Server — Console')
        self.user.LoadImageW.argtypes=[w.HINSTANCE,w.LPCWSTR,w.UINT,ctypes.c_int,ctypes.c_int,w.UINT]
        self.user.LoadImageW.restype=w.HANDLE
        self.user.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        self.user.SendMessageW.restype=w.LPARAM
        self.user.ShowWindow.argtypes=[w.HWND,ctypes.c_int]
        self.user.IsIconic.argtypes=[w.HWND];self.user.IsIconic.restype=w.BOOL
        self.user.IsWindowVisible.argtypes=[w.HWND];self.user.IsWindowVisible.restype=w.BOOL
        self.user.SetForegroundWindow.argtypes=[w.HWND]
        self.user.GetSystemMenu.argtypes=[w.HWND,w.BOOL];self.user.GetSystemMenu.restype=w.HMENU
        self.user.EnableMenuItem.argtypes=[w.HMENU,w.UINT,w.UINT]
        self.icons=[]
        for kind,size in ((0,16),(1,32)):
            icon=self.user.LoadImageW(None,str(icon_path),1,size,size,0x10)
            if not icon:raise ctypes.WinError(ctypes.get_last_error())
            self.icons.append(icon);self.user.SendMessageW(self.hwnd,0x80,kind,icon)
        # The console host cannot redirect X to our Tk loop. Disable X and use the
        # tray's confirmed Exit command, preventing an accidental server shutdown.
        menu=self.user.GetSystemMenu(self.hwnd,False)
        self.user.EnableMenuItem(menu,0xF060,0x0001) # SC_CLOSE, MF_GRAYED
        self._handler=ctypes.WINFUNCTYPE(w.BOOL,w.DWORD)(lambda event:event in (0,1))
        self.kernel.SetConsoleCtrlHandler(self._handler,True)
    def minimized(self):return bool(self.user.IsIconic(self.hwnd))
    def visible(self):return bool(self.user.IsWindowVisible(self.hwnd))
    def hide(self):self.user.ShowWindow(self.hwnd,0)
    def minimize(self):self.user.ShowWindow(self.hwnd,6)
    def show(self):self.user.ShowWindow(self.hwnd,9);self.user.SetForegroundWindow(self.hwnd)
    def verify_icons(self):
        return all(self.user.SendMessageW(self.hwnd,0x7F,kind,0)==icon for kind,icon in enumerate(self.icons))
