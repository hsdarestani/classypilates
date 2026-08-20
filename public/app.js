const studios=[
{id:'bhf1',name:'Bahnhofsviertel · 1. OG',short:'Bahnhofsviertel 1F',address:'Kaiserstraße 61 · 60329 Frankfurt',type:'Reformer',image:'https://classypilates.de/wp-content/uploads/2026/05/Bahnhofviertel_01-scaled.jpg'},
{id:'ladies',name:'Bahnhofsviertel · Ladies',short:'Ladies 2F',address:'Kaiserstraße 61 · 60329 Frankfurt',type:'Reformer · Ladies only',image:'https://classypilates.de/wp-content/uploads/2026/05/Ladies_02-scaled.jpg'},
{id:'sachsen',name:'Sachsenhausen',short:'Sachsenhausen',address:'Zum Gipfelhof 5 · 60594 Frankfurt',type:'Reformer · Mat',image:'https://classypilates.de/wp-content/uploads/2026/06/IMG_2751-scaled.jpeg'},
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

const $=s=>document.querySelector(s); const $$=s=>[...document.querySelectorAll(s)];
const state={dateOffset:0,selectedDay:0,location:'all',classType:'all',time:'all',mode:'returning',selectedClass:null};
const dayNames=['SO','MO','DI','MI','DO','FR','SA'];
const monthNames=['JAN','FEB','MÄR','APR','MAI','JUN','JUL','AUG','SEP','OKT','NOV','DEZ'];

function dateAt(index){const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+state.dateOffset+index);return d}
function isoDate(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function seedFor(str){let h=2166136261;for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619)}return Math.abs(h)}
function studioById(id){return studios.find(s=>s.id===id)}
function formatFullDate(d){return new Intl.DateTimeFormat('de-DE',{weekday:'long',day:'2-digit',month:'long'}).format(d)}

function renderLocations(){
  const sel=$('#locationFilter');
  sel.innerHTML='<option value="all">Alle 6 Studios</option>'+studios.map(s=>`<option value="${s.id}">${s.name}</option>`).join('');
}
function renderStudios(){
  $('#studioGrid').innerHTML=studios.map((s,i)=>`<article class="studio-card" data-studio="${s.id}"><div class="studio-photo" style="background-image:url('${s.image}')"></div><span class="studio-arrow">↗</span><div class="studio-info"><span>0${i+1} · ${s.type}</span><h3>${s.name}</h3><p>${s.address}</p></div></article>`).join('');
  $$('.studio-card').forEach(card=>card.addEventListener('click',()=>{state.location=card.dataset.studio;$('#locationFilter').value=state.location;renderSchedule();$('#schedule').scrollIntoView({behavior:'smooth'})}));
}
function renderDates(){
  const strip=$('#dateStrip');
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
      const cap=studio.id==='ladies'?8:10;let spots=(seed+ti*13+si*5)% (cap+2);if(spots>cap)spots=0;
      rows.push({id:`${dateKey}-${studio.id}-${time.replace(':','')}`,date:dateKey,dateObj:day,time,duration:50,studio:studio.id,type:ct[0],name:ct[1],coach:coaches[(seed+ti+si)%coaches.length],spots,capacity:cap});
    })
  });
  return rows.sort((a,b)=>a.time.localeCompare(b.time)||a.studio.localeCompare(b.studio));
}
function timeMatches(time,filter){const h=Number(time.split(':')[0]);if(filter==='morning')return h<12;if(filter==='afternoon')return h>=12&&h<17;if(filter==='evening')return h>=17;return true}
function renderSchedule(){
  const all=generateSchedule();
  const rows=all.filter(r=>(state.location==='all'||r.studio===state.location)&&(state.classType==='all'||r.type===state.classType)&&timeMatches(r.time,state.time));
  const date=dateAt(state.selectedDay);$('#resultsLabel').textContent=`${formatFullDate(date)} · ${rows.length} Classes`;
  const list=$('#classList');
  if(!rows.length){list.innerHTML='<div class="empty-state"><h4>Keine Classes für diese Filter.</h4><p>Ändere Studio, Class oder Uhrzeit — oder aktiviere eine Benachrichtigung.</p></div>';return}
  list.innerHTML=rows.map(r=>{const studio=studioById(r.studio);const availability=r.spots===0?{label:'Ausgebucht',cls:'full',btn:'Waitlist',bcls:'waitlist'}:r.spots<=3?{label:`Nur ${r.spots} Plätze`,cls:'low',btn:'Reserve',bcls:''}:{label:`${r.spots} Plätze`,cls:'',btn:'Reserve',bcls:''};return `<article class="class-row"><div class="class-time"><b>${r.time}</b><small>${r.duration} MIN</small></div><div class="class-name"><b>${r.name}</b><span>${r.type.toUpperCase()} · ALL LEVELS</span></div><div class="class-coach"><span>COACH</span><b>${r.coach}</b></div><div class="class-location"><span>STUDIO</span><b>${studio.short}</b></div><div class="reserve-wrap"><span class="spots ${availability.cls}">${availability.label}</span><button class="reserve-btn ${availability.bcls}" data-reserve="${r.id}" type="button">${availability.btn}</button></div></article>`}).join('');
  $$('[data-reserve]').forEach(btn=>btn.addEventListener('click',()=>openClass(all.find(r=>r.id===btn.dataset.reserve))));
}

