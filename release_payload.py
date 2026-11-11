"""Lossless web-asset packaging within the existing updater size limit."""
import ast, base64, gzip, json

def release_bytes(root,name):
    raw=(root/name).read_bytes()
    if name=='server.py':
        # Compress only the embedded HTML/CSS/JS data, never executable Python.
        # Older updaters still receive an ordinary, compilable server.py file.
        source=raw.decode('utf-8')
        for node in ast.parse(source).body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='POS_ASSETS' for t in node.targets):
                assets=ast.literal_eval(node.value)
                payload=base64.b64encode(gzip.compress(json.dumps(assets,ensure_ascii=False).encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
                lines=source.splitlines(keepends=True)
                replacement="import gzip as _web_asset_gzip\nPOS_ASSETS=json.loads(_web_asset_gzip.decompress(base64.b64decode("+repr(payload)+"))) # lossless packaged web assets\n"
                return (''.join(lines[:node.lineno-1])+replacement+''.join(lines[node.end_lineno:])).encode('utf-8')
        raise ValueError('Embedded POS web assets were not found for packaging.')
    return gzip.compress(raw,compresslevel=9,mtime=0) if name.startswith('static/') and not raw.startswith(b'\x1f\x8b') else raw
