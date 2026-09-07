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
    .coach-photo-fill{display:block!important;width:100%!important;height:100%!important;object-fit:cover!important;object-position:center!important;border-radius:inherit!important}
    .coach-real-avatar img{width:100%;height:100%;object-fit:cover;object-position:center}
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

  function isCircleLike(el){
    if(!el)return false;
    const rect=el.getBoundingClientRect();
    if(rect.width<24||rect.height<24||rect.width>100||rect.height>100)return false;
    if(Math.max(rect.width,rect.height)/Math.max(1,Math.min(rect.width,rect.height))>1.35)return false;
    const radius=getComputedStyle(el).borderRadius||'';
    return radius.includes('%')||parseFloat(radius)>=Math.min(rect.width,rect.height)*.28;
  }

  function existingScheduleAvatar(row,coachBox,name){
    const initial=(String(name||'').trim()[0]||'').toUpperCase();
    const preferred=['.coach-avatar','.coach-initial','.coach-badge','.class-coach-avatar','[data-coach-avatar]'];
    for(const selector of preferred){
      const found=row.querySelector(selector);
      if(found&&!found.classList.contains('coach-inline-avatar'))return found;
    }
    const coachRect=coachBox.getBoundingClientRect();
    return [...row.querySelectorAll('div,span,i,b')]
      .filter(el=>el!==coachBox&&!coachBox.contains(el)&&!el.classList.contains('coach-inline-avatar')&&el.textContent.trim().toUpperCase()===initial&&isCircleLike(el))
      .sort((a,b)=>{
        const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();
        const ad=Math.hypot((ar.left+ar.width/2)-(coachRect.left+coachRect.width/2),(ar.top+ar.height/2)-(coachRect.top+coachRect.height/2));
        const bd=Math.hypot((br.left+br.width/2)-(coachRect.left+coachRect.width/2),(br.top+br.height/2)-(coachRect.top+coachRect.height/2));
        return ad-bd;
      })[0]||null;
  }

  function fillExistingAvatar(circle,src,name){
    if(!circle||!src)return;
    circle.style.overflow='hidden';
    circle.setAttribute('aria-label',`Coach ${name.trim()}`);
    circle.textContent='';
    const image=document.createElement('img');
    image.className='coach-photo-fill';
    image.src=src;
    image.alt=`Coach ${name.trim()}`;
    image.loading='lazy';
    circle.appendChild(image);
  }

  function applyCoachPhotos(){
    document.querySelectorAll('#classList .coach-inline-avatar').forEach(node=>node.remove());
    document.querySelectorAll('#classList .class-coach.has-local-photo').forEach(box=>box.classList.remove('has-local-photo'));

    document.querySelectorAll('#classList .class-row').forEach(row=>{
      const box=row.querySelector('.class-coach');
      if(!box)return;
      const name=box.querySelector('b')?.textContent||'';
      const src=coachPhoto(name);if(!src)return;
      const circle=existingScheduleAvatar(row,box,name);
      if(circle&&!circle.querySelector('.coach-photo-fill'))fillExistingAvatar(circle,src,name);
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
