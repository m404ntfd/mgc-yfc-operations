"""Computer identity for inventory; never used as an authentication credential."""
import hashlib,platform,uuid
_network_cache={}

def cached_connection(address):
    import time
    if not address:return {}
    now=time.monotonic();previous=_network_cache.get(address)
    if previous and now-previous[0]<60:return previous[1]
    value=active_connection(address);_network_cache[address]=(now,value)
    return value

def active_connection(address):
    """Resolve the adapter for a connection to this server, not the first NIC on the PC."""
    import ipaddress,json,os,re,socket,subprocess
    from urllib.parse import urlsplit
    if platform.system()!='Windows' or not address:return {}
    try:
        parts=urlsplit(address)
        with socket.create_connection((parts.hostname,parts.port or (443 if parts.scheme=='https' else 80)),timeout=4) as connection:
            local=connection.getsockname()[0]
        ip=ipaddress.ip_address(local.split('%')[0])
        if ip.is_loopback:return {'local_address':local,'active_adapter':'Local server (loopback)'}
        # Values are supplied through the environment; no server/user text is executed.
        script="$ErrorActionPreference='Stop'; $entry=Get-NetIPAddress -IPAddress $env:CY_SETUP_LOCAL_IP | Select-Object -First 1; $adapter=Get-NetAdapter -InterfaceIndex $entry.InterfaceIndex -IncludeHidden; @{mac=$adapter.MacAddress;name=$adapter.Name} | ConvertTo-Json -Compress"
        command=[os.path.join(os.environ.get('SystemRoot',r'C:\Windows'),'System32','WindowsPowerShell','v1.0','powershell.exe'),'-NoProfile','-NonInteractive','-Command',script]
        result=subprocess.run(command,capture_output=True,text=True,timeout=8,env={**os.environ,'CY_SETUP_LOCAL_IP':str(ip)},creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:return {'local_address':local}
        adapter=json.loads(result.stdout);mac=str(adapter.get('mac','')).replace('-',':').upper()
        if not re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}',mac) or mac=='00:00:00:00:00:00' or int(mac[:2],16)&1:return {'local_address':local}
        return {'active_mac':mac,'active_adapter':str(adapter.get('name',''))[:120],'local_address':local}
    except (OSError,ValueError,subprocess.SubprocessError):return {}

def computer_info(address=None):
    identity=''
    if platform.system()=='Windows':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography',0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
                identity=str(winreg.QueryValueEx(key,'MachineGuid')[0])
        except OSError:pass
    # Unsupported hosts do not invent a machine identity or merge on a MAC address.
    node=uuid.getnode()
    macs=[] if (node>>40)&1 else [':'.join(f'{node:012X}'[i:i+2] for i in range(0,12,2))]
    return {'id':hashlib.sha256(('CoastYouthRetail:computer:'+identity).encode()).hexdigest()[:32] if identity else '',
            'hostname':platform.node()[:120],'macs':macs,'os':platform.platform()[:160],**cached_connection(address)}
