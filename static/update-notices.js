// Notices never close a form, freeze a register, or launch an installer.
(()=>{
 const warning=document.createElement('aside'),notice=document.createElement('aside');
 const style=document.createElement('style');style.textContent='@media screen and (min-width:761px){body.retailOffice .workspace{height:calc(100dvh - var(--office-topbar-height,82px) - var(--office-status-height,26px) - var(--desktop-notice-height,0px))}}@media print{#serverMaintenanceBanner,#desktopVersionNotice{display:none!important}}';document.head.append(style);
 warning.id='serverMaintenanceBanner';notice.id='desktopVersionNotice';
 for(const b of [warning,notice]){b.hidden=true;b.setAttribute('role','status');b.style.cssText='position:relative;z-index:1000;padding:12px 18px;background:#fff1c2;color:#312600;border:2px solid #a75e00;font:600 16px/1.4 system-ui;flex-shrink:0';document.body.prepend(b);}
 warning.textContent='YFC OPERATIONS SERVER UPDATES & RESTARTS AT 4:00AM. SAVE ALL WORK AND EXIT APPLICATIONS UNTIL 04:05. APPLICATIONS WILL BE OFFLINE DURING THIS TIME';
 const resize=new ResizeObserver(()=>document.body.style.setProperty('--desktop-notice-height',(warning.getBoundingClientRect().height+notice.getBoundingClientRect().height)+'px'));resize.observe(warning);resize.observe(notice);
 let offset=0,last=0,busy=false;
 function clock(){const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(Date.now()+offset));const minutes=Number(parts.find(p=>p.type==='hour').value)*60+Number(parts.find(p=>p.type==='minute').value);warning.hidden=minutes<230||minutes>241;}
 async function check(){if(busy)return;busy=true;try{
  const native=window.pywebview?.api;if(native?.desktop_update_status){const status=await native.desktop_update_status();notice.hidden=!status.available;notice.textContent=status.message||'';}
  if(Date.now()-last>300000){last=Date.now();const response=await fetch('/api/maintenance',{cache:'no-store'});if(response.ok){const data=await response.json();offset=Date.parse(data.time)-Date.now();}}
 }catch{/* Keep the last notice and clock during a network interruption. */}finally{busy=false;clock();}}
 window.addEventListener('pywebviewready',check);check();setInterval(check,60000);setInterval(clock,1000);
})();
