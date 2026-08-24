(()=>{
  const gate=document.querySelector('#experienceGate');
  if(!gate)return;
  const body=document.body;
  const remember=(choice)=>{try{sessionStorage.setItem('cpExperienceChoice',choice)}catch(_){}};
  const current=()=>{try{return sessionStorage.getItem('cpExperienceChoice')}catch(_){return null}};
  const open=()=>{gate.removeAttribute('aria-hidden');gate.classList.remove('is-leaving');body.classList.add('gate-open');requestAnimationFrame(()=>gate.querySelector('[data-enter-pilates]')?.focus({preventScroll:true}))};
  const close=()=>{gate.classList.add('is-leaving');body.classList.remove('gate-open');setTimeout(()=>gate.setAttribute('aria-hidden','true'),560)};

  gate.querySelector('[data-enter-pilates]')?.addEventListener('click',()=>{remember('pilates');close()});
  gate.querySelector('[data-enter-fit]')?.addEventListener('click',()=>remember('fit'));

  const switcher=document.createElement('button');
  switcher.type='button';switcher.className='experience-switch';switcher.textContent='Switch experience';switcher.setAttribute('aria-label','Class Fit oder Classy Pilates wählen');
  switcher.addEventListener('click',()=>{try{sessionStorage.removeItem('cpExperienceChoice')}catch(_){}open()});
  body.appendChild(switcher);

  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!gate.hasAttribute('aria-hidden')){remember('pilates');close()}});

  if(current()==='pilates'){gate.setAttribute('aria-hidden','true');body.classList.remove('gate-open')}else{open()}

  /* Booking floor plans: kept as separate assets so the booking wizard stays maintainable. */
  if(!document.querySelector('link[data-studio-layouts]')){
    const css=document.createElement('link');css.rel='stylesheet';css.href='./studio-layouts.css';css.dataset.studioLayouts='1';document.head.appendChild(css);
  }
  if(!document.querySelector('script[data-studio-layouts]')){
    const script=document.createElement('script');script.src='./studio-layouts.js';script.defer=true;script.dataset.studioLayouts='1';document.body.appendChild(script);
  }
})();
