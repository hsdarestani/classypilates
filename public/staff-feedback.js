(()=>{
  const originalFetch=window.fetch.bind(window);
  const moneyEuros=cents=>`${(Number(cents||0)/100).toFixed(2).replace('.',',')} €`;
  const knownPrices={1:2800,5:11900,10:21900,20:39900};
  const token=()=>localStorage.getItem('cpStaffToken')||'';
  const authFetch=(path,opt={})=>originalFetch(path,{...opt,headers:{'content-type':'application/json',authorization:`Bearer ${token()}`,...(opt.headers||{})},credentials:'same-origin',cache:'no-store'});

  window.fetch=async(input,opt={})=>{
    const url=typeof input==='string'?input:(input?.url||'');
    const method=String(opt.method||'GET').toUpperCase();
    let next=opt;
    if((url==='/api/staff/classes'||/^\/api\/staff\/classes\/\d+$/.test(url))&&(method==='POST'||method==='PATCH')&&typeof opt.body==='string'){
      try{
        const body=JSON.parse(opt.body);
        if(Object.prototype.hasOwnProperty.call(body,'repeat_weeks')){
          body.repeat_months=Number(body.repeat_weeks)||1;
          delete body.repeat_weeks;
          next={...opt,body:JSON.stringify(body)};
        }
      }catch(_){ }
    }
    if(url==='/api/staff/class-passes/sell'&&method==='POST'&&typeof opt.body==='string'){
      try{
        const body=JSON.parse(opt.body);
        const credits=Number(document.querySelector('#passCredits')?.value||10);
        const rawPrice=document.querySelector('#passAmount')?.value;
        const amount=Math.round(Number(String(rawPrice||'').replace(',','.'))*100);
        body.credits=credits;
        if(Number.isFinite(amount)&&amount>=0)body.amount_cents=amount;
        next={...opt,body:JSON.stringify(body)};
      }catch(_){ }
    }
    return originalFetch(input,next);
  };

  function enhancePassSale(){
    const panel=document.querySelector('.pass-sale-panel');
    const grid=panel?.querySelector('.pass-sale-grid');
    if(!grid||grid.dataset.feedbackEnhanced)return;
    grid.dataset.feedbackEnhanced='1';
    const summary=grid.querySelector('.pass-summary');
    const packageLabel=document.createElement('label');
    packageLabel.innerHTML='CLASS CREDITS<select id="passCredits"><option>1</option><option>5</option><option selected>10</option><option>20</option><option>30</option><option>50</option></select>';
    const priceLabel=document.createElement('label');
    priceLabel.innerHTML='PRICE (€)<input id="passAmount" type="number" min="0" step="0.01" value="219.00">';
    if(summary){grid.insertBefore(packageLabel,summary);grid.insertBefore(priceLabel,summary)}else{grid.append(packageLabel,priceLabel)}
    const credits=document.querySelector('#passCredits'),price=document.querySelector('#passAmount');
    const update=()=>{
      const count=Number(credits.value||10),known=knownPrices[count];
      if(known!=null)price.value=(known/100).toFixed(2);else if(credits.dataset.last!==String(count))price.value='';
      credits.dataset.last=String(count);
      if(summary){summary.querySelector('span').textContent=`${count} CLASS CREDIT${count===1?'':'S'}`;summary.querySelector('b').textContent=`${price.value?price.value.replace('.',',')+' € · ':''}${count} booking${count===1?'':'s'}`;summary.querySelector('small').textContent='Valid across all Classy studios.'}
    };
    credits.addEventListener('change',update);price.addEventListener('input',update);update();
    const result=panel.querySelector('#passResult');
    if(result)new MutationObserver(()=>{
      const count=Number(credits.value||10);
      result.querySelectorAll('p,b').forEach(el=>{el.textContent=el.textContent.replace(/10 credits?/gi,`${count} credit${count===1?'':'s'}`).replace(/adds 10 credits/gi,`adds ${count} credits`)})
    }).observe(result,{childList:true,subtree:true});
    const title=panel.querySelector('.panel-head h2');if(title)title.textContent='Sell Class Credits';
    const copy=panel.querySelector('.panel-head p:last-child');if(copy)copy.textContent='Sell 1, 5, 10, 20, 30 or 50 credits to a customer account or as a gift code.';
  }

  // Historical SEPA recurring-membership prototype intentionally remains dormant.
  // Production commerce is handled by SumUp Hosted Checkout instead.
  async function enhanceMembership(){
    return;
  }

  function enhanceMonthlyRecurrence(){
    const input=document.querySelector('#cRepeat');
    if(!input||input.dataset.monthly)return;
    input.dataset.monthly='1';input.max='36';
    const label=input.closest('label');
    if(label){for(const node of label.childNodes){if(node.nodeType===Node.TEXT_NODE&&node.textContent.trim()){node.textContent='MONTHLY REPEAT';break}}const small=label.querySelector('small');if(small)small.textContent='1 = once · 12 = once per month for 12 months'}
    const head=input.closest('.panel')?.querySelector('.panel-head p:last-child');if(head)head.textContent='Create one session or repeat it automatically every month.';
  }

  async function annotateLanguages(){
    const rows=[...document.querySelectorAll('.trow:not(.head)')];if(!rows.length)return;
    let data;try{const r=await authFetch('/api/staff/booking-preferences');if(!r.ok)return;data=await r.json()}catch(_){return}
    const map=new Map((data.preferences||[]).map(x=>[x.reference,x]));
    rows.forEach(row=>{
      if(row.querySelector('.booking-lang-flag'))return;
      const match=row.textContent.match(/CP-[A-Z0-9-]+/);if(!match)return;
      const pref=map.get(match[0]);if(!pref)return;
      const first=row.querySelector('div,span');if(!first)return;
      const badge=document.createElement('span');badge.className='booking-lang-flag';badge.textContent=pref.language==='de'?' DE':' EN';badge.title=pref.sepa?`SEPA mandate · IBAN •••• ${pref.iban_last4}`:'Booking language';first.appendChild(badge);
    });
  }

  async function enhanceNotifications(){
    const createPanel=document.querySelector('#cRepeat')?.closest('.panel');
    if(!createPanel||document.querySelector('#notificationStatus'))return;
    const box=document.createElement('div');box.id='notificationStatus';box.className='notification-status';box.innerHTML='<b>Instant attendee emails</b><small>Trainer changes, class changes and cancellations send an email immediately to website-booked attendees.</small>';
    createPanel.querySelector('.panel-head')?.appendChild(box);
    try{const r=await authFetch('/api/staff/class-notifications');if(!r.ok)return;const d=await r.json();const recent=(d.notifications||[]).slice(0,3);if(recent.length)box.innerHTML+=`<div>${recent.map(n=>`<span class="notify-chip ${n.status}">${n.status} · ${n.event_type}</span>`).join('')}</div>`}catch(_){ }
  }

  let scheduled=false;
  const run=()=>{if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;enhancePassSale();enhanceMonthlyRecurrence();annotateLanguages();enhanceNotifications()})};
  new MutationObserver(run).observe(document.body,{childList:true,subtree:true});run();
})();
