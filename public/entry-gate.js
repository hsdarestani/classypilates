(()=>{
  const gate=document.querySelector('#experienceGate');
  if(!gate)return;
  const body=document.body;

  if(!document.querySelector('link[data-classfit-coming-soon]')){
    const css=document.createElement('link');
    css.rel='stylesheet';
    css.href='./classfit-coming-soon.css?v=20260827-1';
    css.dataset.classfitComingSoon='1';
    document.head.appendChild(css);
  }
  if(!document.querySelector('link[data-client-feedback]')){
    const css=document.createElement('link');css.rel='stylesheet';css.href='./client-feedback.css?v=20260827-2';css.dataset.clientFeedback='1';document.head.appendChild(css);
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
      <p class="eyebrow">CLASS FIT · FRANKFURT</p>
      <h2 id="classfitComingSoonTitle">Something powerful<br><em>is coming.</em></h2>
      <p>High-energy small group training, strength and conditioning — the new Class Fit experience is currently being prepared.</p>
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
  switcher.type='button';switcher.className='experience-switch';switcher.textContent='Switch experience';switcher.setAttribute('aria-label','Choose Class Fit or Classy Pilates');
  switcher.addEventListener('click',()=>{try{sessionStorage.removeItem('cpExperienceChoice')}catch(_){}hideComingSoon();open()});
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
    const script=document.createElement('script');script.src='./studio-layouts.js?v=20260828-bhf1-exact2';script.defer=true;script.dataset.studioLayouts='1';document.body.appendChild(script);
  }

  if(!document.querySelector('script[data-client-feedback]')){
    const script=document.createElement('script');script.src='./client-feedback.js?v=20260827-2';script.defer=true;script.dataset.clientFeedback='1';document.body.appendChild(script);
  }
  if(!document.querySelector('script[data-class-language]')){
    const script=document.createElement('script');script.src='./class-language.js?v=20260828-2';script.async=false;script.dataset.classLanguage='1';document.body.appendChild(script);
  }

  /* Production bridge: once the real API is available, selected spots and reservations are synced centrally. */
  if(!document.querySelector('script[data-production-sync]')){
    const sync=document.createElement('script');sync.src='./production-sync.js?v=20260824-1';sync.defer=true;sync.dataset.productionSync='1';document.body.appendChild(sync);
  }

  const footerLinks=document.querySelector('.footer-links');
  if(footerLinks&&!footerLinks.querySelector('[data-team-login]')){
    const team=document.createElement('a');team.href='/login';team.textContent='Login';team.dataset.teamLogin='1';footerLinks.appendChild(team);
  }
})();
