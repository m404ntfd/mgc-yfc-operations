"""Lossless static packaging within the existing updater size limit."""
import gzip

def release_bytes(root,name):
    raw=(root/name).read_bytes()
    return gzip.compress(raw,compresslevel=9,mtime=0) if name.startswith('static/') and not raw.startswith(b'\x1f\x8b') else raw
