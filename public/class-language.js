(()=>{
  const languageByClass=new Map();
  const upstreamFetch=window.fetch.bind(window);
  const ACTIVE_KEY='cpActiveClassLanguage';
  const normalize=value=>String(value||'de').toLowerCase()==='en'?'en':'de';
  const flag=value=>normalize(value)==='en'?'🇬🇧':'🇩🇪';

  const style=document.createElement('style');
  style.textContent=`
    .class-name{position:relative;padding-right:82px}
    .class-name .class-language{position:absolute;right:0;top:50%;transform:translateY(-50%);display:inline-flex;align-items:center;gap:6px;min-width:58px;width:max-content;padding:6px 9px;margin:0;border:1px solid rgba(21,21,19,.14);border-radius:999px;background:#f4f0e8;color:#454139;font:700 9px/1 Manrope,Arial,sans-serif;letter-spacing:.08em;white-space:nowrap;z-index:2}
    .class-name .class-language .class-language-flag{display:inline;margin:0;color:inherit;font-size:15px;line-height:1;letter-spacing:0}
    .class-name .class-language .class-language-code{display:inline;margin:0;color:inherit;font:700 9px/1 Manrope,Arial,sans-serif;letter-spacing:.08em}
    @media(max-width:760px){.class-name{padding-right:0}.class-name .class-language{position:static;transform:none;margin-top:8px;padding:5px 8px}.class-name .class-language .class-language-flag{font-size:13px}}
  `;
  document.head.appendChild(style);

  function remember(data){
    (data?.classes||[]).forEach(row=>{
      if(row?.id!=null)languageByClass.set(String(row.id),normalize(row.language));
    });
    decorate();
  }

  window.fetch=async(input,opt={})=>{
    const url=typeof input==='string'?input:(input?.url||'');
    const response=await upstreamFetch(input,opt);
    if(url.startsWith('/api/schedule')&&response.ok){
      response.clone().json().then(remember).catch(()=>{});
    }
    return response;
  };

  function decorate(){
    document.querySelectorAll('#classList .class-row').forEach(row=>{
      const button=row.querySelector('[data-reserve]');
      const name=row.querySelector('.class-name');
      if(!button||!name)return;
      const language=languageByClass.get(String(button.dataset.reserve))||'de';
      let badge=name.querySelector('.class-language');
      if(!badge){
        badge=document.createElement('span');
        badge.className='class-language';
        name.appendChild(badge);
      }
      if(badge.dataset.language===language)return;
      badge.dataset.language=language;
      badge.setAttribute('aria-label',language==='en'?'Class language English':'Kurssprache Deutsch');
      badge.title=language==='en'?'Class language: English':'Kurssprache: Deutsch';
      badge.innerHTML=`<span class="class-language-flag">${flag(language)}</span><span class="class-language-code">${language.toUpperCase()}</span>`;
    });
  }

  document.addEventListener('click',event=>{
    const button=event.target.closest?.('[data-reserve]');
    if(!button)return;
    const language=languageByClass.get(String(button.dataset.reserve))||'de';
    try{sessionStorage.setItem(ACTIVE_KEY,language)}catch(_){}
  },true);

  function berlinIsoDate(date){
    const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date).map(p=>[p.type,p.value]));
    return `${parts.year}-${parts.month}-${parts.day}`;
  }

  async function seed(){
    const start=new Date(),end=new Date(start.getTime()+44*86400000);
    try{
      const response=await upstreamFetch(`/api/schedule?from=${encodeURIComponent(berlinIsoDate(start))}&to=${encodeURIComponent(berlinIsoDate(end))}`,{headers:{accept:'application/json'},cache:'no-store'});
      if(response.ok)remember(await response.json());
      else decorate();
    }catch(_){decorate()}
  }

  const list=document.querySelector('#classList');
  if(list)new MutationObserver(decorate).observe(list,{childList:true});
  seed();
  decorate();
})();
