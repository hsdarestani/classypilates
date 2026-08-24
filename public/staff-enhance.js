(()=>{
  const token=()=>localStorage.getItem('cpStaffToken')||'';
  const api=async(path,opt={})=>{const h={...(opt.headers||{}),authorization:`Bearer ${token()}`};if(!(opt.body instanceof FormData))h['content-type']='application/json';const r=await fetch(path,{...opt,headers:h});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||'Fehler');return d};
  const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  let cache=[];
  function modal(c){
    document.querySelector('.class-edit-modal')?.remove();
    const w=document.createElement('div');w.className='class-edit-modal';w.style.cssText='position:fixed;inset:0;z-index:100;background:rgba(0,0,0,.58);display:grid;place-items:center;padding:16px';
    const local=new Date(c.starts_at);const value=new Date(local.getTime()-local.getTimezoneOffset()*60000).toISOString().slice(0,16);
    w.innerHTML=`<div class="panel" style="width:min(650px,100%);margin:0"><div class="panel-head"><div><p class="kicker">EDIT CLASS</p><h2>Klasse bearbeiten</h2><p>${esc(c.studio_name)}</p></div><button class="secondary" data-close>×</button></div><div class="form-grid"><label>KLASSE<input data-title value="${esc(c.name)}"></label><label>TYP<select data-type><option ${c.type==='Reformer'?'selected':''}>Reformer</option><option ${c.type==='Powerformer'?'selected':''}>Powerformer</option><option ${c.type==='Mat'?'selected':''}>Mat</option><option ${c.type==='Barre'?'selected':''}>Barre</option></select></label><label>START<input data-start type="datetime-local" value="${value}"></label><label>DAUER<input data-duration type="number" value="${c.duration}"></label><label>KAPAZITÄT<input data-capacity type="number" value="${c.capacity}"></label></div><button class="primary" data-save>Änderungen speichern</button><div class="msg" data-msg></div></div>`;
    document.body.appendChild(w);w.querySelector('[data-close]').onclick=()=>w.remove();w.querySelector('[data-save]').onclick=async()=>{try{await api(`/api/staff/classes/${c.id}`,{method:'PATCH',body:JSON.stringify({studio_id:c.studio,title:w.querySelector('[data-title]').value,class_type:w.querySelector('[data-type]').value,coach_id:c.coach_id||null,starts_at:new Date(w.querySelector('[data-start]').value).toISOString(),duration:Number(w.querySelector('[data-duration]').value),capacity:Number(w.querySelector('[data-capacity]').value)})});w.remove();location.reload()}catch(e){w.querySelector('[data-msg]').textContent=e.message}};
  }
  async function enhance(){
    const buttons=[...document.querySelectorAll('[data-delete-class]')];if(!buttons.length)return;
    try{cache=(await api('/api/staff/classes')).classes}catch(_){return}
    buttons.forEach(del=>{if(del.parentElement.querySelector('[data-edit-class]'))return;const id=Number(del.dataset.deleteClass),c=cache.find(x=>x.id===id);if(!c)return;const b=document.createElement('button');b.className='secondary';b.dataset.editClass=id;b.textContent='Bearbeiten';b.onclick=()=>modal(c);del.parentElement.insertBefore(b,del)});
  }
  new MutationObserver(()=>setTimeout(enhance,20)).observe(document.body,{childList:true,subtree:true});setTimeout(enhance,800);
})();
