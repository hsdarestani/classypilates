(()=>{
  const $=(s,c=document)=>c.querySelector(s), $$=(s,c=document)=>[...c.querySelectorAll(s)];
  const token=()=>localStorage.getItem('cpStaffToken')||'';
  const locale=()=>document.documentElement.lang==='de'?'de-DE':'en-GB';
  const money=cents=>new Intl.NumberFormat(locale(),{style:'currency',currency:'EUR'}).format((Number(cents)||0)/100);
  const dt=value=>{try{return new Intl.DateTimeFormat(locale(),{dateStyle:'medium',timeStyle:'short'}).format(new Date(value))}catch(_){return value||'—'}};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const authFetch=async(path)=>{
    const headers={};if(token())headers.authorization=`Bearer ${token()}`;
    const response=await fetch(path,{headers,credentials:'same-origin',cache:'no-store'});
    if(!response.ok)throw new Error('request_failed');
    return response.json();
  };

  const PHOTO_MAP=[
    [/^anna\s+k\b/i,'/anna%20K.jpg'],[/^anna$/i,'/anna.jpg'],[/^ouafaa\b/i,'/Ouafaa.jpeg'],
    [/^arja\b/i,'/Arja.jpeg'],[/^sophie\b/i,'/Sophie.jpg'],[/^schahrzad\b/i,'/Schahrzad.jpg'],
    [/^sani\b/i,'/Sani.jpg'],[/^sayna\b/i,'/sayna.jpg'],[/^luca\b/i,'/luca.jpg'],[/^zora\b/i,'/zora.jpg']
  ];
  const photoFor=name=>{const normalized=String(name||'').trim().replace(/[.]+/g,' ').replace(/\s+/g,' ');return PHOTO_MAP.find(([rx])=>rx.test(normalized))?.[1]||''};

  function ensureScrim(){
    if($('.staff-nav-scrim'))return;
    const scrim=document.createElement('div');scrim.className='staff-nav-scrim';scrim.setAttribute('aria-hidden','true');
    document.body.appendChild(scrim);
    const close=()=>{document.querySelector('.sidebar')?.classList.remove('open');document.body.classList.remove('staff-menu-open')};
    scrim.addEventListener('click',close);
    document.addEventListener('keydown',event=>{if(event.key==='Escape')close()});
    document.querySelector('#mobileNav')?.addEventListener('click',()=>requestAnimationFrame(()=>document.body.classList.toggle('staff-menu-open',document.querySelector('.sidebar')?.classList.contains('open'))));
    document.querySelector('#nav')?.addEventListener('click',event=>{if(event.target.closest('button'))close()});
  }

  function labelTable(table){
    if(!table||table.dataset.mobileLabels==='1')return;
    const headers=$$('.trow.head > *',table).map(node=>node.textContent.trim()).filter(Boolean);
    if(!headers.length)return;
    $$('.trow:not(.head)',table).forEach(row=>{
      [...row.children].forEach((cell,index)=>cell.dataset.label=headers[index]||'');
    });
    table.dataset.mobileLabels='1';
  }

  function paginateCollection(root,items,{pageSizeDesktop=25,pageSizeMobile=12,searchPlaceholder='Search…'}={}){
    if(!root||root.dataset.paginated==='1')return;
    const rows=[...items];if(rows.length<10)return;
    root.dataset.paginated='1';
    const panel=root.closest('.panel')||root.parentElement;
    const tools=document.createElement('div');tools.className='collection-tools';
    tools.innerHTML=`<input class="collection-search" type="search" autocomplete="off" placeholder="${esc(searchPlaceholder)}"><span class="collection-count"></span>`;
    root.before(tools);
    const pager=document.createElement('div');pager.className='collection-pager';pager.innerHTML='<button type="button" data-prev aria-label="Previous page">←</button><span class="collection-page"></span><button type="button" data-next aria-label="Next page">→</button>';
    root.after(pager);
    let page=0,query='';
    const render=()=>{
      const size=matchMedia('(max-width:760px)').matches?pageSizeMobile:pageSizeDesktop;
      const filtered=rows.filter(row=>!query||row.textContent.toLowerCase().includes(query));
      const pages=Math.max(1,Math.ceil(filtered.length/size));page=Math.min(page,pages-1);
      const visible=new Set(filtered.slice(page*size,(page+1)*size));
      rows.forEach(row=>row.hidden=!visible.has(row));
      tools.querySelector('.collection-count').textContent=`${filtered.length} item${filtered.length===1?'':'s'}`;
      pager.querySelector('.collection-page').textContent=`${page+1} / ${pages}`;
      pager.querySelector('[data-prev]').disabled=page===0;
      pager.querySelector('[data-next]').disabled=page>=pages-1;
      pager.hidden=filtered.length<=size;
      if(panel)panel.dataset.visibleItems=String(visible.size);
    };
    tools.querySelector('input').addEventListener('input',event=>{query=event.target.value.trim().toLowerCase();page=0;render()});
    pager.querySelector('[data-prev]').addEventListener('click',()=>{if(page>0){page--;render();root.scrollIntoView({block:'start',behavior:'smooth'})}});
    pager.querySelector('[data-next]').addEventListener('click',()=>{page++;render();root.scrollIntoView({block:'start',behavior:'smooth'})});
    addEventListener('resize',()=>render(),{passive:true});render();
  }

  function enhanceTables(){
    $$('.table').forEach(table=>{
      labelTable(table);
      paginateCollection(table,$$('.trow:not(.head)',table),{pageSizeDesktop:30,pageSizeMobile:10,searchPlaceholder:'Search this list…'});
    });
  }

  function enhanceCoachRoster(){
    const grid=$('.coach-roster-grid');if(!grid)return;
    $$('.coach-admin-card',grid).forEach(card=>{
      if(card.dataset.photoChecked==='1')return;card.dataset.photoChecked='1';
      const holder=card.querySelector('.coach-photo');if(!holder||holder.querySelector('img'))return;
      const name=card.querySelector('.coach-card-title h3')?.textContent||'';const src=photoFor(name);if(!src)return;
      const image=document.createElement('img');image.src=src;image.alt=`Coach ${name}`;image.loading='lazy';image.decoding='async';
      holder.appendChild(image);
    });
    paginateCollection(grid,$$('.coach-admin-card',grid),{pageSizeDesktop:12,pageSizeMobile:8,searchPlaceholder:'Search coaches…'});
  }

  async function enhanceFinance(){
    const heading=$('#pageTitle');if(!heading||heading.textContent.trim()!=='Finance')return;
    const view=$('#view');if(!view||view.dataset.sumupEnhanced==='1')return;
    view.dataset.sumupEnhanced='loading';
    try{
      const data=await authFetch('/api/staff/finance');
      if($('#pageTitle')?.textContent.trim()!=='Finance')return;
      const metrics=$$('.metric',view);
      if(metrics[2]){const label=metrics[2].querySelector('span');if(label)label.textContent='PAID TRANSACTIONS'}
      if(metrics[3]){
        const label=metrics[3].querySelector('span'),value=metrics[3].querySelector('b'),small=metrics[3].querySelector('small');
        if(label)label.textContent='SUMUP';
        if(value)value.textContent=data.sumup_configured?'Connected':'Needs setup';
        if(small)small.textContent=data.sumup_configured?'Hosted Checkout · production':'SumUp credentials are not configured';
      }
      const firstPanel=$('.panel',view);
      if(firstPanel&&!view.querySelector('.sumup-finance-strip')){
        const strip=document.createElement('section');strip.className='sumup-finance-strip';
        strip.innerHTML=`<div><span>Payment provider</span><b>SumUp Hosted Checkout</b><small>${data.sumup_configured?'Live production connection':'Connection requires attention'}</small><span class="sumup-provider-pill">${data.sumup_configured?'● LIVE':'○ SETUP'}</span></div><div><span>SumUp paid</span><b>${money(data.sumup_paid_cents)}</b><small>${Number(data.sumup_paid_orders)||0} paid order${Number(data.sumup_paid_orders)===1?'':'s'}</small></div><div><span>SumUp pending</span><b>${money(data.sumup_pending_cents)}</b><small>${Number(data.sumup_pending_orders)||0} awaiting completion</small></div><div><span>All paid revenue</span><b>${money(data.revenue_cents)}</b><small>Bookings + credits + on-site sales</small></div>`;
        firstPanel.before(strip);
      }
      view.dataset.sumupEnhanced='1';
    }catch(_){view.dataset.sumupEnhanced='error'}
  }

  function cleanupMembership(){
    // staff-feedback.js still knows the historical SEPA experiment. It is not a
    // production product; keep it inaccessible even if that enhancer executes.
    const membership=$('#membershipPanel');if(membership){membership.hidden=true;membership.setAttribute('aria-hidden','true')}
  }

  let queued=false;
  const run=()=>{
    if(queued)return;queued=true;
    requestAnimationFrame(()=>{
      queued=false;ensureScrim();cleanupMembership();enhanceCoachRoster();enhanceTables();enhanceFinance();
    });
  };
  new MutationObserver(run).observe(document.body,{childList:true,subtree:true});
  run();
})();
