import os
"""Hidden native OFFICE client against isolated shared server data."""
import tempfile,time,traceback
from pathlib import Path
import webview
from office_desktop import office_window
from test_update_coordination import CoordinatorFixture

def run():
 import faulthandler
 faulthandler.dump_traceback_later(80,exit=True)
 f=CoordinatorFixture();tmp=tempfile.TemporaryDirectory();errors=[];os.environ['APPDATA']=tmp.name;w=office_window(f'http://127.0.0.1:{f.port}',Path(tmp.name),hidden=True)
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
   w.show()
   assert not w.events.maximized.is_set(), 'Login should start at the normal window size'
   w.evaluate_js("document.querySelector('#login [name=name]').value='Admin';document.querySelector('#login [name=password]').value='wrong-test-password';document.querySelector('#login').requestSubmit()")
   wait("document.querySelector('#authError').textContent.length>0")
   assert not w.events.maximized.is_set(), 'Failed sign-in must not maximize OFFICE'
   w.evaluate_js("document.querySelector('#login [name=name]').value='Admin';document.querySelector('#login [name=password]').value='testpassword';document.querySelector('#login').requestSubmit()")
   wait("document.querySelector('#officeTiles [data-office-category=staff]') && document.querySelector('#officeTiles [data-office-category=accounts]')")
   assert w.events.maximized.wait(5), 'Successful sign-in should maximize OFFICE'
   wait("document.querySelector('#nativeTerminalForm')")
   w.evaluate_js("document.querySelector('#nativeTerminalForm').requestSubmit()")
   wait("document.querySelector('#nativeTerminalStatus').textContent.includes('Registered') && !document.querySelector('#nativeTerminalSetup').open")
   w.restore();w.events.maximized.clear()
   w.evaluate_js('boot()');time.sleep(.3)
   assert not w.events.maximized.is_set(), 'Refreshing OFFICE must not override a manually restored window'
   w.evaluate_js("document.querySelector('#signOut').click()")
   wait("!document.querySelector('#auth').hidden")
   w.evaluate_js("document.querySelector('#login [name=name]').value='Admin';document.querySelector('#login [name=password]').value='testpassword';document.querySelector('#login').requestSubmit()")
   assert w.events.maximized.wait(5), 'A new sign-in should maximize OFFICE again'
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
  print('PASS native OFFICE sign-in maximizes, failed sign-in stays normal, manual restore is respected, shared users and unsaved-work close protection')
 finally:
  f.close()
  for _ in range(30):
   try:tmp.cleanup();break
   except PermissionError:time.sleep(.2)
if __name__=='__main__':run()
