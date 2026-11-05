"""HTTP client for MGC YFC Operations Remote Manager; credentials stay in memory."""
import http.cookiejar,json,urllib.request,urllib.error,urllib.parse

def normalize_address(value):
    value=value.strip()
    if '://' not in value:value='http://'+value
    p=urllib.parse.urlsplit(value)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.path not in ('','/') or p.query or p.fragment:
        raise ValueError('Enter only a server name or IP address, such as 192.168.1.50:8080.')
    try: port=p.port
    except ValueError:raise ValueError('Enter a valid port number.')
    if port is not None and not 1<=port<=65535:raise ValueError('Enter a valid port number.')
    host='['+p.hostname+']' if ':' in p.hostname else p.hostname
    return f'{p.scheme}://{host}:{port or (8080 if p.scheme=="http" else 443)}'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class Client:
    def __init__(self,address,local_control=None,session_path=None):
        self.address=normalize_address(address)
        if local_control and urllib.parse.urlsplit(self.address).hostname not in ('localhost','127.0.0.1','::1'):raise ValueError('Local sign-in requires the server computer.')
        self.local_control=local_control;self.session_path=session_path;self.session_token=None
        self.cookies=http.cookiejar.CookieJar()
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPCookieProcessor(self.cookies))
    def request(self,path,data=None):
        headers={'X-Dispatch':'1','X-Dispatch-Activity':'1','Content-Type':'application/json'}
        if self.local_control:headers['X-Local-Control']=self.local_control
        if self.session_token:headers['Cookie']='session='+self.session_token
        req=urllib.request.Request(self.address+'/api/'+path,data=None if data is None else json.dumps(data).encode(),headers=headers)
        try:
            with self.opener.open(req,timeout=60 if path=='update-install' else 30) as r:return json.loads(r.read(1024*1024))
        except urllib.error.HTTPError as e:
            try:
                error=json.loads(e.read());message=error.get('error','Request failed.')
                if isinstance(error.get('attempts_remaining'),int):message+='\nAttempts Remaining Until Account Lock: '+str(error['attempts_remaining'])
            except Exception:message='Server refused the request.'
            raise ValueError(message) from e
        except (urllib.error.URLError,TimeoutError,OSError) as e:raise ValueError('Cannot reach the server. Check its address, power, staff network, and Windows Firewall.') from e
    def probe(self):
        r=self.request('session')
        if r.get('application')!='thrift-mart-dispatch':raise ValueError('This is not a compatible MGC YFC Operations Server. Install server version 0.3.0 or newer.')
        return r
    def login(self,name,password):
        self.session_token=None
        payload={'name':name,'password':password}
        if self.local_control:payload.update(local_admin=True,local_control_token=self.local_control)
        self.probe();self.request('login',payload)
        s=self.request('session')
        if not s.get('user',{}).get('admin'):
            self.request('logout',{})
            raise ValueError('Remote management requires an administrator account. Employees can use Open schedule in browser.')
        result=self.request('admin/status')
        if self.local_control and self.session_path:
            from native_auth import save_token
            token=next(cookie.value for cookie in self.cookies if cookie.name=='session')
            save_token(self.session_path,token)
        return result

    def restore_local_session(self):
        if not self.local_control or not self.session_path:return None
        from native_auth import load_token
        self.session_token=load_token(self.session_path)
        if not self.session_token:return None
        session=self.probe()
        if session.get('user') and session['user'].get('admin'):return self.request('admin/status')
        self.session_token=None
        from pathlib import Path
        Path(self.session_path).unlink(missing_ok=True)
        return None
