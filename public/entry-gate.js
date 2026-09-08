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
    @media(max-width:980px){#passes .pass-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
    @media(max-width:620px){#passes .pass-grid{grid-template-columns:1fr!important}}
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
      syncText(link,isDe?'Alle Zahlungsarten ansehen ↗':'View all payment methods ↗');
    }
  }

  applyClientRequestedUi();

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
    const script=document.createElement('script');script.src='./homepage-feedback.js?v=20260908-coach-fullface1';script.defer=true;script.dataset.homepageFeedback='1';document.body.appendChild(script);
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
