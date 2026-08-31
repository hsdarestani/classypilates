(()=>{
  const WHATSAPP='https://wa.me/4915253816033';
  const whatsappIcon='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11.5a8 8 0 0 1-11.8 7L4 20l1.5-4A8 8 0 1 1 20 11.5Z"/><path d="M9 8.3c.2 2 1.8 4.1 4.2 5.3.7.3 1.3.4 1.8-.2l.8-1-2.2-1.1-.6.8c-.2.2-.5.2-.8.1-1.1-.6-2-1.4-2.6-2.5-.2-.3-.1-.6.1-.8l.6-.6-.9-2.1-.4.1Z"/></svg>';

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

  fixStudioWhatsApp();
  new MutationObserver(fixStudioWhatsApp).observe(document.body,{childList:true,subtree:true});
})();
