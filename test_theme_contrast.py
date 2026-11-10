"""Rendered foreground/background checks using isolated sample data."""
import os,json
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import password_login_page
AUDIT = r"""() => {
 const rgba=c=>(c.match(/[\d.]+/g)||[]).map(Number);
 const over=(a,b)=>{let t=a.length>3?a[3]:1;return a.slice(0,3).map((v,i)=>v*t+b[i]*(1-t))};
 const lum=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
 const background=e=>{let chain=[];for(let p=e;p;p=p.parentElement)chain.unshift(p);return chain.reduce((c,p)=>over(rgba(getComputedStyle(p).backgroundColor),c),[255,255,255]);};
 let issues=[];
 for(const e of document.querySelectorAll('button,summary,input,select,textarea,label,p,h1,h2,h3,strong,small,span,a,th,td')){
  if(!e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})||e.disabled||e.closest('[hidden]'))continue;
  let text=[...e.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim();if(e.matches('input,textarea,select'))text=e.value||e.placeholder;if(!text)continue;
  let s=getComputedStyle(e),bg=background(e),fg=over(rgba(s.color),bg),a=lum(fg),b=lum(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05),limit=parseFloat(s.fontSize)>=24||(parseFloat(s.fontSize)>=18.66&&parseInt(s.fontWeight)>=700)?3:4.5;
  if(ratio<limit)issues.push({tag:e.tagName,id:e.id,cls:e.className,text:text.slice(0,55),ratio:+ratio.toFixed(2),fg:s.color,bg:bg.map(Math.round)});
 }
 return issues;
}"""
def run():
 f=CoordinatorFixture();out=Path('output/preview/theme-audit');out.mkdir(parents=True,exist_ok=True);results=[]
 code,result=f.call('pos/catalog-options-save',dict(request='d'*32,revision=0,categories=['Clothing'],printing=[],taxes=[]));assert code==200,result
 code,result=f.call('pos/product',dict(request='e'*32,name='Sample shirt',price=599,category='Clothing',taxable=True));assert code==200,result
 themes=['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+c for c in ['blue','teal','violet','rose','graphite']]
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}))
   for app,width in [('ops',1366),('ops',390),('office',1366),('pos',1366)]:
    context=browser.new_context(viewport={'width':width,'height':950},bypass_csp=True);p=context.new_page();p.goto(f'http://127.0.0.1:{f.port}/'+('' if app=='ops' else app))
    if app!='ops':password_login_page(p)
    p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
    if app=='ops':
     p.locator('#sectionChooser').wait_for();p.evaluate("document.querySelector('#sectionChooser').close();storeSection('print')");p.locator('#profileWelcomeSkip').click();p.locator('.headerMenu summary').click()
    elif app=='office':p.locator('#officeTiles').wait_for()
    else:p.locator('#posPanel').wait_for()
    states = [('home','')]
    if app=='ops':states += [('views',"document.querySelector('.headerMenu').open=false;document.querySelector('#storeMenuButton').click()"),('settings',"document.querySelector('#storeMenu').hidden=true;tab('settings')"),('time',"workOpen(false,'clock');document.querySelectorAll('.workDropdown').forEach(e=>e.open=true)"),('communications',"commOpen()")]
    if app=='office':states += [('catalog',"officeAction('catalog')"),('users',"officeAction('users')")]
    if app=='pos':states += [('manual',"document.querySelectorAll('details').forEach(e=>{if(e.textContent.includes('Manual item'))e.open=true})")]
    for state,script in states:
     if script:
      p.evaluate("document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
      p.evaluate(script);p.wait_for_timeout(400)
     for theme in (['default']+themes[5:] if app=='ops' else themes):
      for mode in ['light','dark']:
       p.evaluate('([theme,mode])=>{document.body.dataset.retailTheme=theme;document.documentElement.dataset.theme=mode}',[theme,mode]);p.wait_for_timeout(80)
       issues=p.evaluate(AUDIT);results.append(dict(app=app,width=width,state=state,theme=theme,mode=mode,issues=issues))
       if app=='ops' and state=='home':
        assert p.locator('.headerMenu>div').evaluate('(e)=>{const r=e.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth}'), 'Menu clipped outside viewport'
        target=p.locator('.headerMenu>div button:visible').first;target.hover();target.focus()
        results.append(dict(app=app,width=width,state='menu-hover-focus',theme=theme,mode=mode,issues=p.evaluate(AUDIT)))
        target.evaluate('(e)=>e.blur()');p.mouse.move(0,0)
       if theme=='glass-graphite' and mode=='dark':p.screenshot(path=str(out/(app+'-'+str(width)+'-'+state+'-glass-dark.png')))
    context.close()
   browser.close()
 finally:f.close()
 (out/'contrast-results.json').write_text(json.dumps(results,indent=2))
 bad=[r for r in results if r['issues']];print(json.dumps(bad[:5],indent=2));print(f"{len(results)} combinations; {len(bad)} with contrast findings")
 assert not bad, f'Contrast failures in {len(bad)} rendered theme combinations; see {out}/contrast-results.json'
 return results
if __name__=='__main__':run()

