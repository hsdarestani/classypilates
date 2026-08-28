(()=>{
  const $=(s,c=document)=>c.querySelector(s),$$=(s,c=document)=>[...c.querySelectorAll(s)];
  const upstreamFetch=window.fetch.bind(window);
  const languages=new Map();
  let editingClassId=null;

  const style=document.createElement('style');
  style.textContent=`
    .class-language-field small{display:block;margin-top:6px;color:#8b857b;font-size:10px;font-weight:500;letter-spacing:0;text-transform:none}
    .admin-class-language{display:inline-flex;align-items:center;width:max-content;margin-top:6px;padding:4px 7px;border:1px solid rgba(21,21,19,.13);border-radius:999px;background:#f3eee6;font:700 9px/1 Manrope,Arial,sans-serif;letter-spacing:.05em;color:#4d473f}
  `;
  document.head.appendChild(style);

  const normal=value=>String(value||'de').toLowerCase()==='en'?'en':'de';
  const badge=value=>normal(value)==='en'?'🇬🇧 EN':'🇩🇪 DE';

  function rememberClasses(data){
    (data?.classes||[]).forEach(row=>languages.set(Number(row.id),normal(row.language)));
  }

  window.fetch=async(input,opt={})=>{
    const url=typeof input==='string'?input:(input?.url||'');
    const method=String(opt.method||'GET').toUpperCase();
    let next=opt;

    if((url==='/api/staff/classes'||/^\/api\/staff\/classes\/\d+$/.test(url))&&(method==='POST'||method==='PATCH')&&typeof opt.body==='string'){
      try{
        const body=JSON.parse(opt.body);
        const field=method==='POST'?$('#cLanguage'):$('#ecLanguage');
        body.language=normal(field?.value||'de');
        next={...opt,body:JSON.stringify(body)};
      }catch(_){ }
    }

    const response=await upstreamFetch(input,next);
    if(url==='/api/staff/classes'&&method==='GET'&&response.ok){
      response.clone().json().then(data=>{rememberClasses(data);scheduleEnhance()}).catch(()=>{});
    }
    if((url==='/api/staff/classes'||/^\/api\/staff\/classes\/\d+$/.test(url))&&(method==='POST'||method==='PATCH')&&response.ok){
      response.clone().json().then(data=>{
        const row=data?.class||data;
        if(row?.id)languages.set(Number(row.id),normal(row.language));
      }).catch(()=>{});
    }
    return response;
  };

  function languageLabel(id,current='de'){
    const label=document.createElement('label');
    label.className='class-language-field';
    label.innerHTML=`LANGUAGE<select id="${id}"><option value="de">🇩🇪 DE</option><option value="en">🇬🇧 EN</option></select><small>Language used for this class</small>`;
    $('select',label).value=normal(current);
    return label;
  }

  function enhanceCreateForm(){
    const type=$('#cType');
    if(!type||$('#cLanguage'))return;
    const typeLabel=type.closest('label'),grid=typeLabel?.parentElement;
    if(!grid)return;
    typeLabel.insertAdjacentElement('afterend',languageLabel('cLanguage','de'));
  }

  function enhanceEditModal(){
    const type=$('#ecType');
    if(!type||$('#ecLanguage'))return;
    const typeLabel=type.closest('label');
    if(!typeLabel)return;
    const selected=languages.get(Number(editingClassId))||'de';
    typeLabel.insertAdjacentElement('afterend',languageLabel('ecLanguage',selected));
  }

  function annotateAdminRows(){
    $$('[data-edit-class]').forEach(button=>{
      const row=button.closest('.trow');
      const first=row?.querySelector('div');
      if(!first)return;
      const lang=languages.get(Number(button.dataset.editClass))||'de';
      let mark=first.querySelector('.admin-class-language');
      if(!mark){mark=document.createElement('span');mark.className='admin-class-language';first.appendChild(mark)}
      mark.textContent=badge(lang);
    });
  }

  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-edit-class]');
    if(button)editingClassId=Number(button.dataset.editClass);
  },true);

  let scheduled=false;
  function scheduleEnhance(){
    if(scheduled)return;
    scheduled=true;
    requestAnimationFrame(()=>{
      scheduled=false;
      enhanceCreateForm();
      enhanceEditModal();
      annotateAdminRows();
    });
  }
  new MutationObserver(scheduleEnhance).observe(document.body,{childList:true,subtree:true});
  scheduleEnhance();
})();
