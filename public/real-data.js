(()=>{
  const $=s=>document.querySelector(s);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const locale=()=>document.documentElement.lang==='de'?'de-DE':'en-GB';
  const count=value=>new Intl.NumberFormat(locale()).format(Number(value)||0);
  const day=value=>value?new Intl.DateTimeFormat(locale(),{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'Europe/Berlin'}).format(new Date(value)):'—';
  const initials=name=>String(name||'CP').split(/\s+/).map(part=>part[0]).join('').slice(0,2).toUpperCase();
  const api=async path=>{const response=await fetch(path,{headers:{accept:'application/json'},cache:'no-store'});if(!response.ok)throw new Error(path);return response.json()};

  const LOCAL_COACH_PHOTOS=[
    {match:name=>/^anna\s*k\b/.test(name),src:'/anna%20K.jpg'},
    {match:name=>/^sayna\b/.test(name),src:'/sayna.jpg'},
    {match:name=>/^luca\b/.test(name),src:'/luca.jpg'}
  ];
  const normalizeCoachName=value=>String(value||'').trim().toLowerCase().replace(/[.]+/g,'').replace(/\s+/g,' ');
  const coachPhotoUrl=coach=>{
    const name=normalizeCoachName(coach?.display_name);
    const local=LOCAL_COACH_PHOTOS.find(item=>item.match(name));
    return local?.src||String(coach?.photo_url||'').trim();
  };
  const cssUrl=value=>String(value||'').replace(/\\/g,'\\\\').replace(/"/g,'\\"');

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
    const photoUrl=coachPhotoUrl(coach);
    const avatar=photoUrl
      ?`<span class="coach-real-backdrop" aria-hidden="true"></span><img src="${esc(photoUrl)}" alt="Coach ${esc(coach.display_name)}" loading="lazy" decoding="async">`
      :`<span class="coach-real-initials">${esc(initials(coach.display_name))}</span>`;
    return `<article class="coach-real-card" data-coach-card><div class="coach-real-avatar" data-coach-photo-frame>${avatar}</div><div class="coach-real-copy"><p>CLASSY COACH</p><h3>${esc(coach.display_name)}</h3><span>${esc(studios)}</span><div><b>${count(coach.sessions)}</b><small>Sessions</small><b>${count(coach.bookings)}</b><small>Bookings</small></div></div></article>`;
  }

  function prepareCoachPhotoFrames(grid){
    grid.querySelectorAll('[data-coach-photo-frame]').forEach(frame=>{
      const image=frame.querySelector('img');
      const backdrop=frame.querySelector('.coach-real-backdrop');
      if(!image||!backdrop)return;
      const src=image.getAttribute('src')||image.src;
      if(src)backdrop.style.backgroundImage=`url("${cssUrl(src)}")`;
      image.addEventListener('error',()=>{
        frame.classList.add('coach-photo-error');
        frame.innerHTML=`<span class="coach-real-initials">${esc(initials(image.alt.replace(/^Coach\s+/i,'')))}</span>`;
      },{once:true});
    });
  }

  function renderCoaches(rows){
    const grid=$('#coachGrid'),button=$('#showAllCoaches');if(!grid)return;
    const sorted=[...rows].sort((a,b)=>b.sessions-a.sessions||a.display_name.localeCompare(b.display_name,'en'));
    grid.innerHTML=sorted.map(coachCard).join('')||'<div class="real-loading">No coach data found.</div>';
    prepareCoachPhotoFrames(grid);
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
