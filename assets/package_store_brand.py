from pathlib import Path
import base64,io,json,os
from playwright.sync_api import sync_playwright
root=Path(__file__).parent
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ['TEST_CHROMIUM'])
 page=b.new_page(viewport={'width':512,'height':512},device_scale_factor=1)
 for name in ('desk','office','store-ops'):
  if name=='store-ops':svg=(root/'store-ops.svg').read_text()
  else:
   data=base64.b64encode((root/(name+'.png')).read_bytes()).decode()
   svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><clipPath id="tile"><rect x="2" y="2" width="508" height="506" rx="106"/></clipPath></defs><image width="512" height="512" href="data:image/png;base64,{data}" clip-path="url(#tile)"/></svg>'
  page.set_content('<style>html,body{margin:0;background:transparent}svg{width:512px;height:512px}</style>'+svg)
  page.screenshot(path=str(root/(name+'.png')),omit_background=True)
 b.close()
