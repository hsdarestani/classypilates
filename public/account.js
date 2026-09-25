(()=>{
  const $=(s,c=document)=>c.querySelector(s), $$=(s,c=document)=>[...c.querySelectorAll(s)];
  const state={user:null,view:'overview',dashboard:null};
  const titles={overview:['MY CLASSY','Overview'],bookings:['RESERVATIONS','My bookings'],credits:['CLASS PASSES','Credits & passes'],waitlist:['AVAILABILITY','Waitlist'],profile:['ACCOUNT','Profile & security']};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const locale=()=>document.documentElement.lang==='de'?'de-DE':'en-GB';
  const dt=value=>new Intl.DateTimeFormat(locale(),{weekday:'short',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value));
  const money=value=>new Intl.NumberFormat(locale(),{style:'currency',currency:'EUR'}).format((Number(value)||0)/100);
  const tr=value=>window.ClassyI18n?.t?window.ClassyI18n.t(value):value;
  const toast=text=>{const el=$('#accountToast');el.textContent=text;el.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>el.classList.remove('show'),2800)};
  async function api(path,options={}){let response;try{response=await fetch(path,{credentials:'same-origin',cache:'no-store',...options,headers:{...(options.body?{'content-type':'application/json'}:{}),...(options.headers||{})}})}catch(_){throw new Error('server_unreachable')}let data={};try{data=await response.json()}catch(_){}if(response.status===401){location.replace('/login?next=/account');throw new Error('login_required')}if(!response.ok)throw new Error(data.detail||'request_failed');return data}
  async function init(){try{const user=await api('/api/auth/me');if(user.portal!=='/account'){location.replace(user.portal||'/login');return}state.user=user;const name=[user.first_name,user.last_name].filter(Boolean).join(' ')||user.email;$('#accountName').textContent=name;$('#accountAvatar').textContent=(user.first_name?.[0]||user.email[0]).toUpperCase();$('#accountApp').hidden=false;$$('#accountNav button').forEach(button=>button.onclick=()=>switchView(button.dataset.view));$('#accountMenu').onclick=()=>$('#accountSide').classList.toggle('open');$('#accountLogout').onclick=logout;switchView(location.hash.slice(1)||'overview')}catch(error){if(error.message!=='login_required')location.replace('/login?next=/account')}}
  async function logout(){try{await fetch('/api/auth/logout',{method:'POST',credentials:'same-origin'})}catch(_){}localStorage.removeItem('cpStaffToken');location.replace('/login')}
  async function switchView(view){if(!titles[view])view='overview';state.view=view;history.replaceState({},'',`/account#${view}`);$$('#accountNav button').forEach(button=>button.classList.toggle('active',button.dataset.view===view));$('#accountSide').classList.remove('open');const [eyebrow,title]=titles[view];$('#accountEyebrow').textContent=eyebrow;$('#accountTitle').textContent=title;$('#accountView').innerHTML='<div class="account-loading">Loading…</div>';try{if(view==='overview')await overview();else if(view==='bookings')await bookings();else if(view==='credits')await credits();else if(view==='waitlist')await waitlist();else await profile()}catch(error){$('#accountView').innerHTML=`<div class="empty-account"><div><span>Connection failed</span><p>${esc(error.message)}</p></div></div>`}}
  const statusLabel=status=>({reserved:'Reserved',cancelled:'Cancelled',attended:'Attended',no_show:'No-show'}[status]||status);
  function bookingCard(booking,compact=false){return `<article class="booking-item"><div><span class="status ${esc(booking.status)}">${esc(statusLabel(booking.status))}</span><h3>${esc(booking.name)}</h3><p>${dt(booking.starts_at)} · ${booking.duration} min</p><small>${esc(booking.studio)} · ${esc(booking.coach)}</small></div><div class="booking-meta"><div><span>BOOKING</span><b>${esc(booking.reference)}</b></div><div><span>SPOT</span><b>${booking.spot_number?'#'+booking.spot_number:'—'}</b></div><div><span>PAYMENT</span><b>${esc(booking.payment_status)}</b></div><div><span>AMOUNT</span><b>${money(booking.amount_cents)}</b></div></div>${!compact&&booking.status==='reserved'?`<button class="account-button ${booking.can_cancel?'danger':'secondary'}" data-cancel="${esc(booking.reference)}" ${booking.can_cancel?'':'disabled'}>${booking.can_cancel?'Cancel':'Window closed'}</button>`:'<span></span>'}</article>`}
  async function overview(){
    const data=await api('/api/customer/dashboard');state.dashboard=data;
    const next=data.next_booking;
    const activeRecent=(data.recent_bookings||[]).filter(row=>row.status==='reserved').slice(0,2);
    const historyCount=Math.max(0,Number(data.total_bookings||0)-Number(data.upcoming_count||0));
    $('#accountView').innerHTML=`
      <section class="overview-hero">
        <div class="overview-credit">
          <div class="overview-credit-copy"><span>CLASS CREDITS</span><strong>${data.credits}</strong><small>available on your account</small></div>
          <a href="/#schedule">Book a class</a>
        </div>
        <div class="overview-stats">
          <article><span>UPCOMING</span><b>${data.upcoming_count}</b><small>active bookings</small></article>
          <article><span>WAITLIST</span><b>${data.waitlist_count}</b><small>open entries</small></article>
          <article><span>HISTORY</span><b>${historyCount}</b><small>past bookings</small></article>
        </div>
      </section>
      ${next?`
        <section class="account-panel next-class overview-next">
          <div><p>YOUR NEXT CLASS</p><h2>${esc(next.name)}</h2><p>${dt(next.starts_at)}<br>${esc(next.studio)} · ${esc(next.coach)}</p></div>
          <button type="button" class="next-class-action" id="nextClassBookings">View booking</button>
        </section>`
        :`<section class="overview-empty-next"><div><span>YOUR NEXT CLASS</span><h2>Ready when you are.</h2><p>You have no active class booked right now.</p></div><a href="/#schedule">Explore schedule</a></section>`}
      <section class="account-panel overview-activity">
        <div class="account-panel-head"><div><p>ACTIVE BOOKINGS</p><h2>Your current reservations</h2><small>Only active bookings are shown here. Past and cancelled bookings stay in booking history.</small></div><button class="account-button secondary" id="allBookings">View all</button></div>
        ${activeRecent.length?`<div class="booking-list overview-booking-list">${activeRecent.map(row=>bookingCard(row,true)).join('')}</div>`:`<div class="overview-empty-inline"><span>No active reservations</span><p>Choose your next Classy session whenever you are ready.</p></div>`}
      </section>`;
    $('#allBookings')?.addEventListener('click',()=>switchView('bookings'));
    $('#nextClassBookings')?.addEventListener('click',()=>switchView('bookings'));
  }
  async function bookings(filter=state.bookingFilter||'active'){
    state.bookingFilter=filter;
    const data=await api('/api/customer/bookings');
    const rows=Array.isArray(data.bookings)?data.bookings:[];
    const active=rows.filter(row=>row.status==='reserved');
    const history=rows.filter(row=>row.status!=='reserved');
    const selected=filter==='history'?history:active;
    const empty=filter==='history'
      ?'<div class="empty-account"><div><span>No past bookings yet.</span><p>Cancelled and completed bookings will appear here.</p></div></div>'
      :'<div class="empty-account"><div><span>No active bookings.</span><p>Your next confirmed booking will appear here.</p><a href="/#schedule">Book a class</a></div></div>';
    $('#accountView').innerHTML=`<section class="account-panel bookings-panel">
      <div class="account-panel-head bookings-head"><div><p>BOOKING HISTORY</p><h2>Your bookings</h2><small>Active reservations are shown first. Online cancellation is available until 12 hours before class starts.</small></div>
      <div class="account-head-actions"><button class="account-button secondary" id="claimBooking">Link guest booking</button><a class="account-button" href="/#schedule" style="text-decoration:none">New class</a></div></div>
      <div class="booking-tabs" role="tablist">
        <button type="button" class="${filter==='active'?'active':''}" data-booking-filter="active">Active <span>${active.length}</span></button>
        <button type="button" class="${filter==='history'?'active':''}" data-booking-filter="history">Past & cancelled <span>${history.length}</span></button>
      </div>
      ${selected.length?`<div class="booking-list">${selected.map(row=>bookingCard(row)).join('')}</div>`:empty}
    </section>`;
    $('#claimBooking').onclick=async()=>{const reference=prompt('Enter booking reference (e.g. CP-1234ABCD)');if(!reference)return;try{await api('/api/customer/bookings/claim',{method:'POST',body:JSON.stringify({reference})});toast('Booking linked securely.');bookings(state.bookingFilter)}catch(error){toast(error.message==='booking_not_found'?'No matching booking was found for your account.':'Unable to link this booking.')}};
    $$('[data-booking-filter]').forEach(button=>button.onclick=()=>bookings(button.dataset.bookingFilter));
    $$('[data-cancel]').forEach(button=>button.onclick=async()=>{
      if(!confirm(tr('Cancel this booking?')))return;
      const card=button.closest('.booking-item'),original=button.textContent;
      button.disabled=true;button.setAttribute('aria-busy','true');button.textContent=tr('Cancelling…');card?.classList.add('is-cancelling');toast(tr('Cancellation in progress…'));
      try{
        await api(`/api/customer/bookings/${encodeURIComponent(button.dataset.cancel)}`,{method:'DELETE'});
        toast(tr('Booking cancelled.'));
        await bookings('active');
      }catch(error){
        button.disabled=false;button.removeAttribute('aria-busy');button.textContent=original;card?.classList.remove('is-cancelling');
        toast(error.message==='cancellation_window_closed'?tr('The 12-hour cancellation window has closed.'):tr('Unable to cancel this booking.'))
      }
    })
  }
  async function credits(){const data=await api('/api/customer/dashboard');state.dashboard=data;$('#accountView').innerHTML=`<div class="credit-hero"><section class="credit-balance"><span>AVAILABLE CLASS CREDITS</span><b>${data.credits}</b><p>Credits are added to your Classy account after confirmed payment and can be used across all studios.</p><a class="account-button" href="/shop" style="text-decoration:none;width:max-content">Buy credits</a></section><div class="credit-actions"><article class="voucher-redeem"><h3>Redeem a gift code</h3><p>Enter your Classy gift code to add all 10 credits to this account.</p><label>GIFT CODE<input id="voucherCode" placeholder="CLASSY-XXXXXX-XXXXXX"></label><button class="account-button" id="redeemVoucher">Redeem code</button></article><article><h3>Across all studios</h3><p>One profile and one credit balance for all six Classy spaces.</p></article><article><h3>Securely synchronised</h3><p>Each booking uses one credit. A timely cancellation returns it automatically.</p></article></div></div>`;$('#redeemVoucher').onclick=async()=>{const code=$('#voucherCode').value.trim();if(!code)return toast('Enter your gift code');try{const result=await api('/api/customer/vouchers/redeem',{method:'POST',body:JSON.stringify({code})});toast(`${result.credits_added} credits added`);state.dashboard=null;credits()}catch(error){toast(error.message==='voucher_already_redeemed'?'This code has already been redeemed.':error.message==='voucher_not_found'?'Gift code not found.':'Unable to redeem this code.')}}}
  async function waitlist(){const data=await api('/api/customer/waitlist');$('#accountView').innerHTML=`<section class="account-panel"><div class="account-panel-head"><div><p>WAITLIST</p><h2>Open entries</h2><small>Leave a waitlist at any time with one click.</small></div></div>${data.waitlist.length?`<div class="booking-list">${data.waitlist.map(row=>`<article class="booking-item"><div><span class="status">Waitlist</span><h3>${esc(row.name)}</h3><p>${dt(row.starts_at)}</p><small>${esc(row.studio)} · ${esc(row.coach)}</small></div><div></div><button class="account-button secondary" data-leave="${row.id}">Leave</button></article>`).join('')}</div>`:`<div class="empty-account"><div><span>No waitlists.</span><p>Your active entries appear here.</p></div></div>`}</section>`;$$('[data-leave]').forEach(button=>button.onclick=async()=>{await api(`/api/customer/waitlist/${button.dataset.leave}`,{method:'DELETE'});toast('Left the waitlist.');waitlist()})}
  async function profile(){
    const data=await api('/api/customer/profile');
    $('#accountView').innerHTML=`
      <div class="profile-layout">
        <section class="account-panel profile-card">
          <div class="account-panel-head"><div><p>PERSONAL DATA</p><h2>Your profile</h2><small>Keep your contact details up to date for bookings and studio communication.</small></div></div>
          <div class="profile-grid profile-grid-clean">
            <label>FIRST NAME<input id="pFirst" value="${esc(data.first_name)}"></label>
            <label>LAST NAME<input id="pLast" value="${esc(data.last_name)}"></label>
            <label class="full">EMAIL<input value="${esc(data.email)}" disabled></label>
            <label>MOBILE NUMBER<input id="pPhone" value="${esc(data.phone)}"></label>
            <label>DATE OF BIRTH<input id="pBirth" type="date" value="${esc(data.birth_date)}"></label>
            <label class="full">EMERGENCY CONTACT<input id="pEmergency" value="${esc(data.emergency_contact)}"></label>
          </div>
          <label class="setting-row">
            <span><b>Classy news & studio updates</b><small>Receive selected studio news and class updates by email.</small></span>
            <input id="pMarketing" type="checkbox" ${data.marketing_opt_in?'checked':''}>
            <i aria-hidden="true"></i>
          </label>
          <div class="profile-actions"><button class="account-button" id="saveProfile">Save profile</button></div>
        </section>

        <section class="account-panel security-card">
          <div class="account-panel-head"><div><p>SECURITY</p><h2>Change password</h2><small>Use at least 8 characters for your new password.</small></div></div>
          <div class="security-fields">
            <label><span>CURRENT PASSWORD</span><input id="pCurrent" type="password" autocomplete="current-password"></label>
            <label><span>NEW PASSWORD</span><input id="pNew" type="password" autocomplete="new-password" placeholder="At least 8 characters"></label>
          </div>
          <label class="setting-row password-setting">
            <span><b>Show passwords</b><small>Temporarily reveal both password fields.</small></span>
            <input id="pShowPasswords" type="checkbox" data-password-toggle data-password-targets="#pCurrent,#pNew">
            <i aria-hidden="true"></i>
          </label>
          <div class="profile-actions"><button class="account-button" id="changePassword">Change password</button></div>
        </section>
      </div>`;
    const pShow=$('#pShowPasswords');
    if(pShow){
      const sync=()=>{const type=pShow.checked?'text':'password';['#pCurrent','#pNew'].map(selector=>$(selector)).filter(Boolean).forEach(field=>{field.type=type;field.setAttribute('type',type)})};
      pShow.addEventListener('change',sync);pShow.addEventListener('input',sync);sync()
    }
    $('#saveProfile').onclick=async()=>{
      await api('/api/customer/profile',{method:'PATCH',body:JSON.stringify({first_name:$('#pFirst').value,last_name:$('#pLast').value,phone:$('#pPhone').value,birth_date:$('#pBirth').value,emergency_contact:$('#pEmergency').value,marketing_opt_in:$('#pMarketing').checked})});
      state.user.first_name=$('#pFirst').value;state.user.last_name=$('#pLast').value;
      $('#accountName').textContent=`${state.user.first_name} ${state.user.last_name}`.trim();toast('Profile saved.')
    };
    $('#changePassword').onclick=async()=>{
      try{
        await api('/api/customer/change-password',{method:'POST',body:JSON.stringify({current_password:$('#pCurrent').value,new_password:$('#pNew').value})});
        $('#pCurrent').value='';$('#pNew').value='';toast('Password changed.')
      }catch(error){toast(error.message==='current_password_invalid'?'Current password is incorrect.':error.message==='password_too_short'?'At least 8 characters.':'Unable to change password.')}
    }
  }
  init();
})();
