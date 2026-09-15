(()=>{
  const $=(s,c=document)=>c.querySelector(s), $$=(s,c=document)=>[...c.querySelectorAll(s)];
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const locale=()=>document.documentElement.lang==='de'?'de-DE':'en-GB';
  const money=cents=>new Intl.NumberFormat(locale(),{style:'currency',currency:'EUR'}).format((Number(cents)||0)/100);
  const dt=value=>{try{return new Intl.DateTimeFormat(locale(),{dateStyle:'medium',timeStyle:'short'}).format(new Date(value))}catch(_){return value||'—'}};

  function ensureScrim(){
    if($('.account-nav-scrim'))return;
    const scrim=document.createElement('div');scrim.className='account-nav-scrim';scrim.setAttribute('aria-hidden','true');document.body.appendChild(scrim);
    const close=()=>{$('#accountSide')?.classList.remove('open');document.body.classList.remove('account-menu-open')};
    scrim.addEventListener('click',close);
    document.addEventListener('keydown',event=>{if(event.key==='Escape')close()});
    $('#accountMenu')?.addEventListener('click',()=>requestAnimationFrame(()=>document.body.classList.toggle('account-menu-open',$('#accountSide')?.classList.contains('open'))));
    $('#accountNav')?.addEventListener('click',event=>{if(event.target.closest('button'))close()});
  }

  function improveGiftCopy(){
    const card=$('.voucher-redeem');if(!card||card.dataset.copyFixed==='1')return;card.dataset.copyFixed='1';
    const p=card.querySelector('p');if(p)p.textContent='Enter your Classy gift code to add the credits included in that gift code to this account.';
  }

  function improveAutomaticPlace(){
    $$('.booking-meta',document).forEach(meta=>{
      [...meta.children].forEach(cell=>{
        const label=cell.querySelector('span');if(!label||label.textContent.trim().toUpperCase()!=='SPOT')return;
        label.textContent='PLACE';const value=cell.querySelector('b');
        if(value&&['—','-',''].includes(value.textContent.trim())){value.textContent='Assigned automatically';value.classList.add('auto-place')}
      });
    });
  }

  async function injectPayments(){
    const hero=$('.credit-hero');if(!hero||$('#sumupHistory'))return;
    const panel=document.createElement('section');panel.className='account-panel sumup-history';panel.id='sumupHistory';
    panel.innerHTML='<div class="account-panel-head"><div><p>PAYMENTS</p><h2>SumUp payment history</h2><small>Online class and credit payments linked to this account.</small></div></div><div class="account-loading">Loading payments…</div>';
    hero.insertAdjacentElement('afterend',panel);
    try{
      const response=await fetch('/api/customer/payments',{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw new Error('request_failed');const data=await response.json();
      const rows=data.payments||[];
      panel.innerHTML=`<div class="account-panel-head"><div><p>PAYMENTS</p><h2>SumUp payment history</h2><small>${rows.length?`${rows.length} online payment${rows.length===1?'':'s'} · `:''}Hosted Checkout is the online payment provider.</small></div><span class="sumup-badge paid">SUMUP</span></div>${rows.length?`<div class="sumup-history-list">${rows.map(row=>`<article class="sumup-payment-row"><div><span>${row.booking_reference?'CLASS BOOKING':'CLASS CREDITS'}</span><b>${esc(row.booking_reference||row.reference)}</b><small>${esc(row.reference)} · ${dt(row.created_at)}</small></div><div><span>DETAIL</span><b>${row.booking_reference?'Class payment':`${Number(row.credits)||0} credit${Number(row.credits)===1?'':'s'}`}</b><small>SumUp Hosted Checkout</small></div><div><span>AMOUNT</span><b class="payment-amount">${money(row.amount_cents)}</b></div><span class="sumup-badge ${esc(row.status)}">${esc(row.status)}</span></article>`).join('')}</div>`:'<div class="empty-account"><div><span>No online payments yet.</span><p>Completed SumUp purchases will appear here automatically.</p></div></div>'}`;
    }catch(_){
      panel.innerHTML='<div class="account-panel-head"><div><p>PAYMENTS</p><h2>SumUp payment history</h2></div></div><div class="empty-account"><div><span>Payments unavailable.</span><p>Please try again in a moment.</p></div></div>';
    }
  }

  function clarifyCredits(){
    const balance=$('.credit-balance');if(!balance||balance.dataset.copyFixed==='1')return;balance.dataset.copyFixed='1';
    const p=balance.querySelector('p');if(p)p.textContent='Credits from confirmed SumUp purchases are added to your Classy account and can be used across all studios.';
  }

  let queued=false;
  const run=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;ensureScrim();improveGiftCopy();improveAutomaticPlace();clarifyCredits();injectPayments()})};
  new MutationObserver(run).observe(document.body,{childList:true,subtree:true});run();
})();
