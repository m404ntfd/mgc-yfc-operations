// Compact OFFICE application information; no extra server requests.
if (officeMode) (() => {
 const webVersion = '__OFFICE_WEB_VERSION__'; // replaced by prepare_web_assets.py
 const style = document.createElement('style');
 style.textContent = `
 .retailOffice{--office-status-height:26px}
 .retailOffice .workspace{height:calc(100vh - var(--office-topbar-height,82px) - var(--office-status-height))}
 #officeStatusBar{box-sizing:border-box;position:fixed;inset:auto 0 0;z-index:100;height:var(--office-status-height);display:flex;align-items:center;gap:18px;padding:0 12px;background:var(--rt-surface,#edf2f7);color:var(--rt-text,#223248);border-top:1px solid var(--rt-border,#bccadb);font:12px/1.3 "Segoe UI",sans-serif;white-space:nowrap}
 #officeStatusBar .statusIdentity{overflow:hidden;text-overflow:ellipsis;min-width:40px;flex:1}
 #officeStatusBar .statusConnection::before{content:'';display:inline-block;width:7px;height:7px;border-radius:50%;background:#9a6700;margin-right:6px}
 #officeStatusBar[data-state=connected] .statusConnection::before{background:#18804b}
 #officeStatusBar[data-state=disconnected] .statusConnection::before{background:#c73838}
 #officeStatusBar time{font-variant-numeric:tabular-nums}
 @media(max-width:760px){.retailOffice{--office-status-height:48px;padding-bottom:48px}.retailOffice .workspace{height:auto}#officeStatusBar{display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;padding:4px 10px;font-size:11px}#officeStatusBar time{text-align:right}}
 @media print{#officeStatusBar{display:none!important}.retailOffice{padding-bottom:0}}
 `;
 document.head.append(style);
 const bar=document.createElement('footer');bar.id='officeStatusBar';bar.setAttribute('aria-label','Application information');
 bar.innerHTML='<span class="statusVersion"></span><span class="statusConnection" role="status"></span><span class="statusIdentity"></span><time></time>';
 document.body.append(bar);
 const version=bar.querySelector('.statusVersion'),connection=bar.querySelector('.statusConnection'),identity=bar.querySelector('.statusIdentity'),clock=bar.querySelector('time');
 version.textContent='OFFICE web '+webVersion;
 let nativeVersion='',readingNative=false;
 async function readNative(){
  const native=window.pywebview?.api;
  if(nativeVersion||readingNative||!native?.office_update_info)return;
  readingNative=true;
  try{const info=await native.office_update_info();if(!info.error&&info.version){nativeVersion=String(info.version);version.textContent='OFFICE '+nativeVersion+' | Web '+webVersion;version.title=version.textContent;}}catch{}finally{readingNative=false;}
 }
 function refresh(){
  const label=document.getElementById('connection')?.textContent||'Connecting…';
  const state=!navigator.onLine?'disconnected':label==='Connected to Operations'?'connected':label==='Connection interrupted'?'disconnected':'connecting';
  const text=state==='connected'?'Connected to Operations':state==='disconnected'?'Disconnected':'Connecting…';
  bar.dataset.state=state;if(connection.textContent!==text)connection.textContent=text;
  const name=user?.name?'Signed in: '+user.name:'Not signed in';
  if(identity.textContent!==name){identity.textContent=name;identity.title=name;}
  const now=new Date();clock.dateTime=now.toISOString();clock.textContent=now.toLocaleString(undefined,{year:'numeric',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',second:'2-digit'});clock.title=Intl.DateTimeFormat().resolvedOptions().timeZone;
 }
 const observer=new MutationObserver(refresh);
 const existing=document.getElementById('connection');if(existing)observer.observe(existing,{childList:true,subtree:true,characterData:true});
 window.addEventListener('offline',refresh);window.addEventListener('online',()=>{if(existing)existing.textContent='Connecting…';refresh();});
 window.addEventListener('pywebviewready',readNative);
 refresh();readNative();setInterval(refresh,1000);
})();
