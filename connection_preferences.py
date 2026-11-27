"""Local connection policy cache and appearance; no credentials or business records."""
import json
import os
from pathlib import Path
import re
import threading

_lock = threading.RLock()
FOLDERS = {'pos':'MGCYFCPOS', 'office':'CoastYouthRetailOffice', 'ops':'CoastYouthRetailStoreOps'}
DEFAULTS = dict(timeout_seconds=10, background='#eef3f8', panel='#ffffff', text='#19334a',
                muted='#41586c', accent='#245c8e', border='#8da4ba')

def contrast(a,b):
    def luminance(color):
        channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        return sum(weight*(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4) for weight,c in zip((.2126,.7152,.0722),channels))
    left,right=sorted((luminance(a),luminance(b)))
    return (right+.05)/(left+.05)
def clean(value):
    result = dict(DEFAULTS)
    if not isinstance(value, dict): return result
    timeout = value.get('timeout_seconds')
    if type(timeout) is int and 1 <= timeout <= 120: result['timeout_seconds'] = timeout
    if value.get('managed') is True:result['managed']=True
    for key in ('background','panel','text','muted','accent','border'):
        if isinstance(value.get(key),str) and re.fullmatch(r'#[0-9a-fA-F]{6}',value[key]):
            result[key] = value[key]
    for key in ('text','muted'):
        if contrast(result[key],result['panel'])<4.5:
            result[key]=max(('#ffffff','#142536'),key=lambda color:contrast(color,result['panel']))
    return result

def path(app):
    return Path(os.environ.get('APPDATA',str(Path.home()))) / FOLDERS[app] / 'connection-appearance.json'

def load(app):
    try: return clean(json.loads(path(app).read_text(encoding='utf-8')))
    except (OSError,ValueError): return dict(DEFAULTS)

def save(app, value):
    with _lock:
        target=path(app); target.parent.mkdir(parents=True,exist_ok=True)
        result=clean(value); temporary=target.with_suffix('.tmp')
        with temporary.open('w',encoding='utf-8') as out:
            json.dump(result,out);out.flush();os.fsync(out.fileno())
        os.replace(temporary,target)
        return result

def bridge_preferences(bridge, app, value=None):
    if not bridge._trusted(): return {'error':'Open the configured application.'}
    try: return load(app) if value is None else save(app,value)
    except OSError: return {'error':'Connection appearance settings could not be saved.'}
