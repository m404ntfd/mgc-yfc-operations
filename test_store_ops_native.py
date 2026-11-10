"""Run the real STORE OPS WebView2 window against synthetic server data only."""
import tempfile, time, traceback
from pathlib import Path
import webview
from store_ops_desktop import ops_window
from test_update_coordination import CoordinatorFixture

def run():
    import faulthandler
    faulthandler.dump_traceback_later(100, exit=True)
    f = CoordinatorFixture(); tmp = tempfile.TemporaryDirectory(); errors = []
    w = ops_window(f"http://127.0.0.1:{f.port}", hidden=True)
    def wait(js):
        for _ in range(200):
            try:
                if w.evaluate_js(js): return
            except Exception: pass
            time.sleep(.1)
        raise AssertionError("Timed out: " + js)
    def test():
        try:
            wait('typeof hasUnfinishedWork === "function" && document.querySelector("#login")')
            assert not w.evaluate_js('!!document.querySelector(".posNativeToolbar")')
            w.evaluate_js("document.querySelector('#login [name=name]').value='Admin';document.querySelector('#login [name=password]').value='testpassword';document.querySelector('#login').requestSubmit()")
            wait('typeof user !== "undefined" && user && user.admin')
            assert w.evaluate_js('!!document.querySelector("#work") || !!document.querySelector("#paging")')
            # Exercise the shared unsaved-work guard without creating business records.
            w.evaluate_js("let f=document.createElement('form');f.id='opsTestForm';f.innerHTML='<input name=test>';document.body.append(f);changedForms.set(f,'test')")
            w.destroy(); time.sleep(.5)
            assert not w._ops_guard.exiting
            wait('document.querySelector("#toast").textContent.includes("before closing STORE OPS")')
            w.evaluate_js("document.querySelector('#opsTestForm').remove();changedForms.clear()")
            wait('!hasUnfinishedWork()')
            w.destroy()
        except Exception:
            errors.append(traceback.format_exc());w._ops_guard.exiting=True;w.destroy()
    try:
        webview.start(test, gui='edgechromium', debug=False, private_mode=True, storage_path=str(Path(tmp.name)/'webview'))
        if errors: raise AssertionError(errors[0])
        print('PASS native STORE OPS login, full web app, no POS controls, unsaved-work close guard')
    finally:
        f.close()
        for _ in range(30):
            try: tmp.cleanup(); break
            except PermissionError: time.sleep(.2)
if __name__ == '__main__': run()
