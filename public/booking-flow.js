(()=>{
  const $=(s,c=document)=>c.querySelector(s);const $$=(s,c=document)=>[...c.querySelectorAll(s)];
  const PRESENTATION_PAYMENT=true;
  const PHONE='+4915253816033';
  const INSTAGRAM='https://www.instagram.com/classypilates.de/';
  const coachPhotos={
    Anna:'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=180&q=82',
    Andrea:'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=180&q=82',
    Christina:'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=180&q=82',
    Gabriella:'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=180&q=82',
    Ida:'https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?auto=format&fit=crop&w=180&q=82',
    Jessi:'https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?auto=format&fit=crop&w=180&q=82',
    Kimberley:'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=crop&w=180&q=82',
    Melina:'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=180&q=82',
    Nathalie:'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=180&q=82',
    Sani:'https://images.unsplash.com/photo-1548142813-c348350df52b?auto=format&fit=crop&w=180&q=82',
    Zora:'https://images.unsplash.com/photo-1524250502761-1ac6f2e30d43?auto=format&fit=crop&w=180&q=82',
    Laetitia:'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=180&q=82'
  };
  const fallbackPhotos=Object.values(coachPhotos);
  const photoFor=name=>coachPhotos[name]||fallbackPhotos[Math.abs(seedFor(String(name||'coach')))%fallbackPhotos.length];
  const read=(k,f)=>{try{return JSON.parse(localStorage.getItem(k))??f}catch(_){return f}};
  const write=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(_){}};
  const safe=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const emailOK=v=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  const phoneOK=v=>String(v||'').replace(/\D/g,'').length>=7;
  const payMethods=[
    {id:'card',name:'Karte',detail:'Visa · Mastercard · Amex',mark:'CARD'},
    {id:'apple_pay',name:'Apple Pay',detail:'Face ID / Touch ID',mark:' Pay'},
    {id:'google_pay',name:'Google Pay',detail:'Google Wallet',mark:'G Pay'},
    {id:'paypal',name:'PayPal',detail:'PayPal Checkout',mark:'PayPal'},
    {id:'klarna',name:'Klarna',detail:'Flexible Zahlung',mark:'Klarna.'},
    {id:'sepa',name:'SEPA',detail:'Lastschrift',mark:'SEPA'},
    {id:'link',name:'Link',detail:'Fast checkout by Stripe',mark:'Link'}
  ];
  let wizard=null;

  function moveStudiosBeforeSchedule(){const studiosSection=$('#studios'),schedule=$('#schedule');if(studiosSection&&schedule&&schedule.parentNode)schedule.parentNode.insertBefore(studiosSection,schedule)}

  function addQuickDock(){if($('.classy-quick-dock'))return;const dock=document.createElement('nav');dock.className='classy-quick-dock';dock.setAttribute('aria-label','Schnellaktionen');dock.innerHTML=`<a href="tel:${PHONE}" aria-label="Classy Pilates anrufen"><span class="dock-icon">☎</span><b>Anrufen</b></a><a href="#schedule" aria-label="Kurs buchen"><span class="dock-icon">＋</span><b>Buchen</b></a><a href="${INSTAGRAM}" target="_blank" rel="noopener" aria-label="Instagram öffnen"><span class="dock-icon">◎</span><b>Instagram</b></a>`;document.body.appendChild(dock)}

  function studioActions(){
    $$('.studio-card').forEach(card=>{if($('.studio-hover-actions',card))return;const wrap=document.createElement('div');wrap.className='studio-hover-actions';wrap.innerHTML=`<a href="tel:${PHONE}" data-no-studio-click aria-label="Anrufen">☎ <span>Call</span></a><button type="button" data-studio-book><span>Book</span> ↗</button><a href="${INSTAGRAM}" target="_blank" rel="noopener" data-no-studio-click aria-label="Instagram">◎ <span>Instagram</span></a>`;card.appendChild(wrap);wrap.addEventListener('click',e=>e.stopPropagation());$('[data-studio-book]',wrap)?.addEventListener('click',e=>{e.stopPropagation();state.location=card.dataset.studio;const filter=$('#locationFilter');if(filter)filter.value=state.location;renderSchedule();$('#schedule')?.scrollIntoView({behavior:'smooth',block:'start'})})})
  }

  function coachAvatars(){
    $$('.class-row').forEach(row=>{const coach=$('.class-coach',row);if(!coach||coach.dataset.portrait)return;const name=$('b',coach)?.textContent.trim()||'Coach';coach.dataset.portrait='1';const img=document.createElement('img');img.className='coach-avatar';img.src=photoFor(name);img.alt=`Coach ${name}`;img.loading='lazy';coach.prepend(img)})
  }

  function observeDynamicUi(){const list=$('#classList'),grid=$('#studioGrid');if(list){coachAvatars();new MutationObserver(()=>coachAvatars()).observe(list,{childList:true,subtree:true})}if(grid){studioActions();new MutationObserver(()=>studioActions()).observe(grid,{childList:true,subtree:true})}}

  function studioName(r){return studioById(r.studio)?.name||r.studio}
  function classSummary(r){return `<div class="wizard-class-card"><img src="${photoFor(r.coach)}" alt="Coach ${safe(r.coach)}"><div><span>${safe(r.type)} · ${r.duration} MIN</span><h4>${safe(r.name)}</h4><p>${safe(formatFullDate(r.dateObj))} · ${r.time}<br>${safe(studioName(r))}</p></div><div class="coach-chip"><small>COACH</small><b>${safe(r.coach)}</b><em>Selected</em></div></div>`}
  function setProgress(step){const labels=['Class','Spot','Details','Payment','Done'];const progress=labels.map((x,i)=>`<span class="${i+1<=step?'done':''} ${i+1===step?'active':''}"><i>${i+1<step?'✓':i+1}</i><b>${x}</b></span>`).join('');return `<div class="booking-progress-v2">${progress}</div>`}
  function setDrawer(title,html,step){$('#drawerTitle').textContent=title;$('#drawerBody').innerHTML=setProgress(step)+html;$('#bookingDrawer')?.classList.add('booking-v2');openDrawer()}

  function startWizard(r){wizard={class:r,spot:null,payment:'card',details:read('cpWizardCustomer',{}),mode:state.mode};renderClassStep()}
  function renderClassStep(){const r=wizard.class;const available=Math.max(0,Number(r.spots)||0);setDrawer('Reserve your class',`${classSummary(r)}<div class="wizard-panel"><div class="wizard-kicker">YOUR SESSION</div><h4>Deine Class ist ausgewählt.</h4><p>Prüfe Coach, Studio und Zeit. Im nächsten Schritt wählst du deinen bevorzugten Platz im Studio.</p><div class="class-facts"><div><span>LEVEL</span><b>All Levels</b></div><div><span>AVAILABLE</span><b>${available} Plätze</b></div><div><span>ARRIVE</span><b>10 Min. früher</b></div></div><button class="drawer-action" id="goSpot">Weiter · Platz wählen</button><button class="drawer-action secondary" id="cancelV2">Abbrechen</button></div>`,1);$('#goSpot')?.addEventListener('click',renderSpotStep);$('#cancelV2')?.addEventListener('click',closeDrawer)}

  function seatState(index,r){const h=seedFor(`${r.id}-${index}`);if(index===1+(seedFor(r.id)%Math.max(1,r.capacity)))return'recommended';return h%7===0?'taken':'available'}
  function spotLabel(i,r){if(r.type==='Mat')return`Matte ${String(i).padStart(2,'0')}`;if(r.type==='Barre')return`Position ${String(i).padStart(2,'0')}`;return`Reformer ${String(i).padStart(2,'0')}`}
  function renderSpotStep(){
    const r=wizard.class;const cap=Math.max(6,Number(r.capacity)||10);const seats=Array.from({length:cap},(_,x)=>x+1).map(i=>{const st=seatState(i,r),selected=wizard.spot===i;return `<button type="button" class="studio-spot ${st} ${selected?'selected':''}" data-spot="${i}" ${st==='taken'?'disabled':''} aria-label="${spotLabel(i,r)} ${st==='taken'?'belegt':'verfügbar'}"><span class="spot-bed"><i></i></span><b>${String(i).padStart(2,'0')}</b>${st==='recommended'?'<small>BEST</small>':''}</button>`}).join('');
    setDrawer('Choose your spot',`${classSummary(r)}<div class="studio-map"><div class="studio-map-top"><span>MIRROR WALL</span><div class="coach-station"><img src="${photoFor(r.coach)}" alt="${safe(r.coach)}"><b>${safe(r.coach)}</b><small>COACH</small></div></div><div class="studio-floor"><div class="floor-glow"></div><div class="spot-grid ${r.type==='Mat'||r.type==='Barre'?'mat-layout':''}">${seats}</div><div class="floor-entry">ENTRANCE</div></div><div class="spot-legend"><span><i class="available"></i>Available</span><span><i class="recommended"></i>Recommended</span><span><i class="taken"></i>Taken</span><span><i class="selected"></i>Selected</span></div></div><div class="wizard-sticky-actions"><button class="drawer-action secondary" id="backClass">Zurück</button><button class="drawer-action" id="goDetails" ${wizard.spot?'':'disabled'}>${wizard.spot?`${spotLabel(wizard.spot,r)} · Weiter`:'Wähle deinen Platz'}</button></div>`,2);
    $$('[data-spot]').forEach(btn=>btn.addEventListener('click',()=>{wizard.spot=Number(btn.dataset.spot);renderSpotStep()}));$('#backClass')?.addEventListener('click',renderClassStep);$('#goDetails')?.addEventListener('click',()=>wizard.spot&&renderDetailsStep())
  }

  function renderDetailsStep(){
    const c=wizard.details||{},first=wizard.mode==='first';
    const form=first?`<div class="details-grid"><label class="field"><span>VORNAME *</span><input id="wfFirst" autocomplete="given-name" value="${safe(c.firstName||'')}"></label><label class="field"><span>NACHNAME *</span><input id="wfLast" autocomplete="family-name" value="${safe(c.lastName||'')}"></label><label class="field full"><span>E-MAIL *</span><input id="wfEmail" type="email" autocomplete="email" value="${safe(c.email||'')}"></label><label class="field"><span>MOBILNUMMER *</span><input id="wfPhone" type="tel" autocomplete="tel" value="${safe(c.phone||'')}"></label><label class="field"><span>GEBURTSDATUM *</span><input id="wfBirth" type="date" value="${safe(c.birth||'')}"></label><label class="field full"><span>PASSWORT *</span><input id="wfPassword" type="password" autocomplete="new-password" placeholder="Mindestens 6 Zeichen"></label><label class="field full"><span>NOTFALLKONTAKT</span><input id="wfEmergency" type="tel" value="${safe(c.emergency||'')}" placeholder="Optional"></label></div>`:`<div class="details-grid"><label class="field full"><span>E-MAIL *</span><input id="wfEmail" type="email" autocomplete="email" value="${safe(c.email||'')}"></label><label class="field full"><span>PASSWORT *</span><input id="wfPassword" type="password" autocomplete="current-password" placeholder="Dein Classy Passwort"></label></div>`;
    setDrawer(first?'Create your Classy profile':'Welcome back',`${classSummary(wizard.class)}<div class="spot-summary"><span>SELECTED SPOT</span><b>${safe(spotLabel(wizard.spot,wizard.class))}</b><button id="changeSpot" type="button">Ändern</button></div><div class="wizard-panel"><div class="wizard-kicker">${first?'FIRST CLASS':'RETURNING CLIENT'}</div><h4>${first?'Fast geschafft.':'Melde dich an.'}</h4><p>${first?'Wir benötigen die wichtigsten Profil- und Kontaktdaten für deine Buchung.':'Verwende dein Classy-Profil für diese Reservierung.'}</p>${form}<label class="wizard-check"><input id="wfTerms" type="checkbox" ${c.terms?'checked':''}><span>Ich akzeptiere AGB, Datenschutz und die Studio-/Cancellation-Rules. *</span></label>${first?'<label class="wizard-check optional"><input id="wfNews" type="checkbox" '+(c.news?'checked':'')+'><span>News, neue Classes und Studio-Updates per E-Mail erhalten.</span></label>':''}<div class="wizard-sticky-actions"><button class="drawer-action secondary" id="backSpot">Zurück</button><button class="drawer-action" id="goPayment">Weiter zur Zahlung</button></div></div>`,3);
    $('#changeSpot')?.addEventListener('click',renderSpotStep);$('#backSpot')?.addEventListener('click',renderSpotStep);$('#goPayment')?.addEventListener('click',saveDetails)
  }

  function saveDetails(){
    const first=wizard.mode==='first',email=$('#wfEmail')?.value.trim().toLowerCase()||'',password=$('#wfPassword')?.value||'';if(!emailOK(email)){showToast('E-Mail prüfen','Bitte gib eine gültige E-Mail-Adresse ein.');$('#wfEmail')?.focus();return}if(password.length<6){showToast('Passwort prüfen','Mindestens 6 Zeichen.');$('#wfPassword')?.focus();return}if(!$('#wfTerms')?.checked){showToast('Zustimmung fehlt','Bitte akzeptiere die Bedingungen.');return}
    const d={email,password,terms:true,news:!!$('#wfNews')?.checked};if(first){d.firstName=$('#wfFirst')?.value.trim()||'';d.lastName=$('#wfLast')?.value.trim()||'';d.phone=$('#wfPhone')?.value.trim()||'';d.birth=$('#wfBirth')?.value||'';d.emergency=$('#wfEmergency')?.value.trim()||'';if(d.firstName.length<2||d.lastName.length<2){showToast('Name fehlt','Vor- und Nachname werden benötigt.');return}if(!phoneOK(d.phone)){showToast('Mobilnummer prüfen','Bitte gib eine gültige Mobilnummer ein.');return}if(!d.birth){showToast('Geburtsdatum fehlt','Bitte gib dein Geburtsdatum ein.');return}}
    wizard.details=d;write('cpWizardCustomer',d);renderPaymentStep()
  }

  function renderPaymentStep(){
    setDrawer('Choose payment',`${classSummary(wizard.class)}<div class="checkout-mini-summary"><div><span>SPOT</span><b>${safe(spotLabel(wizard.spot,wizard.class))}</b></div><div><span>CLASS CREDIT</span><b>${wizard.mode==='first'?'28,00 €':'1 Credit'}</b></div></div><div class="wizard-panel"><div class="wizard-kicker">PAY YOUR WAY</div><h4>${wizard.mode==='first'?'Wähle deine Zahlungsart.':'Credit verwenden oder Zahlungsart wählen.'}</h4><p>Für die Präsentation wird der Zahlungsschritt simuliert. Auf dem Live-System werden dieselben Optionen mit den echten Provider-Accounts verarbeitet.</p><div class="wizard-payment-grid">${payMethods.map(m=>`<button type="button" class="wizard-pay ${wizard.payment===m.id?'active':''}" data-wpay="${m.id}"><span class="pay-mark">${safe(m.mark)}</span><span><b>${safe(m.name)}</b><small>${safe(m.detail)}</small></span><i>${wizard.payment===m.id?'✓':''}</i></button>`).join('')}</div><div class="demo-payment-note"><span>DEMO</span><p>Keine echte Belastung in dieser Präsentationsumgebung.</p></div><div class="wizard-sticky-actions"><button class="drawer-action secondary" id="backDetails">Zurück</button><button class="drawer-action" id="finishPayment">${wizard.mode==='first'?'Demo-Zahlung bestätigen':'Reservierung bestätigen'}</button></div></div>`,4);
    $$('[data-wpay]').forEach(b=>b.addEventListener('click',()=>{wizard.payment=b.dataset.wpay;renderPaymentStep()}));$('#backDetails')?.addEventListener('click',renderDetailsStep);$('#finishPayment')?.addEventListener('click',processPayment)
  }

  function processPayment(){const btn=$('#finishPayment');if(btn){btn.disabled=true;btn.innerHTML='<span class="button-spinner"></span> Zahlung wird bestätigt…'}setTimeout(()=>completeDemoBooking(),PRESENTATION_PAYMENT?1150:250)}
  function bookingRefV2(){return 'CP-'+(cryptoSafeToken?cryptoSafeToken(8):Math.random().toString(36).slice(2,10).toUpperCase())}
  function completeDemoBooking(){
    const r=wizard.class,ref=bookingRefV2(),email=wizard.details.email;const existing=read('cpBookings',[]);if(!existing.some(b=>b.classId===r.id&&String(b.email).toLowerCase()===email&&b.status!=='cancelled')){existing.unshift({ref,email,classId:r.id,name:r.name,time:r.time,date:r.date,studio:studioName(r),studioId:r.studio,coach:r.coach,spot:spotLabel(wizard.spot,r),spotNumber:wizard.spot,paymentMethod:wizard.payment,status:'reserved',paymentState:'demo_paid',createdAt:new Date().toISOString()});write('cpBookings',existing.slice(0,50));try{adjustSeats(r.id,-1)}catch(_){}}
    try{localStorage.setItem('cpLastEmail',email)}catch(_){ }renderSchedule();renderSuccess(ref)
  }
  function calendarHref(){const r=wizard.class;const start=new Date(`${r.date}T${r.time}:00`),end=new Date(start.getTime()+r.duration*60000),fmt=d=>d.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');const body=`BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nDTSTART:${fmt(start)}\nDTEND:${fmt(end)}\nSUMMARY:Classy Pilates – ${r.name}\nLOCATION:${studioName(r)}\nDESCRIPTION:Coach ${r.coach} · ${spotLabel(wizard.spot,r)}\nEND:VEVENT\nEND:VCALENDAR`;return'data:text/calendar;charset=utf-8,'+encodeURIComponent(body)}
  function renderSuccess(ref){const method=payMethods.find(x=>x.id===wizard.payment)?.name||wizard.payment;setDrawer('Booking confirmed',`<div class="booking-success-v2"><div class="success-orbit"><span>✓</span></div><p class="eyebrow">YOU'RE IN</p><h3>See you in class.</h3><p class="success-lead">Dein Platz ist reserviert und die Demo-Zahlung wurde erfolgreich bestätigt.</p>${classSummary(wizard.class)}<div class="success-grid"><div><span>SPOT</span><b>${safe(spotLabel(wizard.spot,wizard.class))}</b></div><div><span>PAYMENT</span><b>${safe(method)}</b></div><div><span>BOOKING</span><b>${safe(ref)}</b></div></div><div class="demo-payment-note success"><span>DEMO SUCCESS</span><p>Auf Production erfolgt die Bestätigung erst nach erfolgreicher Provider-Autorisierung.</p></div><div class="success-actions"><a class="drawer-action" href="${calendarHref()}" download="classy-pilates.ics">Zum Kalender hinzufügen</a><button class="drawer-action secondary" id="doneV2">Fertig</button></div></div>`,5);$('#doneV2')?.addEventListener('click',closeDrawer)}

  const originalOpenClass=typeof openClass==='function'?openClass:null;
  if(originalOpenClass){openClass=function(r){if(!r)return;if(Number(r.spots)<=0)return originalOpenClass(r);startWizard(r)}}

  moveStudiosBeforeSchedule();addQuickDock();observeDynamicUi();
})();