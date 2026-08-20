const studios=[
{id:'bhf1',name:'Bahnhofsviertel · 1. OG',short:'Bahnhofsviertel 1F',address:'Kaiserstraße 61 · 60329 Frankfurt',type:'Reformer',image:'https://classypilates.de/wp-content/uploads/2026/05/Bahnhofviertel_01-scaled.jpg'},
{id:'ladies',name:'Bahnhofsviertel · Ladies',short:'Ladies 2F',address:'Kaiserstraße 61 · 60329 Frankfurt',type:'Reformer · Ladies only',image:'https://classypilates.de/wp-content/uploads/2026/05/Ladies_02-scaled.jpg'},
{id:'sachsen',name:'Sachsenhausen',short:'Sachsenhausen',address:'Zum Gipelhof 5 · 60594 Frankfurt',type:'Reformer · Mat',image:'https://classypilates.de/wp-content/uploads/2026/06/IMG_2751-scaled.jpeg'},
{id:'bornheim',name:'Bornheim',short:'Bornheim',address:'Wiesenstraße 33 · 60385 Frankfurt',type:'Reformer',image:'https://classypilates.de/wp-content/uploads/2026/05/Bornheim_07-scaled.jpg'},
{id:'mid',name:'Mid',short:'Mid',address:'Große Eschenheimer Straße 45 · 60313 Frankfurt',type:'Powerformer',image:'https://classypilates.de/wp-content/uploads/2026/05/Mid_03-scaled.jpg'},
{id:'oval',name:'Oval',short:'Oval',address:'Baseler Straße 10 · 60329 Frankfurt',type:'Powerformer',image:'https://classypilates.de/wp-content/uploads/2026/05/Oval_01-scaled.jpg'}
];

const coaches=['Anna','Andrea','Christina','Gabriella','Ida','Jessi','Kimberley','Melina','Nathalie','Sani','Zora','Laetitia'];
const classTypes={
  bhf1:[['Reformer','Total Body'],['Reformer','Butt & Abs'],['Reformer','Total Body · Intense']],
  ladies:[['Reformer','Ladies · Total Body'],['Reformer','Ladies · Total Body Lower'],['Barre','Barre Flow']],
  sachsen:[['Reformer','Reformer · Full Body'],['Reformer','Reformer · Intense'],['Mat','Mat Pilates Flow']],
  bornheim:[['Reformer','Total Body · Level 1.0'],['Reformer','Butt & Abs'],['Reformer','Total Body · Intense']],
  mid:[['Powerformer','Powerformer · Total Body'],['Powerformer','Powerformer · Sculpt'],['Powerformer','Powerformer · Core']],
  oval:[['Powerformer','Powerformer · Total Body'],['Powerformer','Powerformer · Core'],['Powerformer','Powerformer · Lower Body']]
};
const timeSets=[['07:00','08:00','09:00','10:00','11:00','17:00','18:00','19:00','20:00'],['07:30','08:30','10:00','12:00','17:30','18:30','19:30'],['08:00','09:00','10:00','11:00','17:00','18:00','19:00','20:00']];
const PASSES={
  '1 Class · 28 €':{name:'1 Class',price:'28 €'},
  '5 Classes · 119 €':{name:'5 Classes',price:'119 €'},
  '10 Classes · 219 €':{name:'10 Classes',price:'219 €'},
  '20 Classes · 399 €':{name:'20 Classes',price:'399 €'}
};
const BUY_URL='https://classypilates.de/buy-classes/';

const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const state={dateOffset:0,selectedDay:0,location:'all',classType:'all',time:'all',mode:'returning',selectedClass:null};
const dayNames=['SO','MO','DI','MI','DO','FR','SA'];
const monthNames=['JAN','FEB','MÄR','APR','MAI','JUN','JUL','AUG','SEP','OKT','NOV','DEZ'];
const memoryStore={};

