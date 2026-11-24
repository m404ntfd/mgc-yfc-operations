"""Print the receipt-only view to a named Windows printer using WebView2."""
import hashlib,json,os,threading,time
from pathlib import Path
_lock=threading.Lock()

def print_shift(bridge,printer,shift):
    """Print only the visible, server-sourced register-shift report."""
    if not bridge._trusted():return {'error':'Open the configured application.'}
    if not isinstance(printer,str) or printer not in printers(bridge).get('printers',[]):return {'error':'The configured receipt printer is not installed on this computer. The shift report is saved.'}
    if not _lock.acquire(blocking=False):return {'error':'Another document is printing. Try again when it finishes.'}
    try:
        if bridge._window.evaluate_js('document.getElementById("registerShiftPaper")?.dataset.shift')!=str(shift):return {'error':'The shift report changed. Reopen it before printing.'}
        from webview.platforms.winforms import BrowserView
        from System import Action
        form=BrowserView.instances[bridge._window.uid];result={};ready=threading.Event()
        def start():
            try:
                core=form.browser.webview.CoreWebView2;settings=core.Environment.CreatePrintSettings()
                settings.PrinterName=printer;settings.ShouldPrintBackgrounds=True;settings.ShouldPrintHeaderAndFooter=False
                result['task']=core.PrintAsync(settings)
            except Exception as exc:result['error']=str(exc)
            finally:ready.set()
        form.BeginInvoke(Action(start))
        if not ready.wait(10):return {'error':'Printer status is uncertain. Check the printer before reprinting. The shift report is saved.'}
        if result.get('error'):return {'error':'Could not print the shift report: '+result['error']}
        task=result['task'];deadline=time.monotonic()+30
        while not task.IsCompleted and time.monotonic()<deadline:time.sleep(.05)
        if not task.IsCompleted:return {'error':'Printer status is uncertain. The shift report is saved; check the printer before reprinting.'}
        status=str(task.GetAwaiter().GetResult())
        if status!='Succeeded':return {'error':'Shift printing failed ('+status+'). Reprint the saved report after checking the printer.'}
        return {'ok':True}
    except Exception as exc:return {'error':'Shift report printing failed: '+str(exc)}
    finally:_lock.release()

def printers(bridge):
    if not bridge._trusted():return {'error':'Open the configured application.'}
    try:
        import clr
        clr.AddReference('System.Drawing')
        from System.Drawing.Printing import PrinterSettings
        return {'printers':[str(p) for p in PrinterSettings.InstalledPrinters]}
    except Exception as exc:return {'error':'Could not list Windows printers: '+str(exc),'printers':[]}

def print_receipt(bridge,printer,sale,automatic=False):
    if not bridge._trusted():return {'error':'Open the configured application.'}
    if not isinstance(printer,str) or not printer:return {'error':'Select a receipt printer in Terminal setup.'}
    if printer not in printers(bridge).get('printers',[]):return {'error':'The configured receipt printer is not installed on this computer. The transaction is saved; use Print receipts after checking the printer.'}
    if not _lock.acquire(blocking=False):return {'error':'Another receipt is printing. Try Print receipts when it finishes.'}
    try:
        if bridge._window.evaluate_js('document.getElementById("automaticReceiptPaper")?.dataset.sale')!=str(sale):return {'error':'The receipt preview changed. Reopen the saved receipt before printing.'}
        from webview.platforms.winforms import BrowserView
        from System import Action
        form=BrowserView.instances[bridge._window.uid]
        key=hashlib.sha256((bridge._window.get_current_url().split('#')[0]+'|'+str(sale)).encode()).hexdigest()
        directory=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'CoastYouthRetail'/'receipt-print-history'
        marker=directory/(key+'.json')
        if automatic:
            directory.mkdir(parents=True,exist_ok=True)
            try:
                with marker.open('x') as f:json.dump({'status':'requested','at':time.time()},f)
            except FileExistsError:return {'ok':True,'already':True}
        result={};ready=threading.Event()
        def start():
            try:
                core=form.browser.webview.CoreWebView2;settings=core.Environment.CreatePrintSettings()
                settings.PrinterName=printer;settings.ShouldPrintBackgrounds=True;settings.ShouldPrintHeaderAndFooter=False
                result['task']=core.PrintAsync(settings)
            except Exception as exc:result['error']=str(exc)
            finally:ready.set()
        form.BeginInvoke(Action(start))
        if not ready.wait(10):return {'error':'Printer status is uncertain. Check the printer before manually reprinting. The transaction is saved.'}
        if result.get('error'):return {'error':'Could not print: '+result['error']+'. The transaction is saved.'}
        task=result['task'];deadline=time.monotonic()+30
        while not task.IsCompleted and time.monotonic()<deadline:time.sleep(.05)
        if not task.IsCompleted:return {'error':'Printer status is uncertain. Check the printer before manually reprinting. The transaction is saved.'}
        status=str(task.GetAwaiter().GetResult())
        if automatic:marker.write_text(json.dumps({'status':status,'at':time.time()}))
        if status!='Succeeded':return {'error':'Receipt printing failed ('+status+'). The transaction is saved. Check the printer and use Print receipts.'}
        return {'ok':True}
    except Exception as exc:return {'error':'Receipt printing failed: '+str(exc)+'. The transaction is saved.'}
    finally:_lock.release()