function openDrawer(){ $('#drawerBackdrop').classList.add('open');$('#bookingDrawer').classList.add('open');$('#bookingDrawer').setAttribute('aria-hidden','false');document.body.style.overflow='hidden'}
function closeDrawer(){ $('#drawerBackdrop').classList.remove('open');$('#bookingDrawer').classList.remove('open');$('#bookingDrawer').setAttribute('aria-hidden','true');document.body.style.overflow=''}
function selectedSummary(r){const s=studioById(r.studio);return `<div class="selected-class"><div class="line"><span>Class</span><b>${r.name}</b></div><div class="line"><span>Wann</span><b>${formatFullDate(r.dateObj)} · ${r.time}</b></div><div class="line"><span>Studio</span><b>${s.name}</b></div><div class="line"><span>Coach</span><b>${r.coach}</b></div></div>`}
function openClass(r){
  state.selectedClass=r;const full=r.spots===0;$('#drawerTitle').textContent=full?'Join the waitlist':'Reserve your spot';
  if(full){$('#drawerBody').innerHTML=selectedSummary(r)+`<div class="drawer-step"><h4>Wir sagen dir sofort Bescheid.</h4><p>Sobald ein Platz frei wird, erhältst du eine Benachrichtigung. Die Warteliste selbst kostet keinen Credit.</p><label class="field"><span>E-MAIL</span><input id="waitEmail" type="email" autocomplete="email" placeholder="name@email.de"></label><button class="drawer-action" id="joinWaitlist" type="button">Warteliste aktivieren</button></div>`;openDrawer();$('#joinWaitlist').addEventListener('click',()=>{const email=$('#waitEmail').value.trim();if(!email||!email.includes('@')){showToast('E-Mail fehlt','Bitte gib eine gültige E-Mail-Adresse ein.');return}showToast('Warteliste aktiviert','Du wirst bei einem freien Platz benachrichtigt.');closeDrawer()});return}
  $('#drawerBody').innerHTML=selectedSummary(r)+`<div class="drawer-step"><h4>${state.mode==='first'?'Deine erste Class':'Welcome back.'}</h4><p>${state.mode==='first'?'Nur die wichtigsten Daten — dein Profil wird bei der Buchung erstellt.':'Buche mit deinem Classy-Profil. Für diesen Prototyp reicht deine E-Mail.'}</p><label class="field"><span>E-MAIL</span><input id="bookEmail" type="email" autocomplete="email" placeholder="name@email.de"></label>${state.mode==='first'?'<label class="field"><span>VORNAME</span><input id="bookName" type="text" autocomplete="given-name" placeholder="Dein Vorname"></label>':''}<div class="credit-box"><span>${state.mode==='first'?'First Class / Single Credit':'Verfügbarer Credit'}</span><b>${state.mode==='first'?'28 €':'1×'}</b></div><button class="drawer-action" id="continueBooking" type="button">${state.mode==='first'?'Weiter zur Bestätigung':'Platz reservieren'}</button><button class="drawer-action secondary" id="cancelBooking" type="button">Abbrechen</button></div>`;
  openDrawer();$('#cancelBooking').addEventListener('click',closeDrawer);$('#continueBooking').addEventListener('click',()=>confirmBooking(r));
}
function confirmBooking(r){
  const email=$('#bookEmail').value.trim();if(!email||!email.includes('@')){showToast('E-Mail fehlt','Bitte gib eine gültige E-Mail-Adresse ein.');return}
  const ref='CP-'+Math.random().toString(36).slice(2,8).toUpperCase();const booking={ref,email,classId:r.id,name:r.name,time:r.time,date:r.date,studio:studioById(r.studio).name,createdAt:new Date().toISOString()};
  const current=JSON.parse(localStorage.getItem('cpBookings')||'[]');if(!current.some(b=>b.classId===r.id&&b.email===email)){current.unshift(booking);localStorage.setItem('cpBookings',JSON.stringify(current.slice(0,12)))}
  $('#drawerTitle').textContent='Confirmed';$('#drawerBody').innerHTML=`<div class="confirmation"><div class="big-check">✓</div><h4>Dein Platz ist reserviert.</h4><p>Die Buchung wurde bestätigt. In der produktiven Version gehen Bestätigung und Kalender-Link automatisch per E-Mail raus.</p><div class="booking-id">BOOKING · ${ref}</div><button class="drawer-action" id="doneBooking" type="button">Fertig</button></div>`;$('#doneBooking').addEventListener('click',closeDrawer)
}
function renderMyBookings(){
  $('#drawerTitle').textContent='Meine Buchungen';const bookings=JSON.parse(localStorage.getItem('cpBookings')||'[]');
  $('#drawerBody').innerHTML=bookings.length?`<div class="drawer-step"><p>Deine lokal in diesem Demo gespeicherten Reservierungen.</p>${bookings.map(b=>`<div class="selected-class"><div class="line"><span>${b.date} · ${b.time}</span><b>${b.name}</b></div><div class="line"><span>Studio</span><b>${b.studio}</b></div><div class="line"><span>Booking</span><b>${b.ref}</b></div></div>`).join('')}</div>`:`<div class="confirmation"><div class="big-check" style="background:#d8d0c1;color:#151513">↗</div><h4>Noch keine Buchungen.</h4><p>Wähle eine Class im Schedule und reserviere deinen Platz.</p><button class="drawer-action" id="goSchedule" type="button">Schedule öffnen</button></div>`;
  openDrawer();const go=$('#goSchedule');if(go)go.addEventListener('click',()=>{closeDrawer();$('#schedule').scrollIntoView({behavior:'smooth'})})
}
function showToast(title,text){$('#toastTitle').textContent=title;$('#toastText').textContent=text;$('#toast').classList.add('show');clearTimeout(showToast.t);showToast.t=setTimeout(()=>$('#toast').classList.remove('show'),3200)}