function safeGet(key,fallback='[]'){
  try{return localStorage.getItem(key)??fallback}catch(_){return memoryStore[key]??fallback}
}
function safeSet(key,value){
  try{localStorage.setItem(key,value)}catch(_){memoryStore[key]=value}
}
function readJson(key,fallback=[]){
  try{const v=JSON.parse(safeGet(key,JSON.stringify(fallback)));return Array.isArray(v)?v:fallback}catch(_){return fallback}
}
function writeJson(key,value){safeSet(key,JSON.stringify(value))}
function validEmail(email){return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)}
function esc(value){return String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]))}
function dateAt(index){const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+state.dateOffset+index);return d}
function isoDate(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function seedFor(str){let h=2166136261;for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619)}return Math.abs(h)}
function studioById(id){return studios.find(s=>s.id===id)}
function formatFullDate(d){return new Intl.DateTimeFormat('de-DE',{weekday:'long',day:'2-digit',month:'long'}).format(d)}
function bookingRef(){return 'CP-'+cryptoSafeToken(6)}
function cryptoSafeToken(len){
  const alphabet='ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  if(window.crypto?.getRandomValues){const a=new Uint8Array(len);crypto.getRandomValues(a);return [...a].map(v=>alphabet[v%alphabet.length]).join('')}
  return Math.random().toString(36).slice(2,2+len).toUpperCase()
}
function classSeatDelta(classId){
  const deltas=readJson('cpSeatDeltas',[]);
  return deltas.filter(x=>x.classId===classId).reduce((sum,x)=>sum+(Number(x.delta)||0),0)
}
function adjustSeats(classId,delta){
  const deltas=readJson('cpSeatDeltas',[]);
  deltas.push({classId,delta,at:new Date().toISOString()});
  writeJson('cpSeatDeltas',deltas.slice(-200));
}

function renderLocations(){
  const sel=$('#locationFilter'); if(!sel)return;
  sel.innerHTML='<option value="all">Alle 6 Studios</option>'+studios.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join('');
}
function renderStudios(){
  const grid=$('#studioGrid'); if(!grid)return;
  grid.innerHTML=studios.map((s,i)=>`<article class="studio-card" data-studio="${s.id}" tabindex="0" role="button" aria-label="Schedule für ${esc(s.name)} öffnen"><div class="studio-photo" style="background-image:url('${s.image}')"></div><span class="studio-arrow">↗</span><div class="studio-info"><span>0${i+1} · ${esc(s.type)}</span><h3>${esc(s.name)}</h3><p>${esc(s.address)}</p></div></article>`).join('');
  $$('.studio-card').forEach(card=>{
    const open=()=>{state.location=card.dataset.studio;$('#locationFilter').value=state.location;renderSchedule();$('#schedule').scrollIntoView({behavior:'smooth'})};
    card.addEventListener('click',open);card.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}})
  });
}
function renderDates(){
  const strip=$('#dateStrip'); if(!strip)return;
  strip.innerHTML=Array.from({length:7},(_,i)=>{const d=dateAt(i);const today=isoDate(d)===isoDate(new Date());return `<button class="date-btn ${i===state.selectedDay?'active':''}" type="button" data-day="${i}"><span class="dow">${today?'HEUTE':dayNames[d.getDay()]}</span><b>${String(d.getDate()).padStart(2,'0')}</b><small>${monthNames[d.getMonth()]}</small></button>`}).join('');
  $$('.date-btn').forEach(btn=>btn.addEventListener('click',()=>{state.selectedDay=Number(btn.dataset.day);renderDates();renderSchedule()}));
}
function generateSchedule(){
  const day=dateAt(state.selectedDay);const dateKey=isoDate(day);const rows=[];
  studios.forEach((studio,si)=>{
    const seed=seedFor(dateKey+studio.id);const times=timeSets[seed%timeSets.length];const baseClasses=classTypes[studio.id];
    times.forEach((time,ti)=>{
      if((seed+ti*7)%5===0&&ti%2===0)return;
      const ct=baseClasses[(seed+ti)%baseClasses.length];
      const cap=studio.id==='ladies'?8:10;
      let baseSpots=(seed+ti*13+si*5)%(cap+2); if(baseSpots>cap)baseSpots=0;
      const id=`${dateKey}-${studio.id}-${time.replace(':','')}`;
      const spots=Math.max(0,Math.min(cap,baseSpots+classSeatDelta(id)));
      rows.push({id,date:dateKey,dateObj:new Date(day),time,duration:50,studio:studio.id,type:ct[0],name:ct[1],coach:coaches[(seed+ti+si)%coaches.length],spots,capacity:cap});
    })
  });
  return rows.sort((a,b)=>a.time.localeCompare(b.time)||a.studio.localeCompare(b.studio));
}
function timeMatches(time,filter){const h=Number(time.split(':')[0]);if(filter==='morning')return h<12;if(filter==='afternoon')return h>=12&&h<17;if(filter==='evening')return h>=17;return true}
function renderSchedule(){
  const all=generateSchedule();
  const rows=all.filter(r=>(state.location==='all'||r.studio===state.location)&&(state.classType==='all'||r.type===state.classType)&&timeMatches(r.time,state.time));
  const date=dateAt(state.selectedDay);if($('#resultsLabel'))$('#resultsLabel').textContent=`${formatFullDate(date)} · ${rows.length} Classes`;
  const list=$('#classList'); if(!list)return;
  if(!rows.length){list.innerHTML='<div class="empty-state"><h4>Keine Classes für diese Filter.</h4><p>Ändere Studio, Class oder Uhrzeit — oder aktiviere eine Benachrichtigung.</p></div>';return}
  list.innerHTML=rows.map(r=>{
    const studio=studioById(r.studio);
    const availability=r.spots===0?{label:'Ausgebucht',cls:'full',btn:'Waitlist',bcls:'waitlist'}:r.spots<=3?{label:`Nur ${r.spots} Plätze`,cls:'low',btn:'Reserve',bcls:''}:{label:`${r.spots} Plätze`,cls:'',btn:'Reserve',bcls:''};
    return `<article class="class-row"><div class="class-time"><b>${r.time}</b><small>${r.duration} MIN</small></div><div class="class-name"><b>${esc(r.name)}</b><span>${esc(r.type.toUpperCase())} · ALL LEVELS</span></div><div class="class-coach"><span>COACH</span><b>${esc(r.coach)}</b></div><div class="class-location"><span>STUDIO</span><b>${esc(studio.short)}</b></div><div class="reserve-wrap"><span class="spots ${availability.cls}">${availability.label}</span><button class="reserve-btn ${availability.bcls}" data-reserve="${r.id}" type="button">${availability.btn}</button></div></article>`
  }).join('');
  $$('[data-reserve]').forEach(btn=>btn.addEventListener('click',()=>{const item=all.find(r=>r.id===btn.dataset.reserve);if(item)openClass(item)}));
}

