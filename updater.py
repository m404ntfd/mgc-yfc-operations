"""GitHub public-release updates. Customer data never enters the release archive."""
import hashlib, io, json, os, re, shutil, sqlite3, time, urllib.request, zipfile
from pathlib import Path
from contextlib import closing
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('DISPATCH_DATA',ROOT/'data'))
FILES=('server.py','updater.py','VERSION','README.txt','static/index.html','static/app.js','static/style.css')
ASSET='Store-Dispatch-Update.zip'
LIMIT=10*1024*1024

def version(v):
    if not re.fullmatch(r'v?\d+\.\d+\.\d+',v): raise ValueError('Release versions must look like v0.2.0.')
    return tuple(map(int,v.lstrip('v').split('.')))

def current(): return (ROOT/'VERSION').read_text().strip()
def repo():
    p=DATA/'updates.json'
    return json.loads(p.read_text()).get('repository','') if p.exists() else 'm404ntfd/mgc-yfc-operations'
def configure(value):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',value): raise ValueError('Enter a GitHub repository as owner/repository.')
    DATA.mkdir(exist_ok=True,parents=True)
    tmp=DATA/'updates.tmp'; tmp.write_text(json.dumps({'repository':value})); os.replace(tmp,DATA/'updates.json')
def fetch(url,limit=LIMIT):
    req=urllib.request.Request(url,headers={'User-Agent':'Store-Dispatch-Updater','Accept':'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req,timeout=25) as r: raw=r.read(limit+1)
    except Exception as e: raise ValueError('GitHub could not be reached, the repository is private, or no release exists. Check the repository and Internet connection.') from e
    if len(raw)>limit: raise ValueError('Release download is too large.')
    return raw

def check():
    repository=repo()
    if not repository: raise ValueError('Save the GitHub repository first.')
    release=json.loads(fetch(f'https://api.github.com/repos/{repository}/releases/latest',1000000))
    tag=release['tag_name']; newer=version(tag)>version(current())
    asset=next((a for a in release.get('assets',[]) if a['name']==ASSET),None)
    if release.get('draft') or release.get('prerelease'): raise ValueError('Only stable published releases are supported.')
    return {'current':current(),'latest':tag.lstrip('v'),'available':newer,'notes':release.get('body') or '', 'asset':asset,'repository':repository}

def inspect(raw,expected):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if len(names)!=len(FILES) or set(names)!=set(FILES): raise ValueError('Update archive has unexpected or missing files.')
        if sum(i.file_size for i in z.infolist())>LIMIT: raise ValueError('Expanded update is too large.')
        contents={name:z.read(name) for name in FILES}
    if contents['VERSION'].decode().strip()!=expected: raise ValueError('Release version and archive version do not match.')
    for name in ('server.py','updater.py'): compile(contents[name],name,'exec')
    return contents

def stage(expected):
    release=check()
    if not release['available'] or release['latest']!=expected: raise ValueError('The release changed. Check for updates again.')
    a=release['asset']
    if not a: raise ValueError(f'The release must include {ASSET}.')
    digest=a.get('digest') or ''
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',digest): raise ValueError('GitHub has not supplied a SHA-256 checksum for this asset.')
    url=a.get('browser_download_url','')
    if not url.startswith(f"https://github.com/{release['repository']}/releases/download/"): raise ValueError('Unexpected release download address.')
    raw=fetch(url)
    if 'sha256:'+hashlib.sha256(raw).hexdigest()!=digest: raise ValueError('Download checksum mismatch. Nothing was installed.')
    inspect(raw,expected)
    stage_dir=DATA/'pending-update'; stage_dir.mkdir(exist_ok=True)
    (stage_dir/'release.zip').write_bytes(raw)
    (stage_dir/'manifest.json').write_text(json.dumps({'version':expected,'sha256':digest[7:]}))

def apply():
    """Called only after the server exits. Backup first; restore code on copy failure."""
    pending=DATA/'pending-update'
    if not (pending/'manifest.json').exists(): raise ValueError('No staged update exists.')
    meta=json.loads((pending/'manifest.json').read_text()); raw=(pending/'release.zip').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=meta['sha256']: raise ValueError('Staged update checksum mismatch.')
    contents=inspect(raw,meta['version'])
    if version(meta['version'])<=version(current()): raise ValueError('Refusing to install an older or identical version.')
    backup=DATA/'update-backups'/str(time.time_ns()); backup.mkdir(parents=True)
    for name in FILES:
        target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    if (DATA/'schedule.db').exists():
        with closing(sqlite3.connect(DATA/'schedule.db')) as src, closing(sqlite3.connect(backup/'schedule.db')) as dst: src.backup(dst)
    if (DATA/'hr-encryption.key').exists():shutil.copy2(DATA/'hr-encryption.key',backup/'hr-encryption.key')
    try:
        for name,content in contents.items():
            target=ROOT/name; temp=target.with_name(target.name+'.update');temp.write_bytes(content);os.replace(temp,target)
    except Exception:
        for name in FILES: shutil.copy2(backup/name,ROOT/name)
        raise
    shutil.rmtree(pending)
    (DATA/'last-update.json').write_text(json.dumps({'version':meta['version'],'backup':str(backup),'at':time.strftime('%Y-%m-%d %H:%M:%S')}))
    return backup

def rollback_code(backup):
    for name in FILES: shutil.copy2(Path(backup)/name,ROOT/name)