function initEvents(){
  $('#locationFilter').addEventListener('change',e=>{state.location=e.target.value;renderSchedule()});
  $('#classFilter').addEventListener('change',e=>{state.classType=e.target.value;renderSchedule()});
  $('#timeFilter').addEventListener('change',e=>{state.time=e.target.value;renderSchedule()});
  $('#resetFilters').addEventListener('click',()=>{state.location='all';state.classType='all';state.time='all';$('#locationFilter').value='all';$('#classFilter').value='all';$('#timeFilter').value='all';renderSchedule()});
  $('#focusLocation').addEventListener('click',()=>$('#locationFilter').focus());
  $('#datePrev').addEventListener('click',()=>{state.dateOffset-=7;renderDates();renderSchedule()});$('#dateNext').addEventListener('click',()=>{state.dateOffset+=7;renderDates();renderSchedule()});
  $$('.booking-tab').forEach(btn=>btn.addEventListener('click',()=>{$$('.booking-tab').forEach(x=>x.classList.remove('active'));btn.classList.add('active');state.mode=btn.dataset.mode;showToast(state.mode==='first'?'First class mode':'Returning client','Der Buchungsflow wurde angepasst.')}));
  $$('[data-class-jump]').forEach(a=>a.addEventListener('click',()=>{state.classType=a.dataset.classJump;$('#classFilter').value=state.classType;renderSchedule()}));
  $$('[data-pass]').forEach(btn=>btn.addEventListener('click',()=>showToast('Pass selected',`${btn.dataset.pass} · Checkout wird im Backend angebunden.`)));
  $('#notifyBtn').addEventListener('click',()=>showToast('Benachrichtigungen','Im Live-System per E-Mail und optional Push.'));
  $('#openBookings').addEventListener('click',renderMyBookings);$('#openBookingsMobile').addEventListener('click',renderMyBookings);
  $('#drawerBackdrop').addEventListener('click',closeDrawer);$('#closeDrawer').addEventListener('click',closeDrawer);document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDrawer()});
  const menuBtn=$('#menuBtn'),menu=$('#mobileMenu');menuBtn.addEventListener('click',()=>{menu.classList.toggle('open');menu.setAttribute('aria-hidden',String(!menu.classList.contains('open')))});menu.querySelectorAll('a,button').forEach(x=>x.addEventListener('click',()=>menu.classList.remove('open')));
  window.addEventListener('scroll',()=>$('#header').classList.toggle('scrolled',window.scrollY>70),{passive:true});
}

renderLocations();renderStudios();renderDates();renderSchedule();initEvents();
