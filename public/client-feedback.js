(()=>{
  const $=(s,c=document)=>c.querySelector(s),$$=(s,c=document)=>[...c.querySelectorAll(s)];
  const originalFetch=window.fetch.bind(window);
  const LANG_KEY='cpBookingLanguage';
  const CLASS_LANG_KEY='cpActiveClassLanguage';
  const VOUCHER_KEY='cpBookingVoucher';
  const lang=()=>{const saved=sessionStorage.getItem(LANG_KEY);if(saved==='de'||saved==='en')return saved;return document.documentElement.lang==='de'?'de':'en'};
  const classLang=()=>{const saved=sessionStorage.getItem(CLASS_LANG_KEY);return saved==='en'?'en':'de'};
  const flag=l=>l==='de'?'🇩🇪':'🇬🇧';
  const iconInstagram='<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg>';
  const iconWhatsapp='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11.5a8 8 0 0 1-11.8 7L4 20l1.5-4A8 8 0 1 1 20 11.5Z"/><path d="M9 8.3c.2 2 1.8 4.1 4.2 5.3.7.3 1.3.4 1.8-.2l.8-1-2.2-1.1-.6.8c-.2.2-.5.2-.8.1-1.1-.6-2-1.4-2.6-2.5-.2-.3-.1-.6.1-.8l.6-.6-.9-2.1-.4.1Z"/></svg>';

  function enhanceSocialIcons(){
    $$('.classy-quick-dock a').forEach(a=>{
      const label=(a.getAttribute('aria-label')||a.textContent||'').toLowerCase(),slot=a.querySelector('.dock-icon');if(!slot)return;
      if(label.includes('instagram'))slot.innerHTML=iconInstagram;
      if(label.includes('call')||label.includes('whatsapp')){a.href='https://wa.me/4915253816033';a.target='_blank';a.rel='noopener';a.setAttribute('aria-label','WhatsApp Classy Pilates');slot.innerHTML=iconWhatsapp;const b=a.querySelector('b');if(b)b.textContent='WhatsApp'}
    });
    $$('.studio-hover-actions a').forEach(a=>{
      const label=(a.getAttribute('aria-label')||a.textContent||'').toLowerCase();
      if(label.includes('instagram')){const text=a.querySelector('span:last-child')?.textContent||'Instagram';a.innerHTML=`<span class="brand-action-icon">${iconInstagram}</span><span>${text}</span>`}
      if(label.includes('call')||label.includes('whatsapp')){a.href='https://wa.me/4915253816033';a.target='_blank';a.rel='noopener';a.setAttribute('aria-label','WhatsApp');a.innerHTML=`<span class="brand-action-icon">${iconWhatsapp}</span><span>WhatsApp</span>`}
    });
  }

  function addLanguageSelector(){
    const go=$('#goPayment');if(!go||$('#bookingLanguage'))return;
    const panel=go.closest('.wizard-panel');if(!panel)return;
    const anchor=panel.querySelector('.wizard-check');
    const box=document.createElement('div');box.id='bookingLanguage';box.className='booking-language-select';box.innerHTML=`<div><span>BOOKING LANGUAGE</span><small>Urgent class-change emails will use this language.</small></div><div class="language-choice"><button type="button" data-booking-lang="de">🇩🇪 DE</button><button type="button" data-booking-lang="en">🇬🇧 EN</button></div>`;
    if(anchor)panel.insertBefore(box,anchor);else panel.insertBefore(box,go.parentElement);
    const set=l=>{sessionStorage.setItem(LANG_KEY,l);$$('[data-booking-lang]',box).forEach(b=>b.classList.toggle('active',b.dataset.bookingLang===l));decorateLanguage()};
    $$('[data-booking-lang]',box).forEach(b=>b.addEventListener('click',()=>set(b.dataset.bookingLang)));set(lang());
  }

  function decorateLanguage(){
    const l=classLang();
    $$('.wizard-class-card').forEach(card=>{let badge=card.querySelector('.booking-language-badge');if(!badge){badge=document.createElement('span');badge.className='booking-language-badge';const copy=card.querySelector('div:nth-child(2)');copy?.appendChild(badge)}if(badge){badge.dataset.language=l;badge.setAttribute('aria-label',l==='en'?'Class language English':'Kurssprache Deutsch');badge.title=l==='en'?'Class language: English':'Kurssprache: Deutsch';badge.textContent=`${flag(l)} ${l.toUpperCase()}`}});
  }

  function enhancePayment(){
    const finish=$('#finishPayment');if(!finish)return;
    const panel=finish.closest('.wizard-panel');if(!panel)return;
    const grid=panel.querySelector('.wizard-payment-grid');
    const card=grid?.querySelector('[data-wpay="card"]');
    if(card&&!card.dataset.cardBrands){card.dataset.cardBrands='1';const mark=card.querySelector('.pay-mark');if(mark)mark.innerHTML='<span class="card-brand visa">VISA</span><span class="card-brand mastercard"><i></i><i></i></span><span class="card-brand amex">AMEX</span>';const accepted=document.createElement('div');accepted.className='accepted-card-brands';accepted.innerHTML='<span>ACCEPTED CARDS</span><b>Visa</b><b>Mastercard</b><b>American Express</b><b>V PAY</b>';grid?.insertAdjacentElement('afterend',accepted)}
    if(!$('#bookingVoucher')){
      const voucher=document.createElement('div');voucher.id='bookingVoucher';voucher.className='voucher-box';voucher.innerHTML=`<span>VOUCHER / GIFT CODE</span><div><input id="voucherCode" autocomplete="off" placeholder="CLASSY-XXXXXX-XXXXXX" value="${(sessionStorage.getItem(VOUCHER_KEY)||'').replace(/[<>&\"']/g,'')}"><button type="button" id="saveVoucher">Use code</button></div><small id="voucherHint">The code will be validated securely when you confirm the booking.</small>`;
      const note=panel.querySelector('.demo-payment-note');panel.insertBefore(voucher,note||finish.parentElement);
      $('#saveVoucher',voucher)?.addEventListener('click',()=>{const code=$('#voucherCode',voucher).value.trim().toUpperCase().replace(/\s+/g,'');sessionStorage.setItem(VOUCHER_KEY,code);$('#voucherHint',voucher).textContent=code?'Code saved — it will be applied before your booking is confirmed.':'Enter a voucher or gift code.'});
      $('#voucherCode',voucher)?.addEventListener('input',e=>sessionStorage.setItem(VOUCHER_KEY,e.target.value.trim().toUpperCase().replace(/\s+/g,'')));
    }
    const sepaActive=grid?.querySelector('[data-wpay="sepa"].active');
    let mandate=$('#sepaMandate');
    if(sepaActive&&!mandate){mandate=document.createElement('div');mandate.id='sepaMandate';mandate.className='sepa-mandate';mandate.innerHTML='<span>SEPA LASTSCHRIFTMANDAT</span><div class="sepa-grid"><label><span>ACCOUNT HOLDER *</span><input id="sepaHolder" autocomplete="name"></label><label><span>IBAN *</span><input id="sepaIban" autocomplete="off" placeholder="DE00 0000 0000 0000 0000 00"></label></div><label class="sepa-check"><input id="sepaConsent" type="checkbox"><span>I authorize Classy Pilates / its payment provider to collect the payment from this account by SEPA Direct Debit. *</span></label><small>For privacy, the booking system sends only the account holder, mandate timestamp and the final four IBAN characters to the Classy server. The full IBAN must be tokenized by the connected payment provider.</small>';const note=panel.querySelector('.demo-payment-note');panel.insertBefore(mandate,note||finish.parentElement);const validate=()=>{const holder=$('#sepaHolder')?.value.trim()||'',iban=($('#sepaIban')?.value||'').replace(/\s+/g,'').toUpperCase(),ok=holder.length>1&&/^[A-Z]{2}[A-Z0-9]{13,32}$/.test(iban)&&!!$('#sepaConsent')?.checked;finish.disabled=!ok;finish.dataset.sepaReady=ok?'1':'0'};mandate.addEventListener('input',validate);mandate.addEventListener('change',validate);validate()}
    if(!sepaActive&&mandate){mandate.remove();finish.disabled=false;delete finish.dataset.sepaReady}
    decorateLanguage();
  }

  let voucherInFlight=false;
  window.fetch=async(input,opt={})=>{
    const url=typeof input==='string'?input:(input?.url||'');const method=String(opt.method||'GET').toUpperCase();
    if(url==='/api/bookings'&&method==='POST'&&typeof opt.body==='string'){
      let body;try{body=JSON.parse(opt.body)}catch(_){body=null}
      if(body){const l=lang();body.language=l;const holder=$('#sepaHolder')?.value.trim()||'',iban=($('#sepaIban')?.value||'').replace(/\s+/g,'').toUpperCase();body.sepaAccountHolder=holder;body.sepaIbanLast4=iban?iban.slice(-4):'';body.sepaMandateAccepted=!!$('#sepaConsent')?.checked;opt={...opt,body:JSON.stringify(body)}}
      const code=(sessionStorage.getItem(VOUCHER_KEY)||'').trim().toUpperCase().replace(/\s+/g,'');
      if(code&&!voucherInFlight){voucherInFlight=true;try{const r=await originalFetch('/api/customer/vouchers/redeem',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'content-type':'application/json'},body:JSON.stringify({code})});if(!r.ok){let d={};try{d=await r.json()}catch(_){}const hint=$('#voucherHint');if(hint)hint.textContent=d.detail==='voucher_already_redeemed'?'This code has already been redeemed.':'This voucher code could not be validated.';return new Response(JSON.stringify({detail:d.detail||'voucher_not_found'}),{status:r.status,headers:{'content-type':'application/json'}})}sessionStorage.removeItem(VOUCHER_KEY);const hint=$('#voucherHint');if(hint)hint.textContent='Voucher applied — credit added to your account.'}finally{voucherInFlight=false}}
    }
    return originalFetch(input,opt);
  };

  let scheduled=false;const run=()=>{if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;enhanceSocialIcons();addLanguageSelector();decorateLanguage();enhancePayment()})};
  new MutationObserver(run).observe(document.body,{childList:true,subtree:true});run();
})();
