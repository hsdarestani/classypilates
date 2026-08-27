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

  async function enhanceMembership(){
    const passPanel=document.querySelector('.pass-sale-panel');
    if(!passPanel||document.querySelector('#membershipPanel'))return;
    const customerSelect=document.querySelector('#passCustomer');
    if(!customerSelect)return;
    const panel=document.createElement('section');
    panel.className='panel membership-panel';panel.id='membershipPanel';
    const start=new Date();start.setDate(start.getDate()+1);
    panel.innerHTML=`<div class="panel-head"><div><p class="kicker">MONTHLY MEMBERSHIP</p><h2>Recurring membership</h2><p>Create a monthly membership with SEPA as the preferred debit method. Bank details are never stored here; the payment-provider mandate is connected separately.</p></div></div><div class="form-grid membership-form"><label>CUSTOMER<select id="membershipCustomer">${customerSelect.innerHTML}</select></label><label>MONTHLY PRICE (€)<input id="membershipAmount" type="number" min="0.01" step="0.01" placeholder="e.g. 99.00"></label><label>CREDITS / MONTH<input id="membershipCredits" type="number" min="1" step="1" placeholder="e.g. 4"></label><label>START DATE<input id="membershipStart" type="date" value="${start.toISOString().slice(0,10)}"></label><label>PAYMENT<select id="membershipPayment"><option value="sepa">SEPA Lastschrift</option></select></label><div class="membership-provider" id="membershipProvider">Checking provider status…</div><div><button class="primary" id="createMembership">Create monthly membership</button></div></div><div class="membership-list" id="membershipList"></div>`;
    passPanel.insertAdjacentElement('afterend',panel);
    const load=async()=>{
      try{const r=await authFetch('/api/staff/memberships');const d=await r.json();document.querySelector('#membershipProvider').innerHTML=d.automatic_debit_ready?'<b>Provider ready</b><small>SEPA automation can be connected to the provider mandate.</small>':'<b>SEPA provider connection required</b><small>The membership is stored now; automatic bank debit needs the provider credentials/mandate connection.</small>';document.querySelector('#membershipList').innerHTML=(d.memberships||[]).length?`<h3>Current memberships</h3>${d.memberships.slice(0,8).map(m=>`<div class="membership-row"><span><b>${m.customer}</b><small>${m.email}</small></span><span><b>${moneyEuros(m.amount_cents)} / month</b><small>${m.credits_per_month} credits · ${m.payment_method.toUpperCase()}</small></span><span class="status ${m.status==='active'?'active':''}">${m.status}</span><small>${m.provider_status}</small></div>`).join('')}`:'<div class="empty">No monthly memberships yet.</div>'}catch(_){document.querySelector('#membershipProvider').textContent='Membership service unavailable.'}
    };
    document.querySelector('#createMembership').addEventListener('click',async()=>{
      const amount=Math.round(Number(String(document.querySelector('#membershipAmount').value).replace(',','.'))*100),credits=Number(document.querySelector('#membershipCredits').value),customer_id=Number(document.querySelector('#membershipCustomer').value),starts_on=document.querySelector('#membershipStart').value;
      if(!amount||amount<1||!credits||credits<1||!customer_id||!starts_on)return;
      const r=await authFetch('/api/staff/memberships',{method:'POST',body:JSON.stringify({customer_id,amount_cents:amount,credits_per_month:credits,starts_on,payment_method:'sepa'})});
      if(!r.ok)return;await load();
    });
    load();
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
      const badge=document.createElement('span');badge.className='booking-lang-flag';badge.textContent=pref.language==='de'?'🇩🇪 DE':'🇬🇧 EN';badge.title=pref.sepa?`SEPA mandate · IBAN •••• ${pref.iban_last4}`:'Booking language';first.appendChild(badge);
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
  const run=()=>{if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;enhancePassSale();enhanceMembership();enhanceMonthlyRecurrence();annotateLanguages();enhanceNotifications()})};
  new MutationObserver(run).observe(document.body,{childList:true,subtree:true});run();
})();