function openDrawer(){
  $('#drawerBackdrop')?.classList.add('open');$('#bookingDrawer')?.classList.add('open');$('#bookingDrawer')?.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
}
function closeDrawer(){
  $('#drawerBackdrop')?.classList.remove('open');$('#bookingDrawer')?.classList.remove('open');$('#bookingDrawer')?.setAttribute('aria-hidden','true');document.body.style.overflow='';
}
function selectedSummary(r){const s=studioById(r.studio);return `<div class="selected-class"><div class="line"><span>Class</span><b>${esc(r.name)}</b></div><div class="line"><span>Wann</span><b>${esc(formatFullDate(r.dateObj))} · ${r.time}</b></div><div class="line"><span>Studio</span><b>${esc(s.name)}</b></div><div class="line"><span>Coach</span><b>${esc(r.coach)}</b></div></div>`}
function openClass(r){
  state.selectedClass=r;const full=r.spots===0;$('#drawerTitle').textContent=full?'Join the waitlist':'Reserve your spot';
  if(full){
    $('#drawerBody').innerHTML=selectedSummary(r)+`<div class="drawer-step"><h4>Wir sagen dir Bescheid, wenn etwas frei wird.</h4><p>Trage deine E-Mail ein. Du kannst die Warteliste jederzeit unter „Meine Buchungen“ wieder entfernen.</p><label class="field"><span>E-MAIL</span><input id="waitEmail" type="email" autocomplete="email" placeholder="name@email.de"></label><button class="drawer-action" id="joinWaitlist" type="button">Warteliste aktivieren</button><button class="drawer-action secondary" id="cancelBooking" type="button">Abbrechen</button></div>`;
    openDrawer();$('#cancelBooking')?.addEventListener('click',closeDrawer);$('#joinWaitlist')?.addEventListener('click',()=>joinWaitlist(r));return;
  }
  $('#drawerBody').innerHTML=selectedSummary(r)+`<div class="drawer-step"><h4>${state.mode==='first'?'Deine erste Class':'Welcome back.'}</h4><p>${state.mode==='first'?'Vorname und E-Mail reichen für diese Reservierung.':'Gib die E-Mail deines Classy-Profils ein.'}</p><label class="field"><span>E-MAIL</span><input id="bookEmail" type="email" autocomplete="email" placeholder="name@email.de"></label>${state.mode==='first'?'<label class="field"><span>VORNAME</span><input id="bookName" type="text" autocomplete="given-name" placeholder="Dein Vorname"></label>':''}<div class="credit-box"><span>${state.mode==='first'?'Single Class':'Reservierung'}</span><b>${state.mode==='first'?'28 €':'1 Platz'}</b></div><button class="drawer-action" id="continueBooking" type="button">Platz reservieren</button><button class="drawer-action secondary" id="cancelBooking" type="button">Abbrechen</button></div>`;
  openDrawer();$('#cancelBooking')?.addEventListener('click',closeDrawer);$('#continueBooking')?.addEventListener('click',()=>confirmBooking(r));
}
function joinWaitlist(r){
  const input=$('#waitEmail');const email=input?.value.trim().toLowerCase()||'';
  if(!validEmail(email)){showToast('E-Mail prüfen','Bitte gib eine gültige E-Mail-Adresse ein.');input?.focus();return}
  const list=readJson('cpWaitlist',[]);
  if(list.some(x=>x.classId===r.id&&x.email===email)){showToast('Bereits eingetragen','Diese E-Mail steht schon auf der Warteliste.');return}
  list.unshift({id:'W-'+cryptoSafeToken(7),classId:r.id,email,name:r.name,time:r.time,date:r.date,studio:studioById(r.studio).name,createdAt:new Date().toISOString()});writeJson('cpWaitlist',list.slice(0,50));
  closeDrawer();showToast('Warteliste gespeichert','Der Eintrag ist unter „Meine Buchungen“ sichtbar.');
}
function confirmBooking(r){
  const emailInput=$('#bookEmail');const email=emailInput?.value.trim().toLowerCase()||'';
  if(!validEmail(email)){showToast('E-Mail prüfen','Bitte gib eine gültige E-Mail-Adresse ein.');emailInput?.focus();return}
  if(state.mode==='first'){const name=$('#bookName')?.value.trim()||'';if(name.length<2){showToast('Vorname fehlt','Bitte gib deinen Vornamen ein.');$('#bookName')?.focus();return}}
  const refreshed=generateSchedule().find(x=>x.id===r.id);
  if(!refreshed||refreshed.spots<=0){showToast('Gerade ausgebucht','Der letzte Platz ist nicht mehr verfügbar.');closeDrawer();renderSchedule();return}
  const current=readJson('cpBookings',[]);
  const existing=current.find(b=>b.classId===r.id&&b.email===email&&b.status!=='cancelled');
  if(existing){showToast('Schon reserviert',`Booking ${existing.ref} ist bereits gespeichert.`);return}
  const ref=bookingRef();
  const booking={ref,email,classId:r.id,name:r.name,time:r.time,date:r.date,studio:studioById(r.studio).name,studioId:r.studio,coach:r.coach,status:'reserved',createdAt:new Date().toISOString()};
  current.unshift(booking);writeJson('cpBookings',current.slice(0,50));adjustSeats(r.id,-1);renderSchedule();
  $('#drawerTitle').textContent='Reservierung gespeichert';
  $('#drawerBody').innerHTML=`<div class="confirmation"><div class="big-check">✓</div><h4>Dein Platz ist vorgemerkt.</h4><p>Booking <b>${ref}</b> wurde auf diesem Gerät gespeichert. Für den finalen Livebetrieb wird diese Aktion serverseitig bestätigt und synchronisiert.</p><div class="booking-id">BOOKING · ${ref}</div><button class="drawer-action" id="doneBooking" type="button">Fertig</button></div>`;
  $('#doneBooking')?.addEventListener('click',closeDrawer);
}
function cancelBooking(ref){
  const bookings=readJson('cpBookings',[]);const booking=bookings.find(b=>b.ref===ref&&b.status!=='cancelled');if(!booking)return;
  booking.status='cancelled';booking.cancelledAt=new Date().toISOString();writeJson('cpBookings',bookings);adjustSeats(booking.classId,+1);renderSchedule();showToast('Buchung storniert',`${ref} wurde storniert.`);renderMyBookings();
}
function removeWaitlist(id){
  const list=readJson('cpWaitlist',[]);writeJson('cpWaitlist',list.filter(x=>x.id!==id));showToast('Warteliste entfernt','Der Eintrag wurde gelöscht.');renderMyBookings();
}
function renderMyBookings(){
  $('#drawerTitle').textContent='Meine Buchungen';
  const bookings=readJson('cpBookings',[]).filter(b=>b.status!=='cancelled');const waitlist=readJson('cpWaitlist',[]);
  const bookingHtml=bookings.map(b=>`<div class="selected-class"><div class="line"><span>${esc(b.date)} · ${esc(b.time)}</span><b>${esc(b.name)}</b></div><div class="line"><span>Studio</span><b>${esc(b.studio)}</b></div><div class="line"><span>Booking</span><b>${esc(b.ref)}</b></div><button class="drawer-action secondary" data-cancel-ref="${esc(b.ref)}" type="button">Buchung stornieren</button></div>`).join('');
  const waitHtml=waitlist.map(w=>`<div class="selected-class"><div class="line"><span>Warteliste · ${esc(w.date)} · ${esc(w.time)}</span><b>${esc(w.name)}</b></div><div class="line"><span>Studio</span><b>${esc(w.studio)}</b></div><button class="drawer-action secondary" data-wait-remove="${esc(w.id)}" type="button">Warteliste verlassen</button></div>`).join('');
  $('#drawerBody').innerHTML=(bookingHtml||waitHtml)?`<div class="drawer-step"><p>Reservierungen und Wartelisten auf diesem Gerät.</p>${bookingHtml}${waitHtml}</div>`:`<div class="confirmation"><div class="big-check" style="background:#d8d0c1;color:#151513">↗</div><h4>Noch keine Buchungen.</h4><p>Wähle eine Class im Schedule und reserviere deinen Platz.</p><button class="drawer-action" id="goSchedule" type="button">Schedule öffnen</button></div>`;
  openDrawer();$('#goSchedule')?.addEventListener('click',()=>{closeDrawer();$('#schedule').scrollIntoView({behavior:'smooth'})});$$('[data-cancel-ref]').forEach(btn=>btn.addEventListener('click',()=>cancelBooking(btn.dataset.cancelRef)));$$('[data-wait-remove]').forEach(btn=>btn.addEventListener('click',()=>removeWaitlist(btn.dataset.waitRemove)));
}
function openNotify(){
  const d=dateAt(state.selectedDay);const studio=state.location==='all'?'Alle Studios':studioById(state.location)?.name||'Alle Studios';const cls=state.classType==='all'?'Alle Classes':state.classType;
  $('#drawerTitle').textContent='Freie Plätze';
  $('#drawerBody').innerHTML=`<div class="drawer-step"><h4>Benachrichtigung speichern</h4><p>${esc(formatFullDate(d))} · ${esc(studio)} · ${esc(cls)}</p><label class="field"><span>E-MAIL</span><input id="notifyEmail" type="email" autocomplete="email" placeholder="name@email.de"></label><button class="drawer-action" id="saveNotify" type="button">Benachrichtigung aktivieren</button><button class="drawer-action secondary" id="cancelNotify" type="button">Abbrechen</button></div>`;
  openDrawer();$('#cancelNotify')?.addEventListener('click',closeDrawer);$('#saveNotify')?.addEventListener('click',()=>{
    const email=$('#notifyEmail')?.value.trim().toLowerCase()||'';if(!validEmail(email)){showToast('E-Mail prüfen','Bitte gib eine gültige E-Mail-Adresse ein.');return}
    const notices=readJson('cpNotices',[]);const key=`${isoDate(d)}|${state.location}|${state.classType}|${state.time}|${email}`;
    if(!notices.some(n=>n.key===key))notices.unshift({key,email,date:isoDate(d),location:state.location,classType:state.classType,time:state.time,createdAt:new Date().toISOString()});writeJson('cpNotices',notices.slice(0,50));closeDrawer();showToast('Benachrichtigung gespeichert','Deine Auswahl wurde gespeichert.');
  });
}
function openPass(passKey){
  const pass=PASSES[passKey];if(!pass){window.open(BUY_URL,'_blank','noopener');return}
  $('#drawerTitle').textContent='Class Pass';
  $('#drawerBody').innerHTML=`<div class="drawer-step"><h4>${esc(pass.name)}</h4><div class="credit-box"><span>Preis</span><b>${esc(pass.price)}</b></div><p>Der Kauf läuft aktuell über die bestehende Classy-Pilates-Verkaufsseite, damit Zahlungen während der Umstellung nicht unterbrochen werden.</p><button class="drawer-action" id="buyPass" type="button">Sicher weiter zum Kauf ↗</button><button class="drawer-action secondary" id="cancelPass" type="button">Abbrechen</button></div>`;
  openDrawer();$('#cancelPass')?.addEventListener('click',closeDrawer);$('#buyPass')?.addEventListener('click',()=>{window.open(BUY_URL,'_blank','noopener');closeDrawer()});
}
function showToast(title,text){
  if(!$('#toast'))return;$('#toastTitle').textContent=title;$('#toastText').textContent=text;$('#toast').classList.add('show');clearTimeout(showToast.t);showToast.t=setTimeout(()=>$('#toast').classList.remove('show'),3200)
}
function initEvents(){
  $('#locationFilter')?.addEventListener('change',e=>{state.location=e.target.value;renderSchedule()});
  $('#classFilter')?.addEventListener('change',e=>{state.classType=e.target.value;renderSchedule()});
  $('#timeFilter')?.addEventListener('change',e=>{state.time=e.target.value;renderSchedule()});
  $('#resetFilters')?.addEventListener('click',()=>{state.location='all';state.classType='all';state.time='all';$('#locationFilter').value='all';$('#classFilter').value='all';$('#timeFilter').value='all';renderSchedule()});
  $('#focusLocation')?.addEventListener('click',()=>$('#locationFilter')?.focus());
  $('#datePrev')?.addEventListener('click',()=>{state.dateOffset-=7;renderDates();renderSchedule()});
  $('#dateNext')?.addEventListener('click',()=>{state.dateOffset+=7;renderDates();renderSchedule()});
  $$('.booking-tab').forEach(btn=>btn.addEventListener('click',()=>{$$('.booking-tab').forEach(x=>x.classList.remove('active'));btn.classList.add('active');state.mode=btn.dataset.mode;showToast(state.mode==='first'?'First class':'Returning client',state.mode==='first'?'Flow für neue Kundinnen und Kunden aktiv.':'Flow für bestehende Kundinnen und Kunden aktiv.')}));
  $$('[data-class-jump]').forEach(a=>a.addEventListener('click',()=>{state.classType=a.dataset.classJump;$('#classFilter').value=state.classType;renderSchedule()}));
  $$('[data-pass]').forEach(btn=>btn.addEventListener('click',()=>openPass(btn.dataset.pass)));
  $('#notifyBtn')?.addEventListener('click',openNotify);
  $('#openBookings')?.addEventListener('click',renderMyBookings);$('#openBookingsMobile')?.addEventListener('click',renderMyBookings);
  $('#drawerBackdrop')?.addEventListener('click',closeDrawer);$('#closeDrawer')?.addEventListener('click',closeDrawer);document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDrawer()});
  const menuBtn=$('#menuBtn'),menu=$('#mobileMenu');if(menuBtn&&menu){menuBtn.addEventListener('click',()=>{menu.classList.toggle('open');menu.setAttribute('aria-hidden',String(!menu.classList.contains('open')))});menu.querySelectorAll('a,button').forEach(x=>x.addEventListener('click',()=>{menu.classList.remove('open');menu.setAttribute('aria-hidden','true')}))}
  window.addEventListener('scroll',()=>$('#header')?.classList.toggle('scrolled',window.scrollY>70),{passive:true});
}

renderLocations();renderStudios();renderDates();renderSchedule();initEvents();
