(()=>{
  const WHATSAPP='https://wa.me/4915253816033';
  const whatsappIcon='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11.5a8 8 0 0 1-11.8 7L4 20l1.5-4A8 8 0 1 1 20 11.5Z"/><path d="M9 8.3c.2 2 1.8 4.1 4.2 5.3.7.3 1.3.4 1.8-.2l.8-1-2.2-1.1-.6.8c-.2.2-.5.2-.8.1-1.1-.6-2-1.4-2.6-2.5-.2-.3-.1-.6.1-.8l.6-.6-.9-2.1-.4.1Z"/></svg>';
  const COACH_PHOTOS=[
    {match:name=>/^anna\s*k\b/.test(name)||name==='anna',src:'/anna%20K.jpg'},
    {match:name=>/^sayna\b/.test(name),src:'/sayna.jpg'},
    {match:name=>/^luca\b/.test(name),src:'/luca.jpg'}
  ];

  const coachName=value=>String(value||'').trim().toLowerCase().replace(/[.]+/g,'').replace(/\s+/g,' ');
  const coachPhoto=value=>{const name=coachName(value);return COACH_PHOTOS.find(item=>item.match(name))?.src||''};

  const style=document.createElement('style');
  style.textContent=`
    .class-coach.has-local-photo{position:relative;min-height:46px;padding-left:54px;display:flex;flex-direction:column;justify-content:center}
    .class-coach .coach-inline-avatar{position:absolute;left:0;top:50%;width:42px;height:42px;transform:translateY(-50%);border-radius:50%;object-fit:cover;object-position:center;border:1px solid rgba(21,21,19,.12);background:#d8d0c1}
    .coach-real-avatar img{width:100%;height:100%;object-fit:cover;object-position:center}
    @media(max-width:760px){.class-coach.has-local-photo{padding-left:46px;min-height:40px}.class-coach .coach-inline-avatar{width:36px;height:36px}}
  `;
  document.head.appendChild(style);

  function fixStudioWhatsApp(){
    document.querySelectorAll('.studio-hover-actions').forEach(wrap=>{
      const link=wrap.querySelector('a[href^="tel:"],a[aria-label*="Call"],a[aria-label*="WhatsApp"],a[href*="wa.me"]');
      if(!link||link.dataset.whatsappFixed==='1')return;
      link.dataset.whatsappFixed='1';
      link.href=WHATSAPP;
      link.target='_blank';
      link.rel='noopener';
      link.setAttribute('aria-label','WhatsApp Classy Pilates');
      link.innerHTML=`<span class="brand-action-icon">${whatsappIcon}</span><span>WhatsApp</span>`;
    });
  }

  function applyCoachPhotos(){
    document.querySelectorAll('#classList .class-coach').forEach(box=>{
      const name=box.querySelector('b')?.textContent||'';
      const src=coachPhoto(name);
      const old=box.querySelector('.coach-inline-avatar');
      if(!src){old?.remove();box.classList.remove('has-local-photo');return}
      box.classList.add('has-local-photo');
      let image=old;
      if(!image){image=document.createElement('img');image.className='coach-inline-avatar';box.prepend(image)}
      if(image.getAttribute('src')!==src)image.src=src;
      image.alt=`Coach ${name.trim()}`;
      image.loading='lazy';
    });

    document.querySelectorAll('#coachGrid .coach-real-card').forEach(card=>{
      const name=card.querySelector('h3')?.textContent||'';
      const src=coachPhoto(name);if(!src)return;
      const avatar=card.querySelector('.coach-real-avatar');if(!avatar)return;
      let image=avatar.querySelector('img');
      if(!image){avatar.textContent='';image=document.createElement('img');avatar.appendChild(image)}
      image.src=src;image.alt=`Coach ${name.trim()}`;image.loading='lazy';
    });
  }

  const run=()=>{fixStudioWhatsApp();applyCoachPhotos()};
  run();
  new MutationObserver(run).observe(document.body,{childList:true,subtree:true});
})();
