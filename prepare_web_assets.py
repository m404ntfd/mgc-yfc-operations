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
  content=re.sub(r'// BEGIN FULFILLMENT PRINT.*?// END FULFILLMENT PRINT',lambda _: '// BEGIN FULFILLMENT PRINT\n'+(root/'static/fulfillment-print.js').read_text(encoding='utf-8')+'\n// END FULFILLMENT PRINT',content,flags=re.S)
  if filename=='pos.js':content=re.sub(r'// BEGIN PICKUP FOLLOWUP.*?// END PICKUP FOLLOWUP',lambda _: '// BEGIN PICKUP FOLLOWUP\n'+(root/'static/pickup-followup.js').read_text(encoding='utf-8')+'\n// END PICKUP FOLLOWUP',content,flags=re.S)
  if filename=='app.js':content=re.sub(r'// BEGIN DELIVERY WORKSPACE.*?// END DELIVERY WORKSPACE',lambda _: '// BEGIN DELIVERY WORKSPACE\n'+(root/'static/delivery-workspace.js').read_text(encoding='utf-8')+'\n// END DELIVERY WORKSPACE',content,flags=re.S)
  if filename=='app.js':content=re.sub(r'// BEGIN OFFICE SECURITY.*?// END OFFICE SECURITY',lambda _: '// BEGIN OFFICE SECURITY\n'+(root/'static/office-security.js').read_text(encoding='utf-8')+'\n// END OFFICE SECURITY',content,flags=re.S)
  content=re.sub(r'// BEGIN REPORT CENTER.*?// END REPORT CENTER',lambda _: '// BEGIN REPORT CENTER\n'+(root/'static/report-center.js').read_text(encoding='utf-8')+'\n// END REPORT CENTER',content,flags=re.S)
  if filename=='pos.js':content=re.sub(r'// BEGIN STORE UI.*?// END STORE UI',lambda _: '// BEGIN STORE UI\n'+(root/'static/retail-stores.js').read_text(encoding='utf-8')+'\n// END STORE UI',content,flags=re.S)
  if filename=='pos.js':content=re.sub(r'// BEGIN THRIFT UI.*?// END THRIFT UI',lambda _: '// BEGIN THRIFT UI\n'+(root/'static/thrift-retail.js').read_text(encoding='utf-8')+'\n// END THRIFT UI',content,flags=re.S)
  if filename=='pos.js':content=re.sub(r'// BEGIN OFFICE EXPANSION.*?// END OFFICE EXPANSION',lambda _: '// BEGIN OFFICE EXPANSION\n'+(root/'static/office-expansion.js').read_text(encoding='utf-8')+'\n// END OFFICE EXPANSION',content,flags=re.S)
  if filename=='pos.js':content=re.sub(r'// BEGIN CATALOG EDITOR.*?// END CATALOG EDITOR',lambda _: '// BEGIN CATALOG EDITOR\n'+(root/'static/catalog-editor.js').read_text(encoding='utf-8')+'\n// END CATALOG EDITOR',content,flags=re.S)
  if filename=='pos.js':content=re.sub(r'\n*// BEGIN CASH ADVANCES.*?// END CASH ADVANCES\n*','\n',content,flags=re.S).rstrip()+'\n// BEGIN CASH ADVANCES\n'+(root/'static/cash-advances.js').read_text(encoding='utf-8')+'\n// END CASH ADVANCES\n'
  if filename=='pos.js':content=re.sub(r'\n*// BEGIN OFFICE UPDATES.*?// END OFFICE UPDATES\n*','\n',content,flags=re.S).rstrip()+'\n// BEGIN OFFICE UPDATES\n'+(root/'static/office-updates.js').read_text(encoding='utf-8')+'\n// END OFFICE UPDATES\n'
  if filename=='pos.js':content=re.sub(r'\n*// BEGIN GIVING UI.*?// END GIVING UI\n*','\n',content,flags=re.S).rstrip()+'\n// BEGIN GIVING UI\n'+(root/'static/giving-office.js').read_text(encoding='utf-8')+'\n// END GIVING UI\n'
  if filename=='pos.js':content=re.sub(r'\n*// BEGIN OFFICE STATUS BAR.*?// END OFFICE STATUS BAR\n*','\n',content,flags=re.S).rstrip()+'\n// BEGIN OFFICE STATUS BAR\n'+(root/'static/office-status.js').read_text(encoding='utf-8').replace('__OFFICE_WEB_VERSION__',(root/'VERSION').read_text(encoding='utf-8').strip())+'\n// END OFFICE STATUS BAR\n'
  if filename=='pos.js':content=re.sub(r'\n*// BEGIN OFFICE NAVIGATION.*?// END OFFICE NAVIGATION\n*','\n',content,flags=re.S).rstrip()+'\n// BEGIN OFFICE NAVIGATION\n'+(root/'static/office-navigation.js').read_text(encoding='utf-8')+'\n// END OFFICE NAVIGATION\n'
  if filename=='pos.js':content=re.sub(r'\n*// BEGIN OFFICE SEARCH.*?// END OFFICE SEARCH\n*','\n',content,flags=re.S).rstrip()+'\n// BEGIN OFFICE SEARCH\n'+(root/'static/office-search.js').read_text(encoding='utf-8')+'\n// END OFFICE SEARCH\n'
  if filename=='pos.js':content=re.sub(r'\n*// BEGIN DESK TOUCH.*?// END DESK TOUCH\n*','\n',content,flags=re.S).rstrip()+'\n// BEGIN DESK TOUCH\n'+(root/'static/desk-touch.js').read_text(encoding='utf-8-sig')+'\n// END DESK TOUCH\n'
  content=re.sub(r'// BEGIN TERMINAL REGISTRATION.*?// END TERMINAL REGISTRATION','',content,flags=re.S).rstrip()+'\n// BEGIN TERMINAL REGISTRATION\n'+(root/'static/terminal-registration.js').read_text(encoding='utf-8')+'\n// END TERMINAL REGISTRATION\n'
  file.write_text(content,encoding='utf-8')
 for name in ('pos.css','style.css'):
  css=root/'static'/name;content=css.read_text(encoding='utf-8-sig');content=re.sub(r'\n*/\* BEGIN GLASS THEME \*/.*?/\* END GLASS THEME \*/\n*','\n',content,flags=re.S);css.write_text(content.rstrip()+'\n/* BEGIN GLASS THEME */\n'+(root/'static/glass-theme.css').read_text(encoding='utf-8')+'\n/* END GLASS THEME */\n',encoding='utf-8')
  css=root/'static'/name;content=css.read_text(encoding='utf-8-sig');content=re.sub(r'\n*/\* BEGIN TERMINAL REGISTRATION \*/.*?/\* END TERMINAL REGISTRATION \*/\n*','\n',content,flags=re.S);css.write_text(content.rstrip()+'\n/* BEGIN TERMINAL REGISTRATION */\n'+(root/'static/terminal-registration.css').read_text()+'\n/* END TERMINAL REGISTRATION */\n',encoding='utf-8')
  css=root/'static'/name;content=css.read_text(encoding='utf-8-sig');content=re.sub(r'\n*/\* BEGIN REPORT DOCUMENT \*/.*?/\* END REPORT DOCUMENT \*/\n*','\n',content,flags=re.S);css.write_text(content.rstrip()+'\n/* BEGIN REPORT DOCUMENT */\n'+(root/'static/report-document.css').read_text(encoding='utf-8')+'\n/* END REPORT DOCUMENT */\n',encoding='utf-8')
 css=root/'static/pos.css';content=css.read_text(encoding='utf-8');content=re.sub(r'\n*/\* BEGIN OFFICE NAVIGATION \*/.*?/\* END OFFICE NAVIGATION \*/\n*','\n',content,flags=re.S);css.write_text(content.rstrip()+'\n/* BEGIN OFFICE NAVIGATION */\n'+(root/'static/office-navigation.css').read_text(encoding='utf-8')+'\n/* END OFFICE NAVIGATION */\n',encoding='utf-8')
 css=root/'static/pos.css';content=css.read_text(encoding='utf-8');content=re.sub(r'\n*/\* BEGIN DESK TOUCH \*/.*?/\* END DESK TOUCH \*/\n*','\n',content,flags=re.S);css.write_text(content.rstrip()+'\n/* BEGIN DESK TOUCH */\n'+(root/'static/desk-touch.css').read_text(encoding='utf-8-sig')+'\n/* END DESK TOUCH */\n',encoding='utf-8')
 hr=root/'static/hr.js';content=hr.read_text(encoding='utf-8');content=re.sub(r'// BEGIN HR BROWSER UI.*?// END HR BROWSER UI',lambda _: '// BEGIN HR BROWSER UI\n'+(root/'static/hr-browser.js').read_text(encoding='utf-8')+'\n// END HR BROWSER UI',content,flags=re.S);hr.write_text(content,encoding='utf-8')
 pos={name:(root/'static'/name).read_text(encoding='utf-8') for name in ('pos.html','pos.js','pos.css','customer-display.html','customer-display.js','customer-display.css','hr.html','hr.js','hr.css')}
 source,count=re.subn(r'^POS_ASSETS=.* # prepared POS application assets$',lambda _: 'POS_ASSETS='+repr(pos)+' # prepared POS application assets',source,flags=re.M)
 if count!=1:raise ValueError('POS asset marker missing')
 source=re.sub(r'# BEGIN RETAIL FULFILLMENT.*?# END RETAIL FULFILLMENT',lambda _: '# BEGIN RETAIL FULFILLMENT\n'+(root/'retail_fulfillment.py').read_text(encoding='utf-8')+'\n# END RETAIL FULFILLMENT',source,flags=re.S)
 source=re.sub(r'# BEGIN RETAIL STORES.*?# END RETAIL STORES',lambda _: '# BEGIN RETAIL STORES\n'+(root/'retail_stores.py').read_text(encoding='utf-8')+'\n# END RETAIL STORES',source,flags=re.S)
 source=re.sub(r'# BEGIN THRIFT RETAIL.*?# END THRIFT RETAIL',lambda _: '# BEGIN THRIFT RETAIL\n'+(root/'thrift_retail.py').read_text(encoding='utf-8')+'\n# END THRIFT RETAIL',source,flags=re.S)
 source=re.sub(r'# BEGIN CUSTOMER SERVICES.*?# END CUSTOMER SERVICES',lambda _: '# BEGIN CUSTOMER SERVICES\n'+(root/'customer_services.py').read_text(encoding='utf-8')+'\n# END CUSTOMER SERVICES',source,flags=re.S)
 source=re.sub(r'# BEGIN RETAIL REPORTS.*?# END RETAIL REPORTS',lambda _: '# BEGIN RETAIL REPORTS\n'+(root/'retail_reports.py').read_text(encoding='utf-8')+'\n# END RETAIL REPORTS',source,flags=re.S)
 source=re.sub(r'# BEGIN COMPUTER REGISTRY.*?# END COMPUTER REGISTRY',lambda _: '# BEGIN COMPUTER REGISTRY\n'+(root/'computer_registry.py').read_text(encoding='utf-8-sig')+'\n# END COMPUTER REGISTRY',source,flags=re.S)
 source=re.sub(r'# BEGIN CATALOG SETUP.*?# END CATALOG SETUP',lambda _: '# BEGIN CATALOG SETUP\n'+(root/'catalog_setup.py').read_text(encoding='utf-8')+'\n# END CATALOG SETUP',source,flags=re.S)
 source=re.sub(r'# BEGIN HR ONBOARDING.*?# END HR ONBOARDING',lambda _: '# BEGIN HR ONBOARDING\n'+(root/'hr_onboarding.py').read_text(encoding='utf-8')+'\n# END HR ONBOARDING',source,flags=re.S)
 source=re.sub(r'^HR_REFERENCE_FORMS=.* # prepared HR reference forms$',lambda _: 'HR_REFERENCE_FORMS='+repr([item for item in json.loads((root/'assets/hr-reference-forms.json').read_text(encoding='utf-8')) if item['kind']=='deposit'])+' # prepared HR reference forms',source,flags=re.M)
 source=re.sub(r'# BEGIN HR BROWSER.*?# END HR BROWSER',lambda _: '# BEGIN HR BROWSER\n'+(root/'hr_browser.py').read_text(encoding='utf-8')+'\n# END HR BROWSER',source,flags=re.S)
 source=re.sub(r'^HR_SOURCE_FORMS=.* # prepared HR source forms$',lambda _: 'HR_SOURCE_FORMS='+repr(json.loads((root/'assets/hr-source-forms.json').read_text(encoding='utf-8')))+' # prepared HR source forms',source,flags=re.M)
 source=re.sub(r'# BEGIN GIVING.*?# END GIVING',lambda _: '# BEGIN GIVING\n'+(root/'giving.py').read_text(encoding='utf-8')+'\n# END GIVING',source,flags=re.S)
 path.write_text(source,encoding='utf-8')
if __name__=='__main__':prepare()
