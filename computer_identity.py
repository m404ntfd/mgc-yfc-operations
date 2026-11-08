"""Computer identity for inventory; never used as an authentication credential."""
import hashlib,platform,uuid

def computer_info():
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
            'hostname':platform.node()[:120],'macs':macs,'os':platform.platform()[:160]}
