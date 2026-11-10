"""Isolated coordinator HTTP tests; downloads and restart are replaced, never installed."""
import unittest,tempfile,threading,os,json,http.cookiejar,urllib.request,time
from pathlib import Path
from unittest.mock import patch
import server

class CoordinatorFixture:
 def __init__(self):
  self.tmp=tempfile.TemporaryDirectory();self.done=threading.Event();self.patches=[]
  for module,name,value in [(server,'DATA',Path(self.tmp.name)),(server,'DB',Path(self.tmp.name)/'schedule.db'),(server.updater,'DATA',Path(self.tmp.name)),(server,'SESSIONS',{}),(server,'HR_SESSIONS',{}),(server,'CLOCK_SESSIONS',{}),(server,'UPDATE_FLOW',None),(server,'RESTART',False),(server,'STOPPING',False)]:
   p=patch.object(module,name,value);p.start();self.patches.append(p)
  p=patch.dict(os.environ,{'OneDrive':'','OneDriveConsumer':'','OneDriveCommercial':'','DISPATCH_LAUNCHER':'1'});p.start();self.patches.append(p)
  p=patch.object(server.updater,'stage',return_value=None);self.stage=p.start();self.patches.append(p)
  server.init()
  self.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);self.port=self.http.server_port
  self.stop=self.http.shutdown;self.http.shutdown=self.done.set
  self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
  self.admin=self.client('a');self.call('setup',dict(name='Admin',password='testpassword'),self.admin)
  for name in ['Employee','Second']:self.call('user',dict(name=name,password='testpassword'),self.admin)
 def client(self,key):return (urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())),key*32)
 def call(self,path,data=None,client=None):
  opener,key=client or self.admin
  req=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-Dispatch':'1','X-Dispatch-Connection':key,'Content-Type':'application/json'})
  try:
   with opener.open(req) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:
   with e:return e.code,json.load(e)
 def wait(self,predicate):
  for _ in range(100):
   if predicate():return
   time.sleep(.03)
  raise AssertionError('Timed out')
 def close(self):
  with server.LOCK:
   if server.UPDATE_FLOW:server.UPDATE_FLOW['phase']='canceled'
  time.sleep(.6);self.stop();self.http.server_close();self.thread.join()
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()

class CoordinationTests(unittest.TestCase):
 def setUp(self):self.f=CoordinatorFixture()
 def tearDown(self):self.f.close()
 def test_wait_freeze_receipt_and_legacy_adoption(self):
  f=self.f;e=f.client('b');f.call('login',dict(name='Employee',password='testpassword'),e)
  other=(f.admin[0],'c'*32);f.call('account/connection',{},other)
  self.assertEqual(f.call('update-flow/start',dict(version='99.0.0',ready=True),e)[0],403)
  code,start=f.call('update-flow/start',dict(version='99.0.0',ready=True));self.assertEqual(code,200)
  f.wait(lambda:server.UPDATE_FLOW['phase']=='waiting')
  self.assertEqual(f.call('update-flow')[1]['waiting'],2)
  self.assertFalse(f.done.is_set())
  self.assertEqual(f.call('login',dict(name='Second',password='testpassword'),f.client('d'))[0],423)
  self.assertEqual(f.call('account/appearance',dict(mode='dark'),e)[0],200)
  self.assertEqual(f.call('update-flow/acknowledge',dict(id=start['id'],ready=True),e)[0],200)
  self.assertEqual(f.call('account/appearance',dict(mode='light'),e)[0],423)
  self.assertEqual(f.call('update-flow')[1]['waiting'],1)
  self.assertFalse(f.done.is_set())
  f.call('update-flow/acknowledge',dict(id=start['id'],ready=True),other)
  self.assertTrue(f.done.wait(3));self.assertTrue(server.RESTART)
  self.assertEqual(f.call('update-result?receipt=bad')[0],404)
  with server.LOCK:server.UPDATE_FLOW=None;server.RESTART=False
  with patch.object(server.updater,'current',return_value='99.0.0'):
   self.assertEqual(f.call('update-result?receipt='+start['receipt'])[1]['phase'],'complete')
  self.assertEqual(f.call('update-result?receipt='+start['receipt'])[1]['phase'],'failed')
 def test_disconnected_user_does_not_auto_ack_and_cancel_unfreezes(self):
  f=self.f;e=f.client('b');f.call('login',dict(name='Employee',password='testpassword'),e)
  start=f.call('update-flow/start',dict(version='99.0.0',ready=True))[1];f.wait(lambda:server.UPDATE_FLOW['phase']=='waiting')
  with server.LOCK:
   for session in server.SESSIONS.values():
    if session['name']=='Employee':
     for conn in session['connections'].values():conn['last_seen']=time.time()-3600
  self.assertEqual(f.call('update-flow')[1]['waiting'],1)
  self.assertFalse(f.done.wait(.7))
  self.assertEqual(f.call('update-flow/cancel',dict(id=start['id']),e)[0],403)
  self.assertEqual(f.call('update-flow/cancel',dict(id=start['id']))[0],200)
  self.assertEqual(f.call('account/appearance',dict(mode='dark'),e)[0],200)
 def test_failed_download_does_not_restart(self):
  f=self.f;f.stage.side_effect=ValueError('Download checksum mismatch')
  result=f.call('update-flow/start',dict(version='99.0.0',ready=True))[1]
  f.wait(lambda:server.UPDATE_FLOW['phase']=='failed')
  self.assertFalse(f.done.is_set());self.assertFalse(server.RESTART)
  self.assertIn('checksum',f.call('update-result?receipt='+result['receipt'])[1]['error'])
 def test_bootstrap_connection_is_adopted_not_duplicated(self):
  f=self.f;legacy=(f.client('e')[0],'')
  f.call('login',dict(name='Employee',password='testpassword'),legacy)
  browser=(legacy[0],'f'*32);f.call('account/connection',{},browser)
  rows=f.call('admin/update-connections')[1]['connections']
  self.assertEqual(len([row for row in rows if row['name']=='Employee']),1)
 def test_shift_save_retries_are_idempotent(self):
  f=self.f
  with server.connect() as c:account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
  data=dict(account=account,start='2026-12-01T09:00',end='2026-12-01T17:00',location='',job='',notes='Keep this',save_request='1'*32)
  code,first=f.call('workforce/shift',data);self.assertEqual(code,200)
  self.assertEqual(f.call('workforce/shift',data)[1],first)
  with server.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM work_shifts').fetchone()[0],1)
  self.assertEqual(f.call('workforce/shift',dict(data,notes='different'))[0],409)
  edit=dict(data,id=first['shift']['id'],revision=first['shift']['revision'],notes='Edited',save_request='2'*32)
  code,result=f.call('workforce/shift',edit);self.assertEqual(code,200)
  self.assertEqual(f.call('workforce/shift',edit)[1],result)
  self.assertEqual(result['shift']['revision'],first['shift']['revision']+1)
if __name__=='__main__':unittest.main()
