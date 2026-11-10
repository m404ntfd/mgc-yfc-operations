"""Build the exact ZIP asset consumed by the in-app GitHub updater."""
from pathlib import Path
import zipfile
import updater
from release_payload import release_bytes
from prepare_web_assets import prepare
prepare()
root=Path(__file__).resolve().parent
updater.version(updater.current())
out=root/'dist';out.mkdir(exist_ok=True)
with zipfile.ZipFile(out/updater.ASSET,'w',zipfile.ZIP_DEFLATED) as z:
    for name in updater.FILES:z.writestr(name,release_bytes(root,name))
print(out/updater.ASSET)

installer=out/('MGC-YFC-Operations-Server-Windows-v'+updater.current()+'.zip')
names=[*updater.FILES,'Start-MGC-YFC-Operations-Server.bat','verify_dispatch_backup.py','DISPATCH-JOURNAL.md','unlock_local.py','LOGIN-SECURITY.md','launcher.py','Start-Store-Dispatch.bat','Start-Thrift-Mart-Dispatch-Server.bat','RELEASE-GUIDE.txt','build_release.py','test_server.py','test_updater.py','test_remote.py']
with zipfile.ZipFile(installer,'w',zipfile.ZIP_DEFLATED) as z:
    for name in names:z.write(root/name,'MGC-YFC-Operations-Server/'+name)
print(installer)
