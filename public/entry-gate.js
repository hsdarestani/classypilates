(()=>{
  const gate=document.querySelector('#experienceGate');
  if(!gate)return;
  const body=document.body;

  if(!document.querySelector('link[data-classfit-coming-soon]')){
    const css=document.createElement('link');
    css.rel='stylesheet';
    css.href='./classfit-coming-soon.css?v=20260831-1';
    css.dataset.classfitComingSoon='1';
    document.head.appendChild(css);
  }
  if(!document.querySelector('link[data-client-feedback]')){
    const css=document.createElement('link');css.rel='stylesheet';css.href='./client-feedback.css?v=20260827-2';css.dataset.clientFeedback='1';document.head.appendChild(css);
  }
  if(!document.querySelector('link[data-homepage-feedback]')){
    const css=document.createElement('link');css.rel='stylesheet';css.href='./homepage-feedback.css?v=20260831-1';css.dataset.homepageFeedback='1';document.head.appendChild(css);
  }

  const requestedStyle=document.createElement('style');
  requestedStyle.dataset.clientRequestedUi='1';
  requestedStyle.textContent=`
    #passes .pass-grid{grid-template-columns:repeat(4,minmax(0,1fr))!important}
    #schedule .booking-topline.client-choice-removed{justify-content:flex-end}
    .client-type-choice{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:22px 0 4px}
    .client-type-choice button{appearance:none;border:1px solid rgba(24,23,20,.18);background:#fff;border-radius:18px;padding:20px;text-align:left;cursor:pointer;min-height:116px;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}
    .client-type-choice button:hover,.client-type-choice button:focus-visible{transform:translateY(-2px);border-color:#171713;box-shadow:0 12px 30px rgba(23,23,19,.08);outline:none}
    .client-type-choice b{display:block;font-size:16px;margin-bottom:8px;color:#171713}
    .client-type-choice span{display:block;font-size:12px;line-height:1.55;color:#6e6a63}
    @media(max-width:980px){#passes .pass-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
    @media(max-width:620px){#passes .pass-grid{grid-template-columns:1fr!important}.client-type-choice{grid-template-columns:1fr}.client-type-choice button{min-height:0;padding:17px}}
  `;
  document.head.appendChild(requestedStyle);

  const syncText=(el,value)=>{if(el&&el.textContent!==value)el.textContent=value};
  function applyClientRequestedUi(){
    const isDe=document.documentElement.lang==='de';
    const fitCard=gate.querySelector('.experience-card.fit');
    if(fitCard){
      syncText(fitCard.querySelector('.experience-card-meta>span:first-child'),'HIIT');
      syncText(fitCard.querySelector('h3'),'Classy Fitness');
      syncText(fitCard.querySelector('.experience-card-action>span'),isDe?'Classy Fitness öffnen':'Enter Classy Fitness');
      fitCard.setAttribute('aria-label',isDe?'Classy Fitness öffnen':'Open Classy Fitness');
    }
    gate.querySelectorAll('.experience-card-icon').forEach(icon=>icon.remove());

    const bookingTabs=document.querySelector('#schedule .booking-tabs');
    if(bookingTabs)bookingTabs.remove();
    const bookingTopline=document.querySelector('#schedule .booking-topline');
    if(bookingTopline)bookingTopline.classList.add('client-choice-removed');

    const passGrid=document.querySelector('#passes .pass-grid');
    if(passGrid){
      let five=passGrid.querySelector('[data-five-class-pass]');
      if(!five){
        five=document.createElement('article');
        five.dataset.fiveClassPass='1';
        five.innerHTML='<span></span><h3></h3><b>119 €</b><p></p><button type="button"></button>';
        five.querySelector('button')?.addEventListener('click',()=>{location.href='/shop?product=five'});
        const featured=passGrid.querySelector('.featured');
        passGrid.insertBefore(five,featured||passGrid.children[1]||null);
      }
      syncText(five.querySelector('span'),isDe?'FLEXIBEL':'FLEXIBLE');
      syncText(five.querySelector('h3'),isDe?'5 Kurse':'5 Classes');
      syncText(five.querySelector('b'),'119 €');
      syncText(five.querySelector('p'),isDe?'Fünf Kurse für einen flexiblen Trainingsrhythmus.':'Five classes for a flexible training rhythm.');
      syncText(five.querySelector('button'),isDe?'In den Warenkorb →':'Buy in the shop →');
    }
    const smallPrint=document.querySelector('#passes .small-print');
    if(smallPrint){
      let link=smallPrint.querySelector('[data-all-payment-methods]');
      if(!link){smallPrint.textContent='';link=document.createElement('a');link.href='/shop';link.dataset.allPaymentMethods='1';smallPrint.appendChild(link)}
      syncText(link,isDe?'Alle Zahlungsarten ansehen ':'View all payment methods ');
    }
  }

  applyClientRequestedUi();

  const bookingOpenClass=typeof window.openClass==='function'?window.openClass:null;
  if(bookingOpenClass){
    window.openClass=function(r){
      if(!r||Number(r.spots)<=0)return bookingOpenClass(r);
      const isDe=document.documentElement.lang==='de';
      const title=document.querySelector('#drawerTitle');
      const drawer=document.querySelector('#drawerBody');
      const shell=document.querySelector('#bookingDrawer');
      if(!title||!drawer||typeof window.openDrawer!=='function')return bookingOpenClass(r);
      if(shell)shell.classList.add('booking-v2');
      title.textContent=isDe?'Wie möchtest du fortfahren?':'How would you like to continue?';
      const summary=typeof window.selectedSummary==='function'?window.selectedSummary(r):'';
      drawer.innerHTML=`${summary}<div class="wizard-panel"><div class="wizard-kicker">${isDe?'BEVOR WIR BUCHEN':'BEFORE WE BOOK'}</div><h4>${isDe?'Bist du schon bei Classy?':'Are you already with Classy?'}</h4><p>${isDe?'Wähle eine Option. Danach öffnen wir direkt den passenden Login- oder Registrierungsbereich.':'Choose one option and we will open the correct sign-in or registration section immediately.'}</p><div class="client-type-choice"><button type="button" data-client-kind="returning"><b>${isDe?'Bestehender Kunde':'Returning client'}</b><span>${isDe?'Mit deinem bestehenden Classy Konto anmelden.':'Sign in with your existing Classy account.'}</span></button><button type="button" data-client-kind="new"><b>${isDe?'Neuer Kunde':'New client'}</b><span>${isDe?'Ein Classy Konto erstellen und mit der Buchung fortfahren.':'Create your Classy account and continue the booking.'}</span></button></div><button class="drawer-action secondary" id="cancelClientChoice" type="button">${isDe?'Abbrechen':'Cancel'}</button></div>`;
      window.openDrawer();
      const continueWith=mode=>{
        state.mode=mode==='new'?'first':'returning';
        bookingOpenClass(r);
        setTimeout(()=>document.querySelector('#goSpot')?.click(),0);
      };
      drawer.querySelector('[data-client-kind="returning"]')?.addEventListener('click',()=>continueWith('returning'));
      drawer.querySelector('[data-client-kind="new"]')?.addEventListener('click',()=>continueWith('new'));
      drawer.querySelector('#cancelClientChoice')?.addEventListener('click',()=>window.closeDrawer?.());
    };
  }

  const remember=(choice)=>{try{sessionStorage.setItem('cpExperienceChoice',choice)}catch(_){}};
  const current=()=>{try{return sessionStorage.getItem('cpExperienceChoice')}catch(_){return null}};
  const open=()=>{gate.removeAttribute('aria-hidden');gate.classList.remove('is-leaving');body.classList.add('gate-open');requestAnimationFrame(()=>gate.querySelector('[data-enter-pilates]')?.focus({preventScroll:true}))};
  const close=()=>{gate.classList.add('is-leaving');body.classList.remove('gate-open');setTimeout(()=>gate.setAttribute('aria-hidden','true'),560)};

  const comingSoon=document.createElement('div');
  comingSoon.className='classfit-coming-soon';
  comingSoon.setAttribute('aria-hidden','true');
  comingSoon.innerHTML=`
    <div class="classfit-coming-soon-bg" aria-hidden="true"></div>
    <button class="classfit-coming-soon-close" type="button" aria-label="Back to experience selection">←</button>
    <div class="classfit-coming-soon-copy" role="dialog" aria-modal="true" aria-labelledby="classfitComingSoonTitle">
      <p class="eyebrow">CLASSY FITNESS · FRANKFURT</p>
      <h2 id="classfitComingSoonTitle">Something powerful<br><em>is coming.</em></h2>
      <p>High-energy small group training, strength and conditioning — the new Classy Fitness experience is currently being prepared.</p>
      <div class="classfit-coming-soon-badge"><span></span> COMING SOON</div>
      <button class="classfit-coming-soon-back" type="button">Back to Classy</button>
    </div>`;
  gate.appendChild(comingSoon);

  const showComingSoon=()=>{
    comingSoon.setAttribute('aria-hidden','false');
    gate.classList.add('fit-coming-soon-open');
    requestAnimationFrame(()=>comingSoon.querySelector('.classfit-coming-soon-back')?.focus({preventScroll:true}));
  };
  const hideComingSoon=()=>{
    comingSoon.setAttribute('aria-hidden','true');
    gate.classList.remove('fit-coming-soon-open');
    requestAnimationFrame(()=>gate.querySelector('[data-enter-fit]')?.focus({preventScroll:true}));
  };

  gate.querySelector('[data-enter-pilates]')?.addEventListener('click',()=>{remember('pilates');close()});
  gate.querySelector('[data-enter-fit]')?.addEventListener('click',e=>{e.preventDefault();showComingSoon()});
  comingSoon.querySelector('.classfit-coming-soon-close')?.addEventListener('click',hideComingSoon);
  comingSoon.querySelector('.classfit-coming-soon-back')?.addEventListener('click',hideComingSoon);

  const switcher=document.createElement('button');
  switcher.type='button';switcher.className='experience-switch';switcher.textContent='Switch experience';switcher.setAttribute('aria-label','Choose Classy Fitness or Classy Pilates');
  switcher.addEventListener('click',()=>{try{sessionStorage.removeItem('cpExperienceChoice')}catch(_){}hideComingSoon();applyClientRequestedUi();open()});
  body.appendChild(switcher);

  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape'||gate.hasAttribute('aria-hidden'))return;
    if(comingSoon.getAttribute('aria-hidden')==='false'){hideComingSoon();return}
    remember('pilates');close();
  });

  if(current()==='pilates'){gate.setAttribute('aria-hidden','true');body.classList.remove('gate-open')}else{open()}

  /* Booking floor plans: kept as separate assets so the booking wizard stays maintainable. */
  if(!document.querySelector('link[data-studio-layouts]')){
    const css=document.createElement('link');css.rel='stylesheet';css.href='./studio-layouts.css?v=20260827-feedback1';css.dataset.studioLayouts='1';document.head.appendChild(css);
  }
  if(!document.querySelector('script[data-studio-layouts]')){
    const script=document.createElement('script');script.src='./studio-layouts.js?v=20260907-bhf1-bottom-mirror';script.defer=true;script.dataset.studioLayouts='1';document.body.appendChild(script);
  }

  if(!document.querySelector('script[data-client-feedback]')){
    const script=document.createElement('script');script.src='./client-feedback.js?v=20260831-whatsapp2';script.defer=true;script.dataset.clientFeedback='1';document.body.appendChild(script);
  }
  if(!document.querySelector('script[data-homepage-feedback]')){
    const script=document.createElement('script');script.src='./homepage-feedback.js?v=20260908-coach-background1';script.defer=true;script.dataset.homepageFeedback='1';document.body.appendChild(script);
  }
  if(!document.querySelector('script[data-class-language]')){
    const script=document.createElement('script');script.src='./class-language.js?v=20260907-code-only';script.async=false;script.dataset.classLanguage='1';document.body.appendChild(script);
  }

  /* Production bridge: once the real API is available, selected spots and reservations are synced centrally. */
  if(!document.querySelector('script[data-production-sync]')){
    const sync=document.createElement('script');sync.src='./production-sync.js?v=20260824-1';sync.defer=true;sync.dataset.productionSync='1';document.body.appendChild(sync);
  }

  const footerLinks=document.querySelector('.footer-links');
  if(footerLinks&&!footerLinks.querySelector('[data-team-login]')){
    const team=document.createElement('a');team.href='/login';team.textContent='Login';team.dataset.teamLogin='1';footerLinks.appendChild(team);
  }

  new MutationObserver(applyClientRequestedUi).observe(document.body,{childList:true,subtree:true});
})();