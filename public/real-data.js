(()=>{
  const $=s=>document.querySelector(s);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const locale=()=>document.documentElement.lang==='de'?'de-DE':'en-GB';
  const count=value=>new Intl.NumberFormat(locale()).format(Number(value)||0);
  const day=value=>value?new Intl.DateTimeFormat(locale(),{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'Europe/Berlin'}).format(new Date(value)):'—';
  const initials=name=>String(name||'CP').split(/\s+/).map(part=>part[0]).join('').slice(0,2).toUpperCase();
  const api=async path=>{const response=await fetch(path,{headers:{accept:'application/json'},cache:'no-store'});if(!response.ok)throw new Error(path);return response.json()};

  function renderOverview(data){
    const metrics=$('#realMetrics');
    if(metrics)metrics.innerHTML=[
      ['STUDIOS',data.studios],['COACHES',data.coaches],['SESSIONS',data.sessions],['BOOKINGS',data.bookings]
    ].map(([label,value])=>`<article><span>${label}</span><b>${count(value)}</b></article>`).join('');
    const range=$('#realDataRange');
    if(range)range.textContent=`Imported period: ${day(data.available_from)} to ${day(data.available_to)} · Source: ${data.source}.`;
  }

  function coachCard(coach){
    const studios=(coach.studios||[]).join(' · ')||'Classy Pilates Frankfurt';
    const avatar=coach.photo_url
      ?`<img src="${esc(coach.photo_url)}" alt="Coach ${esc(coach.display_name)}" loading="lazy">`
      :`<span>${esc(initials(coach.display_name))}</span>`;
    return `<article class="coach-real-card" data-coach-card><div class="coach-real-avatar">${avatar}</div><div class="coach-real-copy"><p>CLASSY COACH</p><h3>${esc(coach.display_name)}</h3><span>${esc(studios)}</span><div><b>${count(coach.sessions)}</b><small>Sessions</small><b>${count(coach.bookings)}</b><small>Bookings</small></div></div></article>`;
  }

  function renderCoaches(rows){
    const grid=$('#coachGrid'),button=$('#showAllCoaches');if(!grid)return;
    const sorted=[...rows].sort((a,b)=>b.sessions-a.sessions||a.display_name.localeCompare(b.display_name,'en'));
    grid.innerHTML=sorted.map(coachCard).join('')||'<div class="real-loading">No coach data found.</div>';
    const cards=[...grid.querySelectorAll('[data-coach-card]')];
    cards.slice(12).forEach(card=>card.hidden=true);
    if(button&&cards.length>12){button.hidden=false;button.addEventListener('click',()=>{const expanding=cards.some(card=>card.hidden);cards.forEach((card,index)=>card.hidden=!expanding&&index>=12);button.textContent=expanding?'Show less':'Show all coaches'})}
  }

  function renderCatalog(rows){
    const grid=$('#catalogGrid');if(!grid)return;
    const merged=new Map();
    rows.forEach(row=>{
      const current=merged.get(row.name)||{...row,studioNames:new Set(),sessions:0,bookings:0,coaches:0};
      current.studioNames.add(row.studio_name);current.sessions+=Number(row.sessions)||0;current.bookings+=Number(row.bookings)||0;current.coaches=Math.max(current.coaches,Number(row.coaches)||0);merged.set(row.name,current);
    });
    grid.innerHTML=[...merged.values()].map((row,index)=>`<article class="catalog-card"><div class="catalog-index">${String(index+1).padStart(2,'0')}</div><p>${esc(row.type)}</p><h3>${esc(row.name)}</h3><span>${esc([...row.studioNames].join(' · '))}</span><div class="catalog-facts"><b>${count(row.sessions)}<small>Sessions</small></b><b>${count(row.coaches)}<small>Coaches</small></b><b>${count(row.bookings)}<small>Bookings</small></b></div><a href="#schedule" data-real-class="${esc(row.type)}">Find in schedule →</a></article>`).join('')||'<div class="real-loading">No class data found.</div>';
    grid.querySelectorAll('[data-real-class]').forEach(link=>link.addEventListener('click',()=>{const type=link.dataset.realClass==='Mat Pilates'?'Mat':link.dataset.realClass;state.classType=type;const filter=$('#classFilter');if(filter)filter.value=type;renderSchedule()}));
  }

  async function load(){
    const [overview,coaches,classes]=await Promise.all([api('/api/public/overview'),api('/api/public/coaches'),api('/api/public/classes')]);
    renderOverview(overview);renderCoaches(coaches.coaches||[]);renderCatalog(classes.classes||[]);
  }
  load().catch(()=>{const range=$('#realDataRange');if(range)range.textContent='Live data could not be loaded.'});
})();
