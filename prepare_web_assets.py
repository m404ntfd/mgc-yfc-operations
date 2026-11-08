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
 js=root/'static/pos.js';text=js.read_text(encoding='utf-8');text=re.sub(r'// BEGIN CUSTOMER OFFICE.*?// END CUSTOMER OFFICE',lambda _: '// BEGIN CUSTOMER OFFICE\n'+(root/'static/customer-office.js').read_text(encoding='utf-8')+'\n// END CUSTOMER OFFICE',text,flags=re.S);js.write_text(text,encoding='utf-8')
 for filename in ('app.js','pos.js'):
  file=root/'static'/filename;content=file.read_text(encoding='utf-8')
  content=re.sub(r'// BEGIN REPORT CENTER.*?// END REPORT CENTER',lambda _: '// BEGIN REPORT CENTER\n'+(root/'static/report-center.js').read_text(encoding='utf-8')+'\n// END REPORT CENTER',content,flags=re.S)
  if filename=='pos.js':content=re.sub(r'// BEGIN OFFICE EXPANSION.*?// END OFFICE EXPANSION',lambda _: '// BEGIN OFFICE EXPANSION\n'+(root/'static/office-expansion.js').read_text(encoding='utf-8')+'\n// END OFFICE EXPANSION',content,flags=re.S)
  file.write_text(content,encoding='utf-8')
 pos={name:(root/'static'/name).read_text(encoding='utf-8') for name in ('pos.html','pos.js','pos.css','customer-display.html','customer-display.js','customer-display.css')}
 source,count=re.subn(r'^POS_ASSETS=.* # prepared POS application assets$',lambda _: 'POS_ASSETS='+repr(pos)+' # prepared POS application assets',source,flags=re.M)
 if count!=1:raise ValueError('POS asset marker missing')
 source=re.sub(r'# BEGIN CUSTOMER SERVICES.*?# END CUSTOMER SERVICES',lambda _: '# BEGIN CUSTOMER SERVICES\n'+(root/'customer_services.py').read_text(encoding='utf-8')+'\n# END CUSTOMER SERVICES',source,flags=re.S)
 source=re.sub(r'# BEGIN RETAIL REPORTS.*?# END RETAIL REPORTS',lambda _: '# BEGIN RETAIL REPORTS\n'+(root/'retail_reports.py').read_text(encoding='utf-8')+'\n# END RETAIL REPORTS',source,flags=re.S)
 path.write_text(source,encoding='utf-8')
if __name__=='__main__':prepare()
