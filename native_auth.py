"""Protect the combined server's local session token with Windows DPAPI."""
import ctypes,os
from pathlib import Path

class Blob(ctypes.Structure):
    _fields_=[('size',ctypes.c_ulong),('data',ctypes.c_void_p)]

def protect(raw,decrypt=False):
    if os.name!='nt':raise OSError('Windows-protected local sign-in is unavailable.')
    buffer=ctypes.create_string_buffer(raw);source=Blob(len(raw),ctypes.cast(buffer,ctypes.c_void_p));target=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    function=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(Blob)]
    function.restype=ctypes.c_int
    if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):raise ctypes.WinError(ctypes.get_last_error())
    try:return ctypes.string_at(target.data,target.size)
    finally:
        free=ctypes.WinDLL('kernel32',use_last_error=True).LocalFree
        free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p;free(target.data)

def save_token(path,token):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_bytes(protect(token.encode()));temporary.replace(path)

def load_token(path):
    try:return protect(Path(path).read_bytes(),True).decode()
    except (OSError,ValueError,UnicodeError):return None
