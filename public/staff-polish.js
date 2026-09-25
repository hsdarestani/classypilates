(()=>{
  const $=(s,c=document)=>c.querySelector(s), $$=(s,c=document)=>[...c.querySelectorAll(s)];
  const token=()=>localStorage.getItem('cpStaffToken')||'';
  const locale=()=>document.documentElement.lang==='de'?'de-DE':'en-GB';
  const money=cents=>new Intl.NumberFormat(locale(),{style:'currency',currency:'EUR'}).format((Number(cents)||0)/100);
  const dt=value=>{try{return new Intl.DateTimeFormat(locale(),{dateStyle:'medium',timeStyle:'short'}).format(new Date(value))}catch(_){return value||'—'}};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const authFetch=async(path,opt={})=>{
    const headers={...(opt.headers||{})};if(token())headers.authorization=`Bearer ${token()}`;
    if(opt.body&&!(opt.body instanceof FormData)&&!headers['content-type'])headers['content-type']='application/json';
    const response=await fetch(path,{...opt,headers,credentials:'same-origin',cache:'no-store'});
    let data={};try{data=await response.json()}catch(_){}
    if(!response.ok)throw new Error(data.detail||data.error||'request_failed');
    return data;
  };

  const PHOTO_MAP=[
    [/^anna\s+k\b/i,'/anna%20K.jpg'],[/^anna$/i,'/anna.jpg'],[/^ouafaa\b/i,'/Ouafaa.jpeg'],
    [/^arja\b/i,'/Arja.jpeg'],[/^sophie\b/i,'/Sophie.jpg'],[/^schahrzad\b/i,'/Schahrzad.jpg'],
    [/^sani\b/i,'/Sani.jpg'],[/^sayna\b/i,'/sayna.jpg'],[/^luca\b/i,'/luca.jpg'],[/^zora\b/i,'/zora.jpg']
  ];
  const photoFor=name=>{const normalized=String(name||'').trim().replace(/[.]+/g,' ').replace(/\s+/g,' ');return PHOTO_MAP.find(([rx])=>rx.test(normalized))?.[1]||''};

  let studioData=null,studioLoading=null;
  function ensureStudioStyles(){
    if($('#studioManagerStyles'))return;
    const style=document.createElement('style');style.id='studioManagerStyles';style.textContent=`
      .studio-manager-intro{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:start;margin-bottom:24px;padding:18px 20px;border:1px solid #ded8cf;border-radius:16px;background:#f8f5ef}
      .studio-manager-intro b{display:block;margin-bottom:6px;font-size:13px}.studio-manager-intro p{margin:0;max-width:850px;color:#6e685f;font-size:12px;line-height:1.65}
      .studio-manager-badge{white-space:nowrap;border-radius:999px;padding:8px 11px;background:#171715;color:#fff;font-size:10px;font-weight:700;letter-spacing:.08em}
      .studio-editor-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
      .studio-editor-card{overflow:hidden;border:1px solid #ded8cf;border-radius:18px;background:#fff}
      .studio-editor-preview{height:190px;background:#ece7df;overflow:hidden}.studio-editor-preview img{width:100%;height:100%;object-fit:cover;display:block}.studio-editor-preview.empty{display:grid;place-items:center;color:#8b8379;font-size:12px}
      .studio-editor-body{padding:20px}.studio-editor-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:16px}.studio-editor-heading h3{margin:3px 0 0;font-family:'Playfair Display',serif;font-size:24px;font-weight:500}.studio-editor-heading small{display:block;color:#797269;font-size:10px;line-height:1.55;text-align:right}
      .studio-editor-fields{display:grid;grid-template-columns:1fr 1fr;gap:12px}.studio-editor-fields label{display:grid;gap:6px;color:#777066;font-size:9px;font-weight:700;letter-spacing:.08em}.studio-editor-fields label.full{grid-column:1/-1}.studio-editor-fields input,.studio-editor-fields textarea{width:100%;box-sizing:border-box;border:1px solid #ded8cf;border-radius:10px;background:#fbfaf8;padding:11px 12px;color:#171715;font:inherit;font-size:12px;letter-spacing:0}.studio-editor-fields textarea{resize:vertical;min-height:78px}
      .studio-editor-actions{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:16px}.studio-editor-actions small{color:#827b72;font-size:10px;line-height:1.45}.studio-editor-actions button{white-space:nowrap}
      @media(max-width:980px){.studio-editor-grid{grid-template-columns:1fr}}
      @media(max-width:620px){.studio-manager-intro{grid-template-columns:1fr}.studio-manager-badge{justify-self:start}.studio-editor-fields{grid-template-columns:1fr}.studio-editor-fields label.full{grid-column:auto}.studio-editor-preview{height:160px}.studio-editor-heading{display:block}.studio-editor-heading small{text-align:left;margin-top:6px}.studio-editor-actions{align-items:stretch;flex-direction:column}.studio-editor-actions button{width:100%}}
    `;document.head.appendChild(style);
  }

  function ensureStudioNav(){
    const nav=$('#nav');if(!nav||nav.querySelector('[data-studio-manager]'))return;
    const button=document.createElement('button');button.type='button';button.dataset.view='studios';button.dataset.studioManager='1';button.hidden=true;
    button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg><span>Studios</span>';
    const classes=nav.querySelector('[data-view="classes"]');classes?classes.after(button):nav.appendChild(button);
  }

  async function loadStudios(force=false){
    if(studioData&&!force)return studioData;
    if(studioLoading&&!force)return studioLoading;
    studioLoading=authFetch('/api/staff/studios').then(data=>{studioData=data;studioLoading=null;const nav=$('[data-studio-manager]');if(nav)nav.hidden=!data.can_edit;return data}).catch(error=>{studioLoading=null;throw error});
    return studioLoading;
  }

  function toast(text){const el=$('#toast');if(!el)return;el.textContent=text;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),2600)}

  function studioCard(studio){
    const image=studio.image_url?`<img src="${esc(studio.image_url)}" alt="${esc(studio.name)} studio" loading="lazy" onerror="this.parentElement.classList.add('empty');this.remove()">`:'Studio image';
    return `<article class="studio-editor-card" data-studio-card="${esc(studio.id)}">
      <div class="studio-editor-preview ${studio.image_url?'':'empty'}">${image}</div>
      <div class="studio-editor-body">
        <div class="studio-editor-heading"><div><span class="kicker">STUDIO</span><h3>${esc(studio.name)}</h3></div><small>Stable ID: ${esc(studio.id)}<br>Mindbody match: ${esc(studio.mindbody_location||'—')}</small></div>
        <div class="studio-editor-fields">
          <label>PUBLIC NAME<input data-studio-field="name" value="${esc(studio.name)}" maxlength="160"></label>
          <label>SHORT NAME<input data-studio-field="short_name" value="${esc(studio.short_name||'')}" maxlength="160"></label>
          <label class="full">ADDRESS<input data-studio-field="address" value="${esc(studio.address||'')}" maxlength="255"></label>
          <label>TRAINING / TYPE<input data-studio-field="public_type" value="${esc(studio.public_type||'')}" maxlength="160"></label>
          <label>DEFAULT CAPACITY<input data-studio-field="capacity" type="number" min="1" max="100" value="${Number(studio.capacity)||10}"></label>
          <label class="full">IMAGE URL<input data-studio-field="image_url" type="url" value="${esc(studio.image_url||'')}" maxlength="800" placeholder="https://..."></label>
          <label class="full">DESCRIPTION<textarea data-studio-field="description" maxlength="3000" placeholder="Optional public studio description">${esc(studio.description||'')}</textarea></label>
          <label>SORT ORDER<input data-studio-field="sort_order" type="number" min="0" max="10000" value="${Number(studio.sort_order)||0}"></label>
        </div>
        <div class="studio-editor-actions"><small>Website metadata updates immediately. Synced Mindbody classes keep their own class capacity.</small><button class="primary" type="button" data-studio-save>Save studio</button></div>
      </div>
    </article>`;
  }

  async function openStudioManager(){
    ensureStudioStyles();
    $$('#nav button').forEach(button=>button.classList.toggle('active',button.dataset.studioManager==='1'));
    document.querySelector('.sidebar')?.classList.remove('open');document.body.classList.remove('staff-menu-open');
    if($('#pageEyebrow'))$('#pageEyebrow').textContent='LOCATIONS';if($('#pageTitle'))$('#pageTitle').textContent='Studios';
    const view=$('#view');if(!view)return;view.innerHTML='<div class="panel"><div class="empty">Loading studios…</div></div>';
    try{
      const data=await loadStudios(true);
      if(!data.can_edit){view.innerHTML='<div class="panel"><div class="empty">You do not have permission to edit studio settings.</div></div>';return}
      view.innerHTML=`<section class="panel"><div class="panel-head"><div><p class="kicker">STUDIO SETTINGS</p><h2>Locations & website data</h2><p>Edit the information customers see across the Classy website and use the default capacity for newly created local sessions.</p></div></div><div class="studio-manager-intro"><div><b>Mindbody stays safely separated</b><p>${esc(data.mindbody_note||'Studio display settings are managed locally.')}</p></div><span class="studio-manager-badge">LOCAL PROFILE → WEBSITE</span></div><div class="studio-editor-grid">${(data.studios||[]).map(studioCard).join('')}</div></section>`;
      $$('[data-studio-save]',view).forEach(button=>button.addEventListener('click',async()=>{
        const card=button.closest('[data-studio-card]'),id=card?.dataset.studioCard;if(!card||!id)return;
        const field=name=>card.querySelector(`[data-studio-field="${name}"]`)?.value??'';
        const body={name:field('name').trim(),short_name:field('short_name').trim(),address:field('address').trim(),public_type:field('public_type').trim(),capacity:Number(field('capacity')),image_url:field('image_url').trim(),description:field('description').trim(),sort_order:Number(field('sort_order'))||0};
        if(!body.name||!Number.isInteger(body.capacity)||body.capacity<1||body.capacity>100){toast('Check studio name and capacity');return}
        const original=button.textContent;button.disabled=true;button.textContent='Saving…';
        try{await authFetch(`/api/staff/studios/${encodeURIComponent(id)}`,{method:'PATCH',body:JSON.stringify(body)});studioData=null;toast('Studio saved · website updated');await openStudioManager()}catch(error){toast(error.message);button.disabled=false;button.textContent=original}
      }));
    }catch(_){view.innerHTML='<div class="panel"><div class="empty">Studio settings could not be loaded.</div></div>'}
  }

  function syncClassStudioSelects(){
    const selects=[$('#cStudio'),$('#ecStudio')].filter(Boolean).filter(select=>select.dataset.liveStudios!=='1');if(!selects.length)return;
    loadStudios().then(data=>{
      const rows=data.studios||[];if(!rows.length)return;
      selects.forEach(select=>{
        if(select.dataset.liveStudios==='1')return;
        const current=select.value;select.innerHTML=rows.map(studio=>`<option value="${esc(studio.id)}">${esc(studio.name)}</option>`).join('');
        if(rows.some(studio=>studio.id===current))select.value=current;
        select.dataset.liveStudios='1';
        if(select.id==='cStudio'){
          const capacity=$('#cCapacity');const apply=()=>{const studio=rows.find(row=>row.id===select.value);if(studio&&capacity)capacity.value=String(studio.capacity)};
          apply();select.addEventListener('change',apply);
        }
      });
    }).catch(()=>{});
  }

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

  function tableFilterValue(row,index,label){
    const cell=row.children[index];if(!cell)return '';
    if(label==='STATUS')return (cell.querySelector('.status')?.textContent||cell.firstElementChild?.textContent||cell.textContent).trim();
    return (cell.querySelector('.source-badge,b')?.textContent||cell.firstElementChild?.textContent||cell.textContent).trim();
  }

  function inferredTableFilters(table,rows){
    const headers=$$('.trow.head > *',table).map(node=>node.textContent.trim().toUpperCase());
    const preferred=['SOURCE','STATUS','STUDIO','COACH','METHOD'];
    return preferred.map(label=>{
      const index=headers.findIndex(header=>header===label||header.startsWith(label+' ')||header.includes('/ '+label));
      if(index<0)return null;
      const values=[...new Set(rows.map(row=>tableFilterValue(row,index,label)).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
      if(values.length<2||values.length>30)return null;
      return {label,values,valueFor:row=>tableFilterValue(row,index,label)};
    }).filter(Boolean).slice(0,2);
  }

  function paginateCollection(root,items,{pageSizeDesktop=25,pageSizeMobile=12,searchPlaceholder='Search…',filters=[],minItems=8}={}){
    if(!root||root.dataset.paginated==='1')return;
    const rows=[...items];if(rows.length<minItems)return;
    root.dataset.paginated='1';
    const panel=root.closest('.panel')||root.parentElement;
    const tools=document.createElement('div');tools.className='collection-tools';
    tools.innerHTML=`<input class="collection-search" type="search" autocomplete="off" placeholder="${esc(searchPlaceholder)}"><span class="collection-count"></span>`;
    const count=tools.querySelector('.collection-count');
    filters.forEach((filter,index)=>{
      const select=document.createElement('select');select.className='collection-filter';select.dataset.filterIndex=String(index);
      select.setAttribute('aria-label',`Filter by ${filter.label.toLowerCase()}`);
      select.innerHTML=`<option value="">All ${esc(filter.label.toLowerCase())}</option>`+filter.values.map(value=>`<option value="${esc(value)}">${esc(value)}</option>`).join('');
      tools.insertBefore(select,count);
    });
    root.before(tools);
    const pager=document.createElement('div');pager.className='collection-pager';pager.innerHTML='<button type="button" data-prev aria-label="Previous page">←</button><span class="collection-page"></span><button type="button" data-next aria-label="Next page">→</button>';
    root.after(pager);
    let page=0,query='',filterValues=filters.map(()=>'');
    const render=()=>{
      const size=matchMedia('(max-width:760px)').matches?pageSizeMobile:pageSizeDesktop;
      const filtered=rows.filter(row=>{
        if(query&&!row.textContent.toLowerCase().includes(query))return false;
        return filters.every((filter,index)=>!filterValues[index]||filter.valueFor(row)===filterValues[index]);
      });
      const pages=Math.max(1,Math.ceil(filtered.length/size));page=Math.min(page,pages-1);
      const visible=new Set(filtered.slice(page*size,(page+1)*size));
      rows.forEach(row=>row.hidden=!visible.has(row));
      count.textContent=`${filtered.length} item${filtered.length===1?'':'s'}`;
      pager.querySelector('.collection-page').textContent=`${page+1} / ${pages}`;
      pager.querySelector('[data-prev]').disabled=page===0;
      pager.querySelector('[data-next]').disabled=page>=pages-1;
      pager.hidden=filtered.length<=size;
      if(panel)panel.dataset.visibleItems=String(visible.size);
    };
    tools.querySelector('.collection-search').addEventListener('input',event=>{query=event.target.value.trim().toLowerCase();page=0;render()});
    $$('.collection-filter',tools).forEach(select=>select.addEventListener('change',event=>{filterValues[Number(event.target.dataset.filterIndex)]=event.target.value;page=0;render()}));
    pager.querySelector('[data-prev]').addEventListener('click',()=>{if(page>0){page--;render();root.scrollIntoView({block:'start',behavior:'smooth'})}});
    pager.querySelector('[data-next]').addEventListener('click',()=>{page++;render();root.scrollIntoView({block:'start',behavior:'smooth'})});
    addEventListener('resize',()=>render(),{passive:true});render();
  }

  function enhanceTables(){
    $('.table').forEach(table=>{
      if(table.dataset.noCollection==='1'||table.classList.contains('schedule-managed-table')){labelTable(table);return;}
      labelTable(table);
      const panel=table.closest('.panel');
      const hasOwnSearch=Boolean(panel?.querySelector('.list-toolbar input[type="search"], .collection-tools'));
      if(hasOwnSearch)return;
      const rows=$$('.trow:not(.head)',table);
      paginateCollection(table,rows,{pageSizeDesktop:30,pageSizeMobile:10,searchPlaceholder:'Search this list…',filters:inferredTableFilters(table,rows),minItems:2});
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
    const cards=$$('.coach-admin-card',grid);
    const states=[...new Set(cards.map(card=>card.querySelector('.status')?.textContent.trim()).filter(Boolean))];
    const filters=states.length>1?[{label:'STATUS',values:states,valueFor:card=>card.querySelector('.status')?.textContent.trim()||''}]:[];
    paginateCollection(grid,cards,{pageSizeDesktop:12,pageSizeMobile:8,searchPlaceholder:'Search coaches…',filters,minItems:2});
  }

  function enhanceRoleLists(){
    $$('.panel').forEach(panel=>{
      const roleCards=$$('.role-card',panel);if(roleCards.length&&!panel.querySelector('.collection-tools')){
        const wrap=document.createElement('div');wrap.className='role-list-filterable';roleCards[0].before(wrap);roleCards.forEach(card=>wrap.appendChild(card));
        paginateCollection(wrap,roleCards,{pageSizeDesktop:20,pageSizeMobile:10,searchPlaceholder:'Search roles…',minItems:2});
      }
      const users=$$('.user-row',panel);if(users.length&&!panel.querySelector('.collection-tools')){
        const wrap=document.createElement('div');wrap.className='user-list-filterable';users[0].before(wrap);users.forEach(row=>wrap.appendChild(row));
        paginateCollection(wrap,users,{pageSizeDesktop:25,pageSizeMobile:10,searchPlaceholder:'Search team access…',minItems:2});
      }
    });
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
    const membership=$('#membershipPanel');if(membership){membership.hidden=true;membership.setAttribute('aria-hidden','true')}
  }

  document.addEventListener('click',event=>{
    const studioButton=event.target.closest('[data-studio-manager]');if(!studioButton)return;
    event.preventDefault();event.stopImmediatePropagation();openStudioManager();
  },true);

  let studioAccessChecked=false,queued=false;
  const run=()=>{
    if(queued)return;queued=true;
    requestAnimationFrame(()=>{
      queued=false;ensureStudioStyles();ensureStudioNav();ensureScrim();cleanupMembership();enhanceCoachRoster();enhanceTables();enhanceRoleLists();enhanceFinance();syncClassStudioSelects();
      if(!studioAccessChecked&&!$('#app')?.hidden){studioAccessChecked=true;loadStudios().catch(()=>{})}
    });
  };
  new MutationObserver(run).observe(document.body,{childList:true,subtree:true});
  run();
})();
