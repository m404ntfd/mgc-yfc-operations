"""Device-local POS exit protection. No timecard/reservation database access."""
import hashlib,hmac,json,os,re,secrets,threading,time
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler,ProxyHandler
from urllib.error import HTTPError

class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

class KioskStore:
 def __init__(self,path,clock=time.time):
  self.path=Path(path);self.clock=clock;self.lock=threading.RLock()
  if self.path.exists():
   try:self.data=json.loads(self.path.read_text(encoding='utf-8'))
   except Exception as e:raise ValueError('POS settings cannot be read. Restore the settings backup or contact an administrator; protection was not reset.') from e
   if not isinstance(self.data,dict):raise ValueError('Invalid POS settings. Protection was not reset.')
  else:self.data={}
  if 'passcode' in self.data:
   record=self.data['passcode']
   if not isinstance(record,dict) or record.get('rounds')!=600000 or not re.fullmatch('[0-9a-f]{32}',str(record.get('salt',''))) or not re.fullmatch('[0-9a-f]{64}',str(record.get('hash',''))):raise ValueError('Exit protection settings are damaged. Contact an administrator.')
  if not re.fullmatch('[0-9a-f]{32}',str(self.data.get('device',''))):
   if self.configured:raise ValueError('Device identifier is missing. Contact an administrator.')
   self.data['device']=secrets.token_hex(16);self.save()
 @property
 def configured(self):return 'passcode' in self.data
 def save(self):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  temp=self.path.with_suffix('.tmp')
  with temp.open('w',encoding='utf-8') as out:
   json.dump(self.data,out);out.flush();os.fsync(out.fileno())
  os.replace(temp,self.path)
 def set_passcode(self,code,confirmation):
  if not isinstance(code,str) or not re.fullmatch('[0-9]{6,12}',code):raise ValueError('Use 6 to 12 digits for the admin exit passcode.')
  if code!=confirmation:raise ValueError('The passcodes do not match.')
  with self.lock:
   salt=secrets.token_hex(16)
   record={'rounds':600000,'salt':salt,'hash':hashlib.pbkdf2_hmac('sha256',code.encode(),bytes.fromhex(salt),600000).hex()}
   before=dict(self.data)
   self.data.update(passcode=record,failures=0,blocked_until=0)
   try:self.save()
   except Exception:self.data=before;raise
 def verify(self,code):
  with self.lock:
   if not self.configured:return False
   now=self.clock();until=self.data.get('blocked_until',0)
   if now<until:raise ValueError('Too many incorrect attempts. Try again in '+str(max(1,int(until-now)))+' seconds.')
   record=self.data['passcode']
   valid=isinstance(code,str) and bool(re.fullmatch('[0-9]{6,12}',code))
   hashed=hashlib.pbkdf2_hmac('sha256',(code if valid else '').encode(),bytes.fromhex(record['salt']),record['rounds']).hex()
   ok=valid and hmac.compare_digest(hashed,record['hash'])
   if ok:self.data.update(failures=0,blocked_until=0)
   else:
    failures=self.data.get('failures',0)+1
    self.data.update(failures=failures if failures<5 else 0,blocked_until=now+60 if failures>=5 else 0)
   self.save()
   return ok

class KioskBridge:
 def __init__(self,store,address,redeem=None):
  self._store=store;self._address=address.rstrip('/');self._window=None;self._nonce=secrets.token_hex(32);self._exiting=False;self._lock=threading.RLock();self._redeem=redeem or self._redeem_remote
 def _trusted(self):
  from urllib.parse import urlsplit
  url=self._window.get_current_url() if self._window else None
  if not url:return False
  p=urlsplit(url);base=urlsplit(self._address)
  return (p.scheme,p.netloc)==(base.scheme,base.netloc) and p.path in ('/pos','/pos/','/')
 def _redeem_remote(self,token):
  req=Request(self._address+'/api/pos/kiosk-redeem',data=json.dumps({'token':token,'device':self._store.data['device'],'nonce':self._nonce}).encode(),headers={'Content-Type':'application/json','X-Dispatch':'1'})
  try:
   with build_opener(ProxyHandler({}),NoRedirect()).open(req,timeout=15) as r:return json.loads(r.read(8192))
  except HTTPError as e:
   try:message=json.loads(e.read(8192)).get('error','Administrator approval failed.')
   except Exception:message='Administrator approval failed.'
   raise ValueError(message) from e
 def kiosk_info(self):
  if not self._trusted():return {'error':'Open the configured Operations server.'}
  return {'device':self._store.data['device'],'nonce':self._nonce,'configured':self._store.configured}
 def configure_passcode(self,token,code,confirmation):
  try:
   with self._lock:
    if not self._trusted():raise ValueError('Open the configured Operations server.')
    if not isinstance(code,str) or not re.fullmatch('[0-9]{6,12}',code):raise ValueError('Use 6 to 12 digits.')
    if code!=confirmation:raise ValueError('The passcodes do not match.')
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{64}',token):raise ValueError('Administrator approval is required.')
    approval=self._redeem(token)
    if approval.get('device')!=self._store.data['device'] or approval.get('nonce')!=self._nonce or approval.get('admin') is not True:raise ValueError('Administrator approval does not match this checkout computer.')
    self._store.set_passcode(code,confirmation);self._nonce=secrets.token_hex(32)
    return {'ok':True}
  except Exception as e:return {'error':str(e)}
 def request_exit(self,code):
  try:
   with self._lock:
    if not self._trusted():raise ValueError('Return to POS before exiting.')
    if self._store.configured and not self._store.verify(code):raise ValueError('Incorrect admin passcode.')
    if self._window.evaluate_js('window.posKioskCanLeave ? window.posKioskCanLeave() : false') is not True:raise ValueError('Finish or save your current work before exiting.')
    self._exiting=True;self._window.destroy();return {'ok':True}
  except Exception as e:return {'error':str(e)}
 def open_operations(self,tool):
  try:
   if not self._trusted() or not self._store.configured:raise ValueError('Complete admin passcode setup first.')
   targets={'clock':'#pos-time-clock','reservations':'#pos-reservations','paging':'#pos-paging','pos':'pos?kiosk=1'}
   if tool not in targets:raise ValueError('Unknown Operations function.')
   if self._window.evaluate_js('window.posKioskCanLeave ? window.posKioskCanLeave() : false') is not True:raise ValueError('Finish or save your current work first.')
   self._window.load_url(self._address+'/'+targets[tool]);return {'ok':True}
  except Exception as e:return {'error':str(e)}
 def _closing(self):
  if self._exiting:return True
  if self._window:
   try:self._window.run_js('window.showPosKioskExit && window.showPosKioskExit()')
   except Exception:pass
  return False
