"""Embed supplied GIF and home-screen icons in server.py for legacy in-app updates."""
import base64,json,re
from pathlib import Path
def prepare(root=None):
 root=Path(root or Path(__file__).parent)
 assets=json.loads((root/'assets/home-icons.json').read_text(encoding='ascii'))
 assets['gif']=''.join(part.read_text(encoding='ascii') for part in sorted((root/'assets').glob('plug-*.b64')))
 if not base64.b64decode(assets['gif'],validate=True).startswith((b'GIF87a',b'GIF89a')):raise ValueError('Invalid supplied offline GIF')
 path=root/'server.py';source=path.read_text(encoding='utf-8')
 source,count=re.subn(r'^WEB_ASSETS=.* # prepared by prepare_web_assets.py$',lambda _: 'WEB_ASSETS='+repr(assets)+' # prepared by prepare_web_assets.py',source,flags=re.M)
 if count!=1:raise ValueError('Web asset marker missing')
 path.write_text(source,encoding='utf-8')
if __name__=='__main__':prepare()
