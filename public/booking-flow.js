(()=>{
  const $=(s,c=document)=>c.querySelector(s);const $$=(s,c=document)=>[...c.querySelectorAll(s)];
  const PHONE='+4951328533996';
  const INSTAGRAM='https://www.instagram.com/classypilates.de/';
  const SPOT_SELECTION_ENABLED=false;
  const coachPhotos={};
  const photoFor=name=>{const initials=String(name||'CP').split(/\s+/).map(part=>part[0]||'').join('').slice(0,2).toUpperCase();const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#24231f"/><stop offset="1" stop-color="#b89f79"/></linearGradient></defs><rect width="180" height="180" fill="url(#g)"/><text x="90" y="108" text-anchor="middle" font-family="Arial,sans-serif" font-size="58" fill="white">${initials}</text></svg>`;return coachPhotos[name]||`data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`};
  const read=(k,f)=>{try{return JSON.parse(localStorage.getItem(k))??f}catch(_){return f}};
  const write=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(_){}};
  const safe=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const plainText=value=>{const el=document.createElement('div');el.innerHTML=String(value??'');return (el.textContent||el.innerText||'').replace(/\s+/g,' ').trim()};
  async function timedFetch(input,opt={},timeout=15000){const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeout);try{return await fetch(input,{...opt,signal:controller.signal})}catch(error){if(error?.name==='AbortError')throw new Error('request_timeout');throw error}finally{clearTimeout(timer)}}
  const emailOK=v=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  const phoneOK=v=>String(v||'').replace(/\D/g,'').length>=7;
  const payMethods=[
    {id:'sumup',name:'Secure checkout',detail:'Pay securely with SumUp',mark:'SumUp'}
  ];
  let wizard=null;

  function moveStudiosBeforeSchedule(){const studiosSection=$('#studios'),schedule=$('#schedule');if(studiosSection&&schedule&&schedule.parentNode)schedule.parentNode.insertBefore(studiosSection,schedule)}

  function addQuickDock(){if($('.classy-quick-dock'))return;const dock=document.createElement('nav');dock.className='classy-quick-dock';dock.setAttribute('aria-label','Quick actions');dock.innerHTML=`<a href="tel:${PHONE}" aria-label="Call Classy Pilates"><span class="dock-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.6 3.5 9 8l-2 1.5c1.2 2.7 3.3 4.8 6 6l1.5-2 4.5 2.4-.8 3c-.2.8-.9 1.3-1.7 1.3C9.4 20 3.8 14.6 3.8 7.5c0-.8.5-1.5 1.3-1.7l1.5-.4Z"/></svg></span><b>Call</b></a><a href="#schedule" aria-label="Book a class"><span class="dock-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg></span><b>Book</b></a><a href="${INSTAGRAM}" target="_blank" rel="noopener" aria-label="Open Instagram"><span class="dock-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg></span><b>Instagram</b></a>`;document.body.appendChild(dock)}

  function studioActions(){
    $$('.studio-card').forEach(card=>{if($('.studio-hover-actions',card))return;const wrap=document.createElement('div');wrap.className='studio-hover-actions';wrap.innerHTML=`<a href="tel:${PHONE}" data-no-studio-click aria-label="Call"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.6 3.5 9 8l-2 1.5c1.2 2.7 3.3 4.8 6 6l1.5-2 4.5 2.4-.8 3c-.2.8-.9 1.3-1.7 1.3C9.4 20 3.8 14.6 3.8 7.5c0-.8.5-1.5 1.3-1.7l1.5-.4Z"/></svg><span>Call</span></a><button type="button" data-studio-book><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg><span>Book</span></button><a href="${INSTAGRAM}" target="_blank" rel="noopener" data-no-studio-click aria-label="Instagram"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg><span>Instagram</span></a>`;card.appendChild(wrap);wrap.addEventListener('click',e=>e.stopPropagation());$('[data-studio-book]',wrap)?.addEventListener('click',e=>{e.stopPropagation();state.location=card.dataset.studio;const filter=$('#locationFilter');if(filter)filter.value=state.location;renderSchedule();$('#schedule')?.scrollIntoView({behavior:'smooth',block:'start'})})})
  }

  function coachAvatars(){
    $$('.class-row').forEach(row=>{const coach=$('.class-coach',row);if(!coach)return;const name=$('b',coach)?.textContent.trim()||'Coach',src=photoFor(name);let img=$('.coach-avatar',coach);if(!img){img=document.createElement('img');img.className='coach-avatar';img.alt=`Coach ${name}`;img.loading='lazy';coach.prepend(img)}if(img.getAttribute('src')!==src)img.src=src})
  }

  async function loadCoachPhotos(){try{const response=await fetch('/api/public/coaches',{credentials:'same-origin',cache:'no-store'});if(!response.ok)return;const data=await response.json();(data.coaches||[]).forEach(coach=>{if(coach.display_name&&coach.photo_url)coachPhotos[coach.display_name]=coach.photo_url});coachAvatars()}catch(_){}}

  function observeDynamicUi(){const list=$('#classList'),grid=$('#studioGrid');if(list){coachAvatars();new MutationObserver(()=>coachAvatars()).observe(list,{childList:true,subtree:true})}if(grid){studioActions();new MutationObserver(()=>studioActions()).observe(grid,{childList:true,subtree:true})}}

  function studioName(r){return studioById(r.studio)?.name||r.studio}
  function classSummary(r){const description=plainText(r.description);return `<div class="wizard-class-card"><img src="${photoFor(r.coach)}" alt="Coach ${safe(r.coach)}"><div><span>${safe(r.type)} · ${r.duration} MIN</span><h4>${safe(r.name)}</h4>${description?`<p>${safe(description)}</p>`:''}<p>${safe(formatFullDate(r.dateObj))} · ${r.time}<br>${safe(studioName(r))}</p></div><div class="coach-chip"><small>COACH</small><b>${safe(r.coach)}</b><em>Selected</em></div></div>`}
  function setProgress(step){const labels=SPOT_SELECTION_ENABLED?['Class','Spot','Details','Payment','Done']:['Class','Details','Payment','Done'];const visibleStep=SPOT_SELECTION_ENABLED?step:step===1?1:step===3?2:step===4?3:4;const progress=labels.map((x,i)=>`<span class="${i+1<=visibleStep?'done':''} ${i+1===visibleStep?'active':''}"><i>${i+1<visibleStep?'✓':i+1}</i><b>${x}</b></span>`).join('');return `<div class="booking-progress-v2">${progress}</div>`}
  function setDrawer(title,html,step){
    $('#drawerTitle').textContent=title;
    $('#drawerBody').innerHTML=setProgress(step)+html;
    const drawer=$('#bookingDrawer');
    drawer?.classList.add('booking-v2');
    openDrawer();
    if(drawer)requestAnimationFrame(()=>{drawer.scrollTop=0});
  }
  function customerDraft(){const value=read('cpWizardCustomer',{});if(!value||typeof value!=='object')return{};const {password,...draft}=value;if(password)write('cpWizardCustomer',draft);return draft}

  function startWizard(r){wizard={class:r,spot:null,payment:'sumup',paymentChoiceMade:false,credits:null,details:customerDraft(),mode:state.mode==='first'?'register':'login',authUser:null,sessionChecked:false};renderClassStep()}
  function renderClassStep(){const r=wizard.class;const available=Math.max(0,Number(r.spots)||0);const nextCopy=SPOT_SELECTION_ENABLED?'Review the coach, studio and time. Next, choose your preferred spot in the studio.':'Review the coach, studio and time. Your place will be assigned automatically while Mindbody sync is active.';const nextLabel=SPOT_SELECTION_ENABLED?'Continue · Choose spot':'Continue · Details';setDrawer('Reserve your class',`${classSummary(r)}<div class="wizard-panel"><div class="wizard-kicker">YOUR SESSION</div><h4>Your class is selected.</h4><p>${nextCopy}</p><div class="class-facts"><div><span>LEVEL</span><b>All Levels</b></div><div><span>AVAILABLE</span><b>${available} spots</b></div><div><span>ARRIVE</span><b>10 min early</b></div></div><button class="drawer-action" id="goSpot">${nextLabel}</button><button class="drawer-action secondary" id="cancelV2">Cancel</button></div>`,1);$('#goSpot')?.addEventListener('click',()=>SPOT_SELECTION_ENABLED?renderSpotStep():prepareDetailsStep());$('#cancelV2')?.addEventListener('click',closeDrawer)}

  function seatState(index,r){const occupied=Math.min(Number(r.capacity)||0,Math.max(0,Number(r.reserved)||0));if(index<=occupied)return'taken';if(index===Math.min((Number(r.capacity)||1),occupied+1))return'recommended';return'available'}
  function spotLabel(i,r){if(r.type==='Mat')return`Mat ${String(i).padStart(2,'0')}`;if(r.type==='Barre')return`Position ${String(i).padStart(2,'0')}`;return`Reformer ${String(i).padStart(2,'0')}`}
  function renderSpotStep(){
    const r=wizard.class;const cap=Math.max(6,Number(r.capacity)||10);const seats=Array.from({length:cap},(_,x)=>x+1).map(i=>{const st=seatState(i,r),selected=wizard.spot===i;return `<button type="button" class="studio-spot ${st} ${selected?'selected':''}" data-spot="${i}" ${st==='taken'?'disabled':''} aria-label="${spotLabel(i,r)} ${st==='taken'?'taken':'available'}"><span class="spot-bed"><i></i></span><b>${String(i).padStart(2,'0')}</b>${st==='recommended'?'<small>BEST</small>':''}</button>`}).join('');
    setDrawer('Choose your spot',`${classSummary(r)}<div class="studio-map"><div class="studio-map-top"><span>MIRROR WALL</span><div class="coach-station"><img src="${photoFor(r.coach)}" alt="${safe(r.coach)}"><b>${safe(r.coach)}</b><small>COACH</small></div></div><div class="studio-floor"><div class="floor-glow"></div><div class="spot-grid ${r.type==='Mat'||r.type==='Barre'?'mat-layout':''}">${seats}</div><div class="floor-entry">ENTRANCE</div></div><div class="spot-legend"><span><i class="available"></i>Available</span><span><i class="recommended"></i>Recommended</span><span><i class="taken"></i>Taken</span><span><i class="selected"></i>Selected</span></div></div><div class="wizard-sticky-actions"><button class="drawer-action secondary" id="backClass">Back</button><button class="drawer-action" id="goDetails" ${wizard.spot?'':'disabled'}>${wizard.spot?`${spotLabel(wizard.spot,r)} · Continue`:'Choose your spot'}</button></div>`,2);
    $$('[data-spot]').forEach(btn=>btn.addEventListener('click',()=>{wizard.spot=Number(btn.dataset.spot);renderSpotStep()}));$('#backClass')?.addEventListener('click',renderClassStep);$('#goDetails')?.addEventListener('click',()=>wizard.spot&&prepareDetailsStep())
  }

  async function prepareDetailsStep(){
    if(!wizard.sessionChecked){wizard.sessionChecked=true;try{const response=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});if(response.ok){const user=await response.json();if(user.portal==='/account'){wizard.authUser=user;wizard.mode='authenticated';let profile={};try{const profileResponse=await fetch('/api/customer/profile',{credentials:'same-origin',cache:'no-store'});if(profileResponse.ok)profile=await profileResponse.json()}catch(_){}const saved=wizard.details||{};wizard.credits=Math.max(0,Number(profile.credits)||0);wizard.details={...saved,email:user.email,firstName:user.first_name||saved.firstName||'',lastName:user.last_name||saved.lastName||'',phone:profile.phone||saved.phone||'',birth:profile.birth_date||saved.birth||'',emergency:profile.emergency_contact||saved.emergency||'',news:profile.marketing_opt_in??saved.news??false}}}}catch(_){}}
    renderDetailsStep()
  }

  async function beginAccountSwitch(mode){
    const button=mode==='register'?$('#newAccount'):$('#changeAccount');
    if(button){button.disabled=true;button.textContent=mode==='register'?'Preparing new customer…':'Switching account…'}
    try{await fetch('/api/auth/logout',{method:'POST',credentials:'same-origin',cache:'no-store'})}catch(_){}
    wizard.authUser=null;wizard.credits=0;wizard.payment='sumup';wizard.paymentChoiceMade=false;wizard.sessionChecked=true;wizard.details={};
    try{localStorage.removeItem('cpWizardCustomer')}catch(_){}
    wizard.mode=mode;
    renderDetailsStep();
  }

  function renderDetailsStep(){
    const c=wizard.details||{},authenticated=wizard.mode==='authenticated'&&!!wizard.authUser,first=wizard.mode==='register';
    const accountName=authenticated?([wizard.authUser.first_name,wizard.authUser.last_name].filter(Boolean).join(' ')||wizard.authUser.email):'';
    const form=authenticated?`<div class="details-grid"><label class="field full"><span>CLASSY ACCOUNT</span><input value="${safe(accountName)}" disabled></label><label class="field full"><span>EMAIL</span><input id="wfEmail" type="email" value="${safe(wizard.authUser.email||c.email||'')}" disabled></label></div>`:first?`<div class="details-grid"><label class="field"><span>FIRST NAME *</span><input id="wfFirst" autocomplete="given-name" value="${safe(c.firstName||'')}"></label><label class="field"><span>LAST NAME *</span><input id="wfLast" autocomplete="family-name" value="${safe(c.lastName||'')}"></label><label class="field full"><span>EMAIL *</span><input id="wfEmail" type="email" autocomplete="email" value="${safe(c.email||'')}"></label><label class="field"><span>MOBILE NUMBER *</span><input id="wfPhone" type="tel" autocomplete="tel" value="${safe(c.phone||'')}"></label><label class="field"><span>DATE OF BIRTH *</span><input id="wfBirth" type="date" value="${safe(c.birth||'')}"></label><label class="field full"><span>PASSWORD *</span><input id="wfPassword" type="password" autocomplete="new-password" placeholder="At least 8 characters"></label><label class="field full"><span>EMERGENCY CONTACT</span><input id="wfEmergency" type="tel" value="${safe(c.emergency||'')}" placeholder="Optional"></label></div>`:`<div class="details-grid"><label class="field full"><span>EMAIL *</span><input id="wfEmail" type="email" autocomplete="email" value="${safe(c.email||'')}"></label><label class="field full"><span>PASSWORD *</span><input id="wfPassword" type="password" autocomplete="current-password" placeholder="Your Classy password"></label></div>`;
    const switchAccount=authenticated?'<div class="booking-account-switch signed-in-switch"><p>You are already signed in.</p><div><button type="button" id="changeAccount">Use a different account</button><button type="button" id="newAccount">Book for a new customer</button></div></div>':first?'<p class="booking-account-switch">Already have a Classy account? <button type="button" id="useSignIn">Sign in</button></p>':'<p class="booking-account-switch">New to Classy? <button type="button" id="createAccount">Create an account</button></p>';
    const title=authenticated?'Your Classy profile':first?'Create your Classy profile':'Welcome back';
    const kicker=authenticated?'SIGNED IN':first?'NEW TO CLASSY':'RETURNING CLIENT';
    const heading=authenticated?`Continue as ${safe(accountName)}.`:first?'Create your account.':'Sign in.';
    const copy=authenticated?'Your active Classy session will be used for this booking. No password is needed.':first?'Create your profile once. Your reservation will continue automatically after registration.':'Use your Classy profile for this booking.';
    const spotSummary=SPOT_SELECTION_ENABLED?`<div class="spot-summary"><span>SELECTED SPOT</span><b>${safe(spotLabel(wizard.spot,wizard.class))}</b><button id="changeSpot" type="button">Change</button></div>`:'';
    setDrawer(title,`${classSummary(wizard.class)}${spotSummary}<div class="wizard-panel"><div class="wizard-kicker">${kicker}</div><h4>${heading}</h4><p>${copy}</p>${form}<label class="wizard-check"><input id="wfTerms" type="checkbox" ${c.terms?'checked':''}><span>I accept the Terms & Conditions, Privacy Policy and Studio/Cancellation Rules. *</span></label>${first?'<label class="wizard-check optional"><input id="wfNews" type="checkbox" '+(c.news?'checked':'')+'><span>Receive news, new classes and studio updates by email.</span></label>':''}${switchAccount}<div class="wizard-sticky-actions"><button class="drawer-action secondary" id="backSpot">Back</button><button class="drawer-action" id="goPayment">Continue to payment</button></div></div>`,3);
    $('#changeSpot')?.addEventListener('click',renderSpotStep);$('#backSpot')?.addEventListener('click',()=>SPOT_SELECTION_ENABLED?renderSpotStep():renderClassStep());$('#goPayment')?.addEventListener('click',saveDetails);$('#createAccount')?.addEventListener('click',()=>{wizard.authUser=null;wizard.mode='register';renderDetailsStep()});$('#useSignIn')?.addEventListener('click',()=>{wizard.authUser=null;wizard.mode='login';renderDetailsStep()});$('#changeAccount')?.addEventListener('click',()=>beginAccountSwitch('login'));$('#newAccount')?.addEventListener('click',()=>beginAccountSwitch('register'))
  }

  function saveDetails(){
    const authenticated=wizard.mode==='authenticated'&&!!wizard.authUser,first=wizard.mode==='register',email=authenticated?(wizard.authUser.email||'').trim().toLowerCase():($('#wfEmail')?.value.trim().toLowerCase()||''),password=authenticated?'':($('#wfPassword')?.value||'');if(!emailOK(email)){showToast('Check email','Please enter a valid email address.');$('#wfEmail')?.focus();return}if(!authenticated&&password.length<8){showToast('Check password','At least 8 characters.');$('#wfPassword')?.focus();return}if(!$('#wfTerms')?.checked){showToast('Consent required','Please accept the terms.');return}
    let d;if(authenticated){const c=wizard.details||{};d={email,terms:true,news:!!c.news,firstName:wizard.authUser.first_name||c.firstName||'',lastName:wizard.authUser.last_name||c.lastName||'',phone:c.phone||'',birth:c.birth||'',emergency:c.emergency||''}}else{d={email,password,terms:true,news:!!$('#wfNews')?.checked};if(first){d.firstName=$('#wfFirst')?.value.trim()||'';d.lastName=$('#wfLast')?.value.trim()||'';d.phone=$('#wfPhone')?.value.trim()||'';d.birth=$('#wfBirth')?.value||'';d.emergency=$('#wfEmergency')?.value.trim()||'';if(d.firstName.length<2||d.lastName.length<2){showToast('Name required','First and last name are required.');return}if(!phoneOK(d.phone)){showToast('Check mobile number','Please enter a valid mobile number.');return}if(!d.birth){showToast('Date of birth required','Please enter your date of birth.');return}}}
    wizard.details=d;const {password:_,...draft}=d;write('cpWizardCustomer',draft);preparePaymentStep()
  }

  async function refreshCreditBalance(){
    try{
      const response=await fetch('/api/customer/profile',{credentials:'same-origin',cache:'no-store'});
      if(response.ok){
        const profile=await response.json();
        wizard.credits=Math.max(0,Number(profile.credits)||0);
        return wizard.credits
      }
    }catch(_){}
    wizard.credits=Math.max(0,Number(wizard.credits)||0);
    return wizard.credits
  }

  async function preparePaymentStep(){
    const button=$('#goPayment');
    if(button){button.disabled=true;button.innerHTML='<span class="button-spinner"></span> Checking your account…'}
    try{
      await authenticateCustomer();
      await refreshCreditBalance();
    }catch(error){
      if(button){button.disabled=false;button.textContent='Continue to payment'}
      const message=error.message==='invalid_credentials'?'Email or password is incorrect.':error.message==='password_too_short'?'The password must be at least 8 characters.':'We could not check your Classy account. Please try again.';
      showToast('Account check failed',message,'error');
      return
    }
    if((Number(wizard.credits)||0)>0&&!wizard.paymentChoiceMade)wizard.payment='class_credit';
    if((Number(wizard.credits)||0)<=0)wizard.payment='sumup';
    renderPaymentStep()
  }

  function renderPaymentStep(){
    const r=wizard.class;
    const credits=Math.max(0,Number(wizard.credits)||0);
    if(credits<=0)wizard.payment='sumup';
    const when=`${safe(formatFullDate(r.dateObj))} · ${safe(r.time)}`;
    const studio=safe(studioName(r));
    const selectedCredit=wizard.payment==='class_credit';
    const review=`<div class="payment-review-card"><div class="payment-review-session"><span>YOUR CLASS</span><b>${safe(r.name)}</b><small>${when}<br>${studio}</small></div><div class="payment-review-price"><span>PAYMENT</span><b>${selectedCredit?'1 Class Credit':'28,00 €'}</b><small>${credits>0?`${credits} Class Credit${credits===1?'':'s'} available`:'Secure payment with SumUp'}</small></div></div>`;
    const creditOption=credits>0?`<button type="button" class="wizard-pay ${selectedCredit?'active':''}" data-wpay="class_credit"><span class="pay-mark">1×</span><span><b>Use 1 Class Credit</b><small>You have ${credits} available. No new payment is needed.</small></span><i>${selectedCredit?'✓':''}</i></button>`:'';
    const paymentOptions=creditOption+payMethods.map(m=>`<button type="button" class="wizard-pay ${wizard.payment===m.id?'active':''}" data-wpay="${m.id}"><span class="pay-mark">${safe(m.mark)}</span><span><b>${safe(m.name)}</b><small>${safe(m.detail)}</small></span><i>${wizard.payment===m.id?'✓':''}</i></button>`).join('');
    const intro=credits>0?'You already have Class Credit available. You can use one for this booking instead of making a new payment.':'No Class Credit is currently available on this account, so this booking will continue with SumUp.';
    const action=selectedCredit?'Use 1 Class Credit':'Continue to SumUp';
    setDrawer('Checkout',`${review}<div class="wizard-panel payment-panel"><div class="wizard-kicker">SECURE CHECKOUT</div><h4>Ready to confirm.</h4><p>${intro}</p><div class="wizard-payment-grid">${paymentOptions}</div><div class="payment-security-note"><span>✓</span><p>${selectedCredit?'Your existing credit is only deducted after the booking is created successfully.':'No payment is marked as successful until SumUp confirms it.'}</p></div><div class="wizard-sticky-actions"><button class="drawer-action secondary" id="backDetails">Back</button><button class="drawer-action" id="finishPayment">${action}</button></div></div>`,4);
    document.querySelectorAll('[data-wpay]').forEach(b=>b.addEventListener('click',()=>{wizard.payment=b.dataset.wpay;wizard.paymentChoiceMade=true;renderPaymentStep()}));$('#backDetails')?.addEventListener('click',renderDetailsStep);$('#finishPayment')?.addEventListener('click',processPayment)
  }
  function resetPaymentButton(){
    const btn=$('#finishPayment');if(!btn)return;
    btn.disabled=false;
    btn.innerHTML=wizard.payment==='class_credit'?'Use 1 Class Credit':'Continue to SumUp'
  }
  function processPayment(){const btn=$('#finishPayment');if(btn){btn.disabled=true;btn.innerHTML=wizard.payment==='class_credit'?'<span class="button-spinner"></span> Using Class Credit…':'<span class="button-spinner"></span> Preparing secure payment…'}completeBookingPayment()}
  function bookingRefV2(){return 'CP-'+(cryptoSafeToken?cryptoSafeToken(8):Math.random().toString(36).slice(2,10).toUpperCase())}
  function checkoutRefV2(){return 'CP-BOOKPAY-'+(cryptoSafeToken?cryptoSafeToken(10):Math.random().toString(36).slice(2,12).toUpperCase())}
  async function accountRequest(path,body){let response;try{response=await timedFetch(path,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'content-type':'application/json'},body:JSON.stringify(body)},12000)}catch(error){if(error.message==='request_timeout')throw new Error('auth_timeout');throw error}let data={};try{data=await response.json()}catch(_){}if(!response.ok)throw new Error(data.detail||'request_failed');return data}
  async function authenticateCustomer(){const details=wizard.details;if(wizard.mode==='authenticated'&&wizard.authUser){const response=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});let user={};try{user=await response.json()}catch(_){}if(response.status===401)throw new Error('session_expired');if(!response.ok)throw new Error(user.detail||'request_failed');if(user.portal!=='/account')throw new Error('customer_account_required');wizard.authUser=user;return user}let result;if(wizard.mode==='register'){try{result=await accountRequest('/api/auth/register',{email:details.email,password:details.password,first_name:details.firstName,last_name:details.lastName,phone:details.phone,birth_date:details.birth,emergency_contact:details.emergency,marketing_opt_in:details.news})}catch(error){if(error.message!=='email_exists')throw error;result=await accountRequest('/api/auth/login',{email:details.email,password:details.password})}}else{result=await accountRequest('/api/auth/login',{email:details.email,password:details.password})}if(result.user?.portal!=='/account')throw new Error('customer_account_required');wizard.authUser=result.user;wizard.mode='authenticated';return result.user}
  async function createServerBooking(r,user){const startsAt=r.startsAt||new Date(`${r.date}T${r.time}:00`).toISOString();const classId=Number.isInteger(Number(r.id))?Number(r.id):String(r.id);let response;try{response=await timedFetch('/api/bookings',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'content-type':'application/json'},body:JSON.stringify({classId,email:user.email,firstName:user.first_name||wizard.details.firstName||'',lastName:user.last_name||wizard.details.lastName||'',phone:wizard.details.phone||'',spot:SPOT_SELECTION_ENABLED?wizard.spot:null,paymentMethod:wizard.payment==='class_credit'?'class_credit':'sumup',useCredit:wizard.payment==='class_credit',studioId:r.studio,title:r.name,classType:r.type,startsAt,duration:r.duration,capacity:r.capacity,coachName:r.coach,language:document.documentElement.lang==='de'?'de':'en'})},12000)}catch(error){if(error.message==='request_timeout')throw new Error('booking_create_timeout');throw error}let data={};try{data=await response.json()}catch(_){}if(!response.ok)throw new Error(data.detail||'booking_failed');return data}
  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  function paymentProgress(text){const btn=$('#finishPayment');if(btn){btn.disabled=true;btn.innerHTML=`<span class="button-spinner"></span> ${safe(text)}`}}
  async function waitForBookingSync(reference){
    const deadline=Date.now()+60000;
    let dots=1;
    while(Date.now()<deadline){
      try{
        const response=await timedFetch('/api/bookings/sync-status?reference='+encodeURIComponent(reference),{credentials:'same-origin',cache:'no-store'},8000);
        let data={};try{data=await response.json()}catch(_){}
        if(response.status===401)throw new Error('session_expired');
        if(!response.ok)throw new Error(data.detail||'booking_sync_failed');
        if(data.ready)return data;
        if(data.failed)throw new Error(data.error||'mindbody_booking_failed');
      }catch(error){
        if(!['request_timeout','booking_sync_failed'].includes(error.message))throw error;
      }
      paymentProgress('Reserving your place'+'.'.repeat(dots));
      dots=dots===3?1:dots+1;
      await sleep(900);
    }
    throw new Error('mindbody_timeout')
  }
  function saveLocalBooking(r,email,ref,paymentState,paymentMethod,adjust=true){const existing=read('cpBookings',[]);if(!existing.some(b=>b.ref===ref)){existing.unshift({ref,email,classId:r.id,name:r.name,time:r.time,date:r.date,studio:studioName(r),studioId:r.studio,coach:r.coach,spot:SPOT_SELECTION_ENABLED?spotLabel(wizard.spot,r):'',spotNumber:SPOT_SELECTION_ENABLED?wizard.spot:null,paymentMethod,status:'reserved',paymentState,createdAt:new Date().toISOString()});write('cpBookings',existing.slice(0,50));if(adjust){try{adjustSeats(r.id,-1)}catch(_){}}}try{localStorage.setItem('cpLastEmail',email)}catch(_){}}
  async function createBookingCheckout(bookingReference,user){const reference=checkoutRefV2();let response;try{response=await timedFetch('/api/checkout/create',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'content-type':'application/json','x-idempotency-key':reference},body:JSON.stringify({reference,bookingReference,customer:{email:user.email,firstName:user.first_name||wizard.details.firstName||'',lastName:user.last_name||wizard.details.lastName||''},items:[]})},12000)}catch(error){if(error.message==='request_timeout')throw new Error('sumup_timeout');throw error}let data={};try{data=await response.json()}catch(_){}const url=data.hosted_checkout_url||data.url;if(!response.ok||!url)throw new Error(data.detail||'checkout_failed');return {reference,url}}
  function showPaymentFailure(code){
    const messages={
      invalid_credentials:'Email or password is incorrect.',
      duplicate_booking:'This class is already booked on this Classy account.',
      class_full:'This class has just sold out.',
      class_unavailable:'This class is no longer available.',
      class_started:'This class has already started.',
      spot_taken:'This spot was just taken.',
      customer_account_required:'Please use a customer account.',
      password_too_short:'The password must be at least 8 characters.',
      voucher_not_found:'The voucher or gift code could not be found. Please check the code or remove it and try again.',
      voucher_already_redeemed:'This voucher has already been redeemed.',
      mindbody_availability_unavailable:'Live availability could not be confirmed with Mindbody. Please try again in a moment.',
      mindbody_booking_failed:'We could not hold this place in Mindbody. No payment was taken. Please retry or choose another class.',
      mindbody_auth_failed:'Mindbody could not authorize the reservation. No payment was taken. Please try again in a moment.',
      mindbody_profile_incomplete:'Your Classy profile is missing information required by Mindbody. Please update your mobile number and try again.',
      mindbody_permission_denied:'Mindbody rejected the reservation permission. No payment was taken.',
      request_timeout:'The request took too long. No payment was taken. Please try again.',
      auth_timeout:'Sign in took too long. No payment was taken. Please try again.',
      booking_create_timeout:'The booking server was busy for too long. No payment was taken. Please tap continue again.',
      sumup_timeout:'SumUp took too long to start the secure checkout. No payment was taken. Please tap continue again.',
      mindbody_timeout:'Mindbody is taking longer than expected to confirm the reservation. No payment was taken. Tap continue again to resume the same booking.',
      sumup_not_configured:'Secure payment is currently unavailable.',
      sumup_unavailable:'SumUp is temporarily unavailable. Please try again.',
      sumup_checkout_state_unavailable:'The current SumUp payment session could not be verified. Please try again.',
      booking_not_payable:'This reservation is no longer payable. Please refresh the schedule and try again.',
      booking_checkout_already_active:'A payment session is already active for this booking. Tap continue again to resume it.',
      booking_already_paid:'This booking is already paid.',
      checkout_failed:'Secure payment could not be started.',
      class_credit_unavailable:'Your Class Credit is no longer available. Please choose SumUp or refresh your account.'
    };
    const message=messages[code]||'We could not start the payment. No payment was confirmed. Please try again.';
    renderPaymentStep();
    const panel=$('.payment-panel');
    const grid=panel?.querySelector('.wizard-payment-grid');
    if(panel&&grid){
      const box=document.createElement('div');
      box.className='payment-error';
      box.innerHTML=`<b>Payment not completed</b><p>${safe(message)}</p>`;
      panel.insertBefore(box,grid);
      requestAnimationFrame(()=>box.scrollIntoView({behavior:'smooth',block:'center'}));
    }else showToast('Payment not completed',message);
  }

  async function completeBookingPayment(){
    const r=wizard.class,email=wizard.details.email;
    try{
      const user=await authenticateCustomer();
      const result=await createServerBooking(r,user);
      const ref=result.booking?.reference||bookingRefV2();
      if(!result.booking?.reference)throw new Error('booking_failed');
      let sync=result;
      if(!['synced','local'].includes(result.sync_status||'')){
        paymentProgress('Reserving your place…');
        sync=await waitForBookingSync(ref);
      }
      const creditUsed=Boolean(sync.credit_used??result.credit_used);
      const paymentStatus=sync.payment_status||result.payment_status;
      if(creditUsed||paymentStatus==='paid'){
        wizard.payment=creditUsed?'class_credit':'sumup';
        saveLocalBooking(r,email,ref,'paid',wizard.payment);
        renderSchedule();
        renderSuccess(ref);
        return
      }
      paymentProgress('Opening secure payment…');
      const checkout=await createBookingCheckout(ref,user);
      write('cpPendingBookingPayment',{bookingReference:result.booking.reference,orderReference:checkout.reference,email,wizard:{class:r,spot:SPOT_SELECTION_ENABLED?wizard.spot:null,payment:'sumup',details:{email,firstName:user.first_name||wizard.details.firstName||'',lastName:user.last_name||wizard.details.lastName||'',phone:wizard.details.phone||''}}});
      location.href=checkout.url
    }catch(error){
      if(error.message==='session_expired'){
        wizard.authUser=null;wizard.mode='login';wizard.sessionChecked=true;
        showToast('Session expired','Please sign in again to continue your booking.');
        renderDetailsStep();
        return
      }
      console.warn('Classy checkout failed:',error.message);
      if(error.message==='class_credit_unavailable'){wizard.credits=0;wizard.payment='sumup';wizard.paymentChoiceMade=true;renderPaymentStep()}
      else resetPaymentButton();
      showPaymentFailure(error.message)
    }
  }
  function calendarFile(){
    const r=wizard.class,start=new Date(r.startsAt||`${r.date}T${r.time}:00`),end=new Date(start.getTime()+r.duration*60000);
    const fmt=d=>d.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
    const spotText=SPOT_SELECTION_ENABLED?` · ${spotLabel(wizard.spot,r)}`:'';
    const escIcs=value=>String(value||'').replace(/\\/g,'\\\\').replace(/,/g,'\\,').replace(/;/g,'\\;').replace(/\n/g,'\\n');
    const uid=`classy-${String(r.id||'class')}-${fmt(start)}@classypilates.de`;
    const body=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Classy Pilates Frankfurt//Booking//DE','CALSCALE:GREGORIAN','METHOD:PUBLISH','BEGIN:VEVENT',`UID:${uid}`,`DTSTAMP:${fmt(new Date())}`,`DTSTART:${fmt(start)}`,`DTEND:${fmt(end)}`,`SUMMARY:${escIcs('Classy Pilates · '+r.name)}`,`LOCATION:${escIcs(studioName(r))}`,`DESCRIPTION:${escIcs('Coach '+r.coach+spotText)}`,'END:VEVENT','END:VCALENDAR',''].join('\r\n');
    return new File([body],'classy-pilates.ics',{type:'text/calendar;charset=utf-8'});
  }
  async function addToCalendar(){
    const button=$('#addCalendarV2'),original=button?.textContent||'Add to calendar';
    if(button){button.disabled=true;button.textContent='Opening calendar…'}
    try{
      const file=calendarFile();
      if(navigator.share&&navigator.canShare?.({files:[file]})) await navigator.share({files:[file],title:'Classy Pilates',text:wizard.class.name});
      else{const url=URL.createObjectURL(file),link=document.createElement('a');link.href=url;link.download=file.name;link.style.display='none';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),15000)}
    }catch(error){if(error?.name!=='AbortError')showToast('Calendar','The calendar file could not be opened. Please try again.')}
    finally{if(button){button.disabled=false;button.textContent=original}}
  }
  function renderSuccess(ref){const method=wizard.payment==='class_credit'?'Class Credit':(payMethods.find(x=>x.id===wizard.payment)?.name||wizard.payment);const spotGrid=SPOT_SELECTION_ENABLED?`<div><span>SPOT</span><b>${safe(spotLabel(wizard.spot,wizard.class))}</b></div>`:'';setDrawer('Booking confirmed',`<div class="booking-success-v2"><div class="success-orbit"><span>✓</span></div><p class="eyebrow">YOU'RE IN</p><h3>See you in class.</h3><p class="success-lead">Your booking is reserved and linked to your Classy account.</p>${classSummary(wizard.class)}<div class="success-grid">${spotGrid}<div><span>PAYMENT</span><b>${safe(method)}</b></div><div><span>BOOKING</span><b>${safe(ref)}</b></div></div><div class="demo-payment-note success"><span>ACCOUNT READY</span><p>Your bookings, credits and profile are now available in “My Classy”.</p></div><div class="success-actions"><a class="drawer-action" href="/account">Open My Classy</a><button class="drawer-action secondary" id="addCalendarV2" type="button">Add to calendar</button><button class="drawer-action secondary" id="doneV2">Done</button></div></div>`,5);$('#addCalendarV2')?.addEventListener('click',addToCalendar);$('#doneV2')?.addEventListener('click',closeDrawer)}

  async function handleBookingPaymentReturn(){
    const q=new URLSearchParams(location.search);if(q.get('flow')!=='booking')return false;const pending=read('cpPendingBookingPayment',null),orderRef=q.get('reference')||pending?.orderReference||'';let verified='pending',ref=q.get('bookingReference')||pending?.bookingReference||'';if(orderRef){try{const response=await fetch('/api/checkout/status?reference='+encodeURIComponent(orderRef),{credentials:'same-origin',cache:'no-store'});const data=await response.json().catch(()=>({}));if(response.ok){verified=data.status||'pending';ref=data.bookingReference||ref}else if(response.status===404)verified='failed'}catch(_){}}if(verified==='paid'&&ref){if(pending&&pending.bookingReference===ref){wizard={...pending.wizard,payment:'sumup'};saveLocalBooking(wizard.class,pending.email,ref,'paid','sumup',false);try{localStorage.removeItem('cpPendingBookingPayment')}catch(_){}renderSchedule();setTimeout(()=>renderSuccess(ref),80)}else{setDrawer('Booking confirmed',`<div class="booking-success-v2"><div class="success-orbit"><span>✓</span></div><p class="eyebrow">PAYMENT VERIFIED</p><h3>Your booking is confirmed.</h3><p class="success-lead">SumUp confirmed the payment. Your paid booking reference is shown below.</p><div class="success-grid"><div><span>PAYMENT</span><b>SumUp</b></div><div><span>BOOKING</span><b>${safe(ref)}</b></div></div><div class="success-actions"><a class="drawer-action" href="/account">Open My Classy</a><button class="drawer-action secondary" id="doneV2">Done</button></div></div>`,5);$('#doneV2')?.addEventListener('click',closeDrawer)}}else{const failed=['failed','cancelled'].includes(verified);showToast(failed?'Payment not completed':'Payment is processing',failed?'SumUp did not confirm the payment. The pending booking has been cancelled.':'No successful payment has been confirmed yet. Please check your account before trying again.')}history.replaceState({},'',location.pathname+(location.hash||'#schedule'));return true
  }

  const originalOpenClass=typeof openClass==='function'?openClass:null;
  if(originalOpenClass){openClass=function(r){if(!r)return;if(Number(r.spots)<=0)return originalOpenClass(r);startWizard(r)}}

  moveStudiosBeforeSchedule();addQuickDock();observeDynamicUi();loadCoachPhotos();handleBookingPaymentReturn();
})();
