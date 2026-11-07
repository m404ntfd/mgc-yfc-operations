"""Real hidden WebView2 integration; isolated server and local device settings."""
import tempfile,time,traceback
from pathlib import Path
import webview
from pos_kiosk import KioskStore,KioskBridge
from test_update_coordination import CoordinatorFixture

def run():
 f=CoordinatorFixture();tmp=tempfile.TemporaryDirectory();errors=[]
 store=KioskStore(Path(tmp.name)/'settings.json');origin=f'http://127.0.0.1:{f.port}'
 bridge=KioskBridge(store,origin)
 w=webview.create_window('POS isolated native test',origin+'/pos?kiosk=1',js_api=bridge,hidden=True,fullscreen=True,frameless=True,easy_drag=False,resizable=False)
 bridge._window=w;w.events.closing+=bridge._closing
 def wait(js):
  for _ in range(100):
   try:
    if w.evaluate_js(js):return
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
   wait("document.body.dataset.kiosk==='ready'");assert store.verify('123456')
   assert bridge._closing() is False
   wait("document.querySelector('#posExitDialog').open")
   w.evaluate_js("document.querySelector('#posExitCancel').click()")
   for tool,target in [('clock','#workforce'),('reservations','#schedule'),('paging','#paging')]:
    assert bridge.open_operations(tool).get('ok'),tool
    wait("document.querySelector('#returnNativePos') && document.querySelector('"+target+"') && !document.querySelector('"+target+"').hidden")
    assert bridge.open_operations('pos').get('ok')
    wait("document.body.dataset.kiosk==='ready'")
   w.evaluate_js("document.querySelector('#posAdmin').open=true;document.querySelector('#changeKioskPasscode').click();document.querySelector('#kioskPasscodeForm [name=code]').value='987654';document.querySelector('#kioskPasscodeForm [name=confirm]').value='987654';document.querySelector('#kioskPasscodeForm').requestSubmit()")
   wait("!document.querySelector('#kioskSetupDialog').open && !kioskBusy")
   assert not store.verify('123456');assert store.verify('987654')
   # Real dirty form blocks native exit even with the correct passcode.
   w.evaluate_js("let el=document.querySelector('#posSetup [name=store]');el.value='unfinished';el.dispatchEvent(new Event('input',{bubbles:true}))")
   assert 'error' in bridge.request_exit('987654')
   w.evaluate_js("document.querySelector('#posSetup').reset()")
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
