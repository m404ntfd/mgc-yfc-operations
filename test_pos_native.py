"""Real hidden WebView2 integration; isolated server and local device settings."""
import tempfile,time,traceback
from pathlib import Path
import webview
from pos_kiosk import KioskStore,KioskBridge
from test_update_coordination import CoordinatorFixture

def run():
 import faulthandler
 faulthandler.dump_traceback_later(100,exit=True)
 f=CoordinatorFixture();tmp=tempfile.TemporaryDirectory();errors=[]
 store=KioskStore(Path(tmp.name)/'settings.json');origin=f'http://127.0.0.1:{f.port}'
 bridge=KioskBridge(store,origin)
 w=webview.create_window('POS isolated native test',origin+'/pos?kiosk=1',js_api=bridge,hidden=True,fullscreen=True,frameless=True,easy_drag=False,resizable=False)
 bridge._window=w;w.events.closing+=bridge._closing
 w.events.loaded+=lambda:print('Native page loaded',flush=True)
 def wait(js):
  for _ in range(100):
   try:
    if w.events.loaded.is_set() and w.evaluate_js("document.readyState==='complete' && ("+js+")"):return
   except Exception:pass
   time.sleep(.1)
  raise AssertionError('Timed out: '+js)
 def test():
  try:
   wait("window.pywebview && document.querySelector('#posExitButton') && !document.querySelector('#posExitButton').hidden")
   assert w.fullscreen and w.frameless and not w.resizable
   w.evaluate_js("document.querySelector('#login [name=name]').value='Admin';document.querySelector('#login [name=password]').value='testpassword';document.querySelector('#login').requestSubmit()")
   wait("document.querySelector('#kioskSetupDialog').open")
   w.evaluate_js("document.querySelector('#kioskPasscodeForm [name=code]').value='123456';document.querySelector('#kioskPasscodeForm [name=confirm]').value='123456';document.querySelector('#kioskPasscodeForm').requestSubmit()")
   wait("document.body.dataset.kiosk==='ready'");assert KioskStore(store.path).verify('123456')
   assert bridge._closing() is False
   wait("document.querySelector('#posExitDialog').open")
   w.evaluate_js("document.querySelector('#posExitCancel').click()")
   for tool,target in [('clock','#workforce'),('reservations','#schedule'),('paging','#paging')]:
    wait('window.posKioskCanLeave && window.posKioskCanLeave()');print('Opening',tool,flush=True);result=bridge.open_operations(tool);assert result.get('ok'),result
    wait("document.querySelector('#returnNativePos') && document.querySelector('"+target+"') && !document.querySelector('"+target+"').hidden")
    wait('window.posKioskCanLeave && window.posKioskCanLeave()');print('Returning to POS',flush=True);result=bridge.open_operations('pos');assert result.get('ok'),result
    wait("document.body.dataset.kiosk==='ready'")
   wait('window.posKioskCanLeave && window.posKioskCanLeave()');assert bridge.open_operations('office').get('ok')
   wait("document.querySelector('#officeHub') && !document.querySelector('#officeHub').hidden && document.body.dataset.kiosk==='ready'")
   assert bridge._trusted();assert bridge._closing() is False
   wait("document.querySelector('#posExitDialog').open");w.evaluate_js("document.querySelector('#posExitCancel').click()")
   w.evaluate_js("document.querySelector('#posAdmin').open=true;document.querySelector('#changeKioskPasscode').click();document.querySelector('#kioskPasscodeForm [name=code]').value='987654';document.querySelector('#kioskPasscodeForm [name=confirm]').value='987654';document.querySelector('#kioskPasscodeForm').requestSubmit()")
   wait("!document.querySelector('#kioskSetupDialog').open && !kioskBusy")
   assert not KioskStore(store.path).verify('123456');assert KioskStore(store.path).verify('987654')
   wait('window.posKioskCanLeave && window.posKioskCanLeave()');assert bridge.open_operations('pos').get('ok')
   wait("document.body.dataset.kiosk==='ready'")
   # Real dirty form blocks native exit even with the correct passcode.
   w.evaluate_js("let el=document.querySelector('#posManual [name=name]');el.value='unfinished';el.dispatchEvent(new Event('input',{bubbles:true}))")
   assert 'error' in bridge.request_exit('987654')
   w.evaluate_js("document.querySelector('#posManual').reset()")
   wait('!unfinished()')
   assert bridge.request_exit('987654').get('ok')
  except Exception:
   errors.append(traceback.format_exc());bridge._exiting=True;w.destroy()
 try:
  webview.start(test,gui='edgechromium',debug=False,private_mode=True,storage_path=str(Path(tmp.name)/'webview'))
  if errors:raise AssertionError(errors[0])
  print('PASS real WebView2 fullscreen, first setup, close veto, admin passcode change, Operations roundtrips and dirty-work exit guard')
 finally:
  f.close()
  # WebView2 subprocesses can retain cache handles briefly after the window closes.
  for _ in range(30):
   try:tmp.cleanup();break
   except PermissionError:time.sleep(.2)

if __name__=='__main__':run()
