"""Hidden native OFFICE client against isolated shared server data."""
import tempfile,time,traceback
from pathlib import Path
import webview
from office_desktop import office_window
from test_update_coordination import CoordinatorFixture

def run():
 import faulthandler
 faulthandler.dump_traceback_later(80,exit=True)
 f=CoordinatorFixture();tmp=tempfile.TemporaryDirectory();errors=[];w=office_window(f'http://127.0.0.1:{f.port}',Path(tmp.name),hidden=True)
 def wait(js):
  for _ in range(150):
   try:
    if w.events.loaded.is_set() and w.evaluate_js("document.readyState==='complete' && ("+js+")"):return
   except Exception:pass
   time.sleep(.1)
  raise AssertionError('Timed out: '+js)
 def test():
  try:
   wait("document.querySelector('#login') && typeof officeAction==='function'")
   w.evaluate_js("document.querySelector('#login [name=name]').value='Admin';document.querySelector('#login [name=password]').value='testpassword';document.querySelector('#login').requestSubmit()")
   wait("document.querySelectorAll('#officeTiles button').length===29")
   w.evaluate_js("officeAction('users')")
   wait("document.querySelector('#officeUserRows').textContent.includes('Employee')")
   w.evaluate_js("let field=document.querySelector('#officeAddUser [name=name]');field.value='Unsaved sample';field.dispatchEvent(new Event('input',{bubbles:true}))")
   assert w.evaluate_js('unfinished()')
   w.destroy();time.sleep(.3)
   wait("document.querySelector('#posStatus').textContent.includes('before closing OFFICE')")
   w.evaluate_js("document.querySelector('#officeAddUser').reset()")
   wait('!unfinished()');w.destroy()
  except Exception:
   errors.append(traceback.format_exc())
   try:w.evaluate_js('changedForms.clear();posPending=null;writeCount=0;posBusy=false');w.destroy()
   except Exception:pass
 try:
  webview.start(test,gui='edgechromium',debug=False,private_mode=True,storage_path=str(Path(tmp.name)/'webview'))
  if errors:raise AssertionError(errors[0])
  print('PASS native OFFICE login, shared users and unsaved-work close protection')
 finally:
  f.close()
  for _ in range(30):
   try:tmp.cleanup();break
   except PermissionError:time.sleep(.2)
if __name__=='__main__':run()
