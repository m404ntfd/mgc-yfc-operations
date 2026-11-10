"""Verified POS installer staging and safe, out-of-process application replacement."""
import hashlib,json,os,re,shutil,subprocess,sys,threading,time
from pathlib import Path
from urllib.request import Request,urlopen
VERSION='1.15.0'
REPO='m404ntfd/mgc-yfc-operations'
def version(value):
 if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value):raise ValueError('Invalid POS version.')
 return tuple(map(int,value.split('.')))
def fetch(url,limit=1000000):
 with urlopen(Request(url,headers={'User-Agent':'MGC-YFC-POS-Updater'}),timeout=30) as response:data=response.read(limit+1)
 if len(data)>limit:raise ValueError('POS download exceeds its size limit.')
 return data
def verified_installer(expected,app='pos'):
 release=json.loads(fetch('https://api.github.com/repos/'+REPO+'/releases/latest'))
 if release.get('draft') or release.get('prerelease'):raise ValueError('Stable POS release required.')
 name={'office':'CoastYouth-Retail-OFFICE-Setup-v','pos':'MGC-YFC-POS-Setup-v','ops':'CoastYouth-Retail-STORE-OPS-Setup-v'}[app]+expected+'.exe'
 asset=next((a for a in release.get('assets',[]) if a.get('name')==name),None)
 if not asset:raise ValueError('The POS release changed. Ask an administrator to check again.')
 digest=asset.get('digest','');url=asset.get('browser_download_url','')
 if not re.fullmatch(r'sha256:[a-f0-9]{64}',digest) or not url.startswith('https://github.com/'+REPO+'/releases/download/'):raise ValueError('Verified POS download information is missing.')
 raw=fetch(url,100*1024*1024)
 if 'sha256:'+hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('POS download checksum mismatch. Nothing was installed.')
 return raw,digest[7:]
class PosUpdater:
 def __init__(self,bridge,app='pos',current=None):
  self.app=app;self.version=current or VERSION
  self.bridge=bridge;self.job=None;self.deadline=0;self.state='idle';self.error='';self.path=None;self.digest=None;self.lock=threading.RLock()
 def ticket(self,ident):
  if not isinstance(ident,str) or not re.fullmatch('[0-9a-f]{64}',ident):raise ValueError('Invalid update request.')
  return json.loads(fetch(self.bridge._address+'/api/'+self.app+'-update/ticket?id='+ident))
 def observe(self,ident):
  if not self.bridge._trusted():return {'error':'Open the configured server.'}
  with self.lock:
   if not ident:self.job=None;self.state='idle';return {'state':'idle','version':self.version}
   try:
    job=self.ticket(ident)
    if job.get('target') not in ('all',self.bridge._store.data['device']) and self.bridge._store.data['device'] not in job.get('targets',[]):return {'state':'idle','version':self.version}
    if version(job['version'])<=version(self.version):return {'state':'complete','version':self.version}
    if not self.job or self.job['id']!=ident:
     seconds=job.get('seconds')
     if type(seconds) is not int or not (30<=seconds<=3600 or seconds==0 and job.get('mode') in ('force','install')):raise ValueError('Invalid warning period.')
     self.job=job;self.deadline=time.monotonic()+seconds;self.state='downloading';self.error='';self.path=None
     threading.Thread(target=self.download,args=(dict(job),),daemon=True).start()
    return {'state':self.state,'seconds':max(0,int(self.deadline-time.monotonic()+.999)),'version':self.version,'target':job['version'],'error':self.error}
   except Exception as e:return {'state':'error','error':str(e),'version':self.version}
 def download(self,job):
  try:
   raw,digest=verified_installer(job['version'],self.app);folder=self.bridge._store.path.parent/'updates'/job['id'];folder.mkdir(parents=True,exist_ok=True)
   path=folder/'installer.exe';path.write_bytes(raw)
   with self.lock:
    if self.job and self.job['id']==job['id']:self.path=path;self.digest=digest;self.state='ready'
  except Exception as e:
   with self.lock:
    if self.job and self.job['id']==job['id']:self.state='error';self.error=str(e)
 def install(self):
  with self.lock:
   b=self.bridge
   if not b._trusted() or not self.job or self.state!='ready':raise ValueError('The verified POS installer is not ready.')
   if time.monotonic()<self.deadline:raise ValueError('Allow the employee warning countdown to finish.')
   current=self.ticket(self.job['id'])
   if current!=self.job:raise ValueError('The update request changed. Check again.')
   if not getattr(sys,'frozen',False):raise ValueError('Automatic installation is available in the installed Windows POS application.')
   if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.digest:raise ValueError('Installer verification failed.')
   # Freeze only if the current sale is finished and no draft/write/retry is pending.
   if b._window.evaluate_js('window.posUpdateFreeze ? window.posUpdateFreeze('+('true' if self.job.get('mode')=='force' else 'false')+') : false') is not True:raise ValueError('Return to POS and finish or cancel the current sale; save all unfinished entries.')
   try:
    exe=Path(sys.executable).resolve();helper=self.path.parent/'pos-update-helper.exe';shutil.copy2(exe,helper)
    manifest=self.path.parent/'install.json';manifest.write_text(json.dumps({'installer':str(self.path),'sha256':self.digest,'exe':str(exe),'pid':os.getpid(),'version':self.job['version'],'settings':str(b._store.path)}),encoding='utf-8')
    subprocess.Popen([str(helper),'--apply-pos-update',str(manifest)],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    self.state='installing';b._exiting=True;b._window.destroy();return {'ok':True}
   except Exception:
    b._window.run_js('window.posUpdateUnfreeze && window.posUpdateUnfreeze()');raise

def apply_update(manifest_path):
 """Runs from a copied helper, after the original POS process releases its files."""
 import ctypes
 manifest=Path(manifest_path);meta=json.loads(manifest.read_text(encoding='utf-8'));exe=Path(meta['exe']);installer=Path(meta['installer']);settings=Path(meta['settings']);result=settings.parent/'pos-update-result.json'
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_bool,ctypes.c_uint32];kernel.OpenProcess.restype=ctypes.c_void_p;kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
 handle=kernel.OpenProcess(0x100000,False,int(meta['pid']))
 if handle:
  try:
   if kernel.WaitForSingleObject(handle,90000)!=0:raise ValueError('POS did not close safely; installation canceled.')
  finally:kernel.CloseHandle(handle)
 outcome={'version':meta['version'],'ok':False}
 try:
  if hashlib.sha256(installer.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('Installer checksum mismatch.')
  if settings.exists():shutil.copy2(settings,manifest.parent/'settings-backup.json')
  command=[str(installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/DIR='+str(exe.parent),'/LOG='+str(manifest.parent/'installer.log')]
  done=subprocess.run(command,timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  if done.returncode not in (0,3010):raise ValueError('Installer failed with code '+str(done.returncode)+'. Check the installer log; settings backup was retained.')
  outcome['ok']=True
 except Exception as e:outcome['error']=str(e)
 result.write_text(json.dumps(outcome),encoding='utf-8')
 if exe.exists():subprocess.Popen([str(exe)],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
