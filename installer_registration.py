"""Administrator-authorized setup connection; no access to a business database on disk."""
import copy
import http.cookiejar
import json
import os
import secrets
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPCookieProcessor, ProxyHandler

from computer_identity import computer_info,active_connection
from desktop_connection import NoRedirect, USER_AGENT, probe_server, server_url
from pos_kiosk import KioskStore

APP_FOLDERS={'pos':'MGCYFCPOS','office':'CoastYouthRetailOffice','ops':'CoastYouthRetailStoreOps'}

class SetupRequestError(ValueError):
    def __init__(self,message,status=None):super().__init__(message);self.status=status


def read_json(path):
    if not path.exists():return {}
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict):raise ValueError()
        return data
    except (ValueError,OSError):raise ValueError('Existing connection settings cannot be read. They have not been replaced. Contact your administrator.') from None


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.setup.tmp')
    with temp.open('w',encoding='utf-8') as out:
        json.dump(data,out);out.flush();os.fsync(out.fileno())
    os.replace(temp,path)


class SetupRegistration:
    def __init__(self,apps,versions,appdata=None,identity=None):
        if len(set(apps))!=len(apps) or any(a not in APP_FOLDERS for a in apps):raise ValueError('Invalid application selection.')
        self.apps=list(apps);self.versions=versions
        self.root=Path(appdata or os.environ.get('APPDATA',str(Path.home())))
        self.identity=identity or computer_info();self.discover_network=identity is None
        self.opener=None;self.address=None;self.details=None;self.app_info=[];self.pending=None;self.created_settings={};self.adoptions={}
        self.connection_id=secrets.token_hex(16);self.handles=[]

    def claim_clients(self):
        if not getattr(sys,'frozen',False) or os.name!='nt':return
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p];kernel.CreateMutexW.restype=ctypes.c_void_p
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        for app in self.apps:
            name='Local\\MGCYFCPOS' if app=='pos' else 'Local\\CoastYouthStartup-'+app
            handle=kernel.CreateMutexW(None,False,name);error=ctypes.get_last_error()
            if handle:self.handles.append(handle)
            if not handle or error==183:
                for held in self.handles:kernel.CloseHandle(held)
                self.handles=[]
                raise ValueError('Finish or save your work and close DESK, OFFICE and STORE OPS on this PC, then retry setup registration.')

    def requires_exit_code(self):
        if 'pos' not in self.apps:return False
        current=KioskStore(self.settings_path('pos'));old=current.data.get('server')
        return bool(old and current.configured and server_url(old)!=self.address)

    def settings_path(self,app):return self.root/APP_FOLDERS[app]/'settings.json'
    def connection_path(self,app):return self.root/APP_FOLDERS[app]/('connection.json' if app=='ops' else 'settings.json')

    def saved_addresses(self):
        return {a:read_json(self.connection_path(a)).get('server','') for a in self.apps}

    def call(self,path,data=None):
        request=Request(self.address+'/api/'+path,data=json.dumps(data).encode() if data is not None else None,
                        headers={'Content-Type':'application/json','X-Dispatch':'1','X-Dispatch-Connection':self.connection_id,'User-Agent':USER_AGENT})
        try:
            with self.opener.open(request,timeout=15) as response:raw=response.read(1000001)
            if len(raw)>1000000:raise ValueError('The server returned too much information. Contact your administrator.')
            return json.loads(raw)
        except HTTPError as error:
            try:message=json.loads(error.read(128000)).get('error','The server refused this request.')
            except (ValueError,UnicodeError):message='The server refused this request.'
            error.close()
            if 300<=error.code<400:message='The server redirected this request. Enter its final HTTPS address. Credentials were not forwarded.'
            elif error.code==404 and path.startswith('computers/setup-'):message='Update the Operations server to a version that supports installer registration, then retry.'
            raise SetupRequestError(message,error.code) from None
        except (URLError,OSError):raise SetupRequestError('The server connection was interrupted. Check the network or VPN and retry. Existing data is kept.') from None

    def connect(self,address,username,password):
        if self.pending:raise ValueError('Retry the pending registration before changing its connection.')
        self.close()
        self.claim_clients()
        try:candidate=probe_server(address,'pos' if 'pos' in self.apps else 'office')
        except Exception:self.close();raise
        if self.discover_network:self.identity={**computer_info(),**active_connection(candidate)}
        self.address=candidate
        self.cookies=http.cookiejar.CookieJar()
        self.opener=build_opener(ProxyHandler({}),NoRedirect(),HTTPCookieProcessor(self.cookies))
        try:
            self.call('login',{'name':username,'password':password})
            user=self.call('session').get('user')
            if not user or not user.get('admin'):raise ValueError('Sign in with an Operations administrator account to register this computer.')
            self.app_info=[];self.adoptions={}
            for app in self.apps:
                path=self.settings_path(app);fresh=not path.exists();store=KioskStore(path)
                if fresh:self.created_settings[app]=store.data['device']
                self.app_info.append({'app':app,'device':store.data['device'],'version':self.versions[app]})
            self.details=self.call('computers/setup-preview',{'computer':self.identity,'apps':self.app_info})
            # Reinstallations without local settings can reuse a unique existing app identity.
            # Existing settings/device IDs are never replaced. Adoption happens only on Register.
            for app in self.app_info:
                known=[a for a in self.details.get('installed_apps',[]) if a['app']==app['app']]
                if len(known)==1 and self.created_settings.get(app['app'])==app['device'] and app['device']!=known[0]['device']:
                    self.adoptions[app['app']]=(app['device'],known[0]['device']);app['device']=known[0]['device']
            if self.adoptions:self.details=self.call('computers/setup-preview',{'computer':self.identity,'apps':self.app_info})
            return self.details
        except Exception:
            self.close();raise

    def register(self,name,role,store_id='',terminal='',restore=False,exit_code='',reuse=False):
        if not self.details:raise ValueError('Check the connection and sign in as an administrator first.')
        if not self.pending:
            if self.details.get('matched_by_mac') and not reuse:raise ValueError('Confirm the matching computer before reusing its registration.')
            # Protect the existing DESK server choice, just as the normal connection editor does.
            if 'pos' in self.apps:
                current=KioskStore(self.settings_path('pos'))
                old=current.data.get('server')
                if old and server_url(old)!=self.address and current.configured and not current.verify(exit_code):
                    raise ValueError('Enter the existing DESK admin exit passcode to change its server address.')
            payload={'computer':self.identity,'apps':self.app_info,'revision':self.details['computer']['revision'],
                     'name':name.strip(),'role':role,'store_id':store_id,'terminal':terminal,'request':secrets.token_hex(16)}
            if self.details.get('removed_terminal') and restore:
                previous=self.details['terminal'];payload.update(restore_terminal=previous['id'],terminal_revision=previous['revision'],confirm_restore=True)
            if self.details.get('matched_by_mac') and reuse:payload.update(reuse_computer=self.details['computer']['id'],confirm_reuse=True)
            for app,(generated,original) in self.adoptions.items():
                path=self.settings_path(app);data=read_json(path)
                if data=={'device':generated}:write_json(path,{'device':original})
                elif data.get('device')!=original:raise ValueError('New local settings changed during setup. Close the applications and reopen setup; no existing identity was replaced.')
            self.pending=copy.deepcopy(payload)
        try:result=self.call('computers/setup-register',self.pending)
        except SetupRequestError as error:
            if error.status in (400,401,403,404,409,422,503):self.pending=None
            raise
        # Preserve passcodes, printers, device IDs and all unknown settings keys.
        # A failed disk save can be retried against the same server receipt.
        for app in self.app_info:
            path=self.settings_path(app['app']);current=KioskStore(path)
            if current.data['device']!=app['device']:raise ValueError('The local device identity changed. Close other applications and reopen setup; no identity was replaced.')
            target=self.connection_path(app['app']);data=read_json(target);data['server']=self.address
            try:write_json(target,data)
            except OSError:raise ValueError('The server registered this PC, but a local connection setting could not be saved. Close the applications and retry to finish saving the same registration.') from None
        self.details=result;self.pending=None
        return result

    def close(self):
        if self.opener and self.address:
            try:self.call('logout',{})
            except Exception:pass
        if hasattr(self,'cookies'):self.cookies.clear()
        if self.handles:
            import ctypes
            kernel=ctypes.WinDLL('kernel32');kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            for handle in self.handles:kernel.CloseHandle(handle)
            self.handles=[]
        self.opener=None;self.details=None
