const officeBeforeComputers=officeAction;
officeAction=async function(action){
 if(!['computer-register','computer-updates'].includes(action))return officeBeforeComputers(action);
 if(!navigationAllowed()||unfinished())return;
 const registration=action==='computer-register',dialog=flowModal(registration?'Registered computers':'Installed application versions','<p>Registration stays with the computer when its address changes. Applications check for updates on startup and hourly; restart an application to install an available update.</p><button id="computerRefresh" type="button">Refresh computers</button><p id="computerStatus" role="status"></p><div id="computerRows"></div>');
 dialog.classList.add('computerDialog');let busy=false;
 function render(data){
  dialog.querySelector('#computerStatus').textContent=`${data.computers.filter(p=>p.registered).length} registered computers · Server ${data.server_version}`;
  dialog.querySelector('#computerRows').innerHTML=data.computers.map(pc=>`<article class="computerCard"><h3>${esc(pc.name||pc.hostname)}</h3><p>${esc(pc.hostname)} · ${esc(pc.role)} · ${pc.registered?'Registered':'Awaiting registration'}</p>${registration?`<form data-register-computer="${pc.id}" data-revision="${pc.revision}"><label>Name<input name="name" maxlength="80" required value="${esc(pc.name||pc.hostname)}"></label><label>Role<select name="role">${[['pos','POS checkout'],['office','Office computer'],['server','Server computer'],['other','Other']].map(([v,t])=>`<option value="${v}" ${pc.role===v?'selected':''}>${t}</option>`).join('')}</select></label><button>Save registration</button></form>`:''}<div class="computerApps">${pc.apps.map(a=>`<div><strong>${a.app==='pos'?'DESK':a.app==='ops'?'STORE OPS desktop':'OFFICE'} · ${esc(a.version)}</strong><span>${a.online?'Connected':'Offline / closed'}</span><small>Last seen ${esc(new Date(a.seen*1000).toLocaleString())} · ${esc(a.ip)}</small></div>`).join('')}</div></article>`).join('')||'<p>No computers registered yet.</p>';
 }
 async function refresh(){if(busy||!dialog.open||[...changedForms.keys()].some(f=>dialog.contains(f)))return;busy=true;try{render(await api('computers/state'));}catch(e){dialog.querySelector('#computerStatus').textContent=e.message;}finally{busy=false;}}
 dialog.querySelector('#computerRefresh').onclick=refresh;
 dialog.querySelector('#computerRows').onsubmit=async e=>{e.preventDefault();if(busy)return;const f=e.target;busy=true;try{const data=await api('computers/register',{id:f.dataset.registerComputer,revision:Number(f.dataset.revision),name:f.elements.name.value,role:f.elements.role.value});changedForms.delete(f);render(data);}catch(error){dialog.querySelector('#computerStatus').textContent=error.message;}finally{busy=false;}};
 const timer=setInterval(refresh,15000);dialog.addEventListener('close',()=>clearInterval(timer),{once:true});await refresh();
};
