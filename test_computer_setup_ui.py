"""Exercise the native installer wizard with a fake server; never touches installed apps."""
import copy,os,traceback
from pathlib import Path
import tkinter as tk
from unittest.mock import patch
from computer_setup import RegistrationWizard


class SampleClient:
    identity={'id':'1'*32,'hostname':'THRIFT-REGISTER-1'}
    apps=['pos','office'];pending=None;details=None;address='https://operations.coastyfc.com'
    calls=0;registrations=0
    def saved_addresses(self):return {'pos':self.address,'office':self.address}
    def requires_exit_code(self):return False
    def connect(self,address,user,password):
        assert user=='Sample administrator' and password=='sample-only-password'
        self.calls+=1
        if self.calls==1:raise ValueError('Sample connection interrupted. Check the server address or VPN, then retry.')
        self.details={'computer':{'id':'1'*32,'hostname':'THRIFT-REGISTER-1','name':'Thrift Mart Checkout 1','role':'pos','registered':True,'revision':3},
                      'stores':[{'id':'thrift-mart','name':'Thrift Mart'},{'id':'binopoly','name':'Binopoly'}],
                      'available_terminals':[],'terminal':{'id':'original-terminal','name':'Thrift Mart Checkout 1','revision':2},
                      'matched_by_mac':True,'removed_terminal':False,'active_mac':'02:AA:BB:CC:DD:10','active_adapter':'Ethernet'}
        return copy.deepcopy(self.details)
    def register(self,name,role,store,terminal,restore,code,reuse):
        assert reuse and name=='Thrift Mart Checkout 1' and role=='pos'
        self.registrations+=1
        return self.details
    def close(self):pass


def run():
    root=tk.Tk();client=SampleClient();wizard=RegistrationWizard(root,client,role='pos')
    stage=[0];errors=[];ticks=[0]
    folder=Path(os.environ.get('CY_SETUP_PREVIEW','output/preview/computer-setup'))
    def capture(name):
        if not os.environ.get('CY_SETUP_PREVIEW'):return
        from PIL import ImageGrab
        folder.mkdir(parents=True,exist_ok=True);root.attributes('-topmost',True);root.update()
        ImageGrab.grab((root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(folder/name)
    def advance():
        try:
            ticks[0]+=1;assert ticks[0]<150,'Wizard test timed out'
            if stage[0]==0:
                capture('01-Server-Connection.png');wizard.username.set('Sample administrator');wizard.password.set('sample-only-password');wizard.connect_button.invoke();stage[0]=1
            elif stage[0]==1 and not wizard.busy:
                assert 'interrupted' in wizard.status.get();assert wizard.password.get()=='';assert not wizard.connect_button.instate(['disabled'])
                wizard.password.set('sample-only-password');wizard.connect_button.invoke();stage[0]=2
            elif stage[0]==2 and not wizard.busy:
                assert wizard.registration.winfo_ismapped();assert 'MAC: 02:AA:BB:CC:DD:10' in wizard.assignment.cget('text')
                wizard.register_button.invoke();assert client.registrations==0;assert 'Confirm' in wizard.status.get()
                capture('02-Existing-Computer-Match.png');wizard.reuse.set(True);wizard.register_button.invoke();stage[0]=3
            elif stage[0]==3 and not wizard.busy:
                assert wizard.complete and wizard.result==0 and client.registrations==1
                assert 'Registered:' in wizard.status.get();capture('03-Registration-Complete.png')
                wizard.register_button.invoke();return
            root.after(80,advance)
        except Exception:
            errors.append(traceback.format_exc());root.after_cancel(wizard.timer);root.destroy()
    root.after(120,advance)
    with patch('computer_setup.messagebox.askyesno',return_value=True):root.mainloop()
    assert not errors,errors
    print('PASS native wizard: connection retry, password clearing, existing MAC confirmation, one registration, completion and preview')


if __name__=='__main__':run()
