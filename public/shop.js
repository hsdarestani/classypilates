const PRODUCTS={
  single:{id:'single',name:'1 Class',eyebrow:'SINGLE',price:2800,description:'Maximale Flexibilität für deine nächste Class.'},
  five:{id:'five',name:'5 Classes',eyebrow:'FLEXIBLE',price:11900,description:'Fünf Classes für deinen flexiblen Trainingsrhythmus.'},
  ten:{id:'ten',name:'10 Classes',eyebrow:'MOST POPULAR',price:21900,description:'21,90 € pro Class – ideal für deine feste Routine.',featured:true},
  twenty:{id:'twenty',name:'20 Classes',eyebrow:'COMMITTED',price:39900,description:'19,95 € pro Class – für regelmäßiges Training.'}
};
const PAYMENT_METHODS=[
  {id:'card',name:'Karte',hint:'Visa · Mastercard · American Express',badge:'CARD'},
  {id:'apple_pay',name:'Apple Pay',hint:'Schnell mit deinem Apple Gerät bezahlen',badge:' Pay'},
  {id:'google_pay',name:'Google Pay',hint:'Schnell mit Google Wallet bezahlen',badge:'G Pay'},
  {id:'paypal',name:'PayPal',hint:'Weiter zu PayPal',badge:'PayPal'},
  {id:'klarna',name:'Klarna',hint:'Verfügbare Klarna-Optionen im Checkout',badge:'Klarna.'},
  {id:'sepa_debit',name:'SEPA-Lastschrift',hint:'Direkte Abbuchung vom Bankkonto',badge:'SEPA'},
  {id:'link',name:'Link',hint:'Stripe Link – schneller Checkout',badge:'Link'}
];
const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
const money=cents=>new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(cents/100);
const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const validEmail=v=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
const state={cart:read('cpCart',[]),step:1,customer:read('cpCustomer',{}),payment:'card'};

function read(key,fallback){try{return JSON.parse(localStorage.getItem(key))??fallback}catch(_){return fallback}}
function write(key,value){try{localStorage.setItem(key,JSON.stringify(value))}catch(_){}}
function token(len=8){const chars='ABCDEFGHJKLMNPQRSTUVWXYZ23456789';if(crypto?.getRandomValues){const a=new Uint8Array(len);crypto.getRandomValues(a);return [...a].map(x=>chars[x%chars.length]).join('')}return Math.random().toString(36).slice(2,2+len).toUpperCase()}
function cartItems(){return state.cart.map(id=>PRODUCTS[id]).filter(Boolean)}
function total(){return cartItems().reduce((s,p)=>s+p.price,0)}
function showToast(title,text=''){const t=$('#toast');$('#toastTitle').textContent=title;$('#toastText').textContent=text;t.classList.add('show');clearTimeout(showToast.timer);showToast.timer=setTimeout(()=>t.classList.remove('show'),2800)}

function renderProducts(){
  $('#productGrid').innerHTML=Object.values(PRODUCTS).map(p=>`<article class="product-card ${p.featured?'featured':''}">${p.featured?'<span class="badge">MOST POPULAR</span>':''}<small>${esc(p.eyebrow)}</small><h3>${esc(p.name)}</h3><div class="price">${money(p.price)}</div><p>${esc(p.description)}</p><button type="button" data-add="${p.id}">In den Warenkorb →</button></article>`).join('');
  $$('[data-add]').forEach(btn=>btn.addEventListener('click',()=>addProduct(btn.dataset.add)));
}
function addProduct(id){if(!PRODUCTS[id])return;if(!state.cart.includes(id))state.cart.push(id);write('cpCart',state.cart);updateCartCount();showToast('Zum Warenkorb hinzugefügt',PRODUCTS[id].name);openCart()}
function removeProduct(id){state.cart=state.cart.filter(x=>x!==id);write('cpCart',state.cart);updateCartCount();renderDrawer()}
function updateCartCount(){$('#cartCount').textContent=state.cart.length}
function openCart(){state.step=1;renderDrawer();$('#drawerBackdrop').classList.add('open');$('#cartDrawer').classList.add('open');$('#cartDrawer').setAttribute('aria-hidden','false');document.body.style.overflow='hidden'}
function closeCart(){$('#drawerBackdrop').classList.remove('open');$('#cartDrawer').classList.remove('open');$('#cartDrawer').setAttribute('aria-hidden','true');document.body.style.overflow=''}
function progress(){const labels=['1 Warenkorb','2 Daten','3 Zahlung'];$('#checkoutProgress').innerHTML=labels.map((x,i)=>`<span class="${state.step===i+1?'active':''}">${x}</span>`).join('')}
function renderDrawer(){progress();if(state.step===1)renderCart();if(state.step===2)renderCustomer();if(state.step===3)renderPayment()}
function renderCart(){
  $('#drawerTitle').textContent='Warenkorb';const items=cartItems();
  if(!items.length){$('#drawerBody').innerHTML='<div class="empty"><h3>Dein Warenkorb ist leer.</h3><p>Wähle ein Class Pack und starte danach den Checkout.</p><button class="drawer-action" id="continueShop" type="button">Weiter shoppen</button></div>';$('#continueShop').addEventListener('click',closeCart);return}
  $('#drawerBody').innerHTML=items.map(p=>`<div class="cart-item"><div><b>${esc(p.name)}</b><span>Digitales Class Pack · alle Studios</span></div><div><b>${money(p.price)}</b><button class="remove-item" data-remove="${p.id}" type="button">Entfernen</button></div></div>`).join('')+`<div class="summary"><div class="summary-row"><span>Zwischensumme</span><b>${money(total())}</b></div><div class="summary-row"><span>Versand</span><b>Digital · 0,00 €</b></div><div class="summary-row total"><span>Gesamt</span><b>${money(total())}</b></div></div><button class="drawer-action" id="toCustomer" type="button">Weiter zu deinen Daten</button>`;
  $$('[data-remove]').forEach(b=>b.addEventListener('click',()=>removeProduct(b.dataset.remove)));$('#toCustomer').addEventListener('click',()=>{state.step=2;renderDrawer()});
}
function renderCustomer(){
  $('#drawerTitle').textContent='Deine Daten';const c=state.customer||{};
  $('#drawerBody').innerHTML=`<div class="grid-2"><label class="field"><span>VORNAME *</span><input id="firstName" autocomplete="given-name" value="${esc(c.firstName||'')}"></label><label class="field"><span>NACHNAME *</span><input id="lastName" autocomplete="family-name" value="${esc(c.lastName||'')}"></label></div><label class="field"><span>E-MAIL *</span><input id="email" type="email" autocomplete="email" value="${esc(c.email||'')}"></label><label class="field"><span>TELEFON</span><input id="phone" type="tel" autocomplete="tel" value="${esc(c.phone||'')}"></label><label class="field"><span>STRASSE & HAUSNUMMER</span><input id="street" autocomplete="street-address" value="${esc(c.street||'')}"></label><div class="grid-2"><label class="field"><span>PLZ</span><input id="zip" autocomplete="postal-code" value="${esc(c.zip||'')}"></label><label class="field"><span>ORT</span><input id="city" autocomplete="address-level2" value="${esc(c.city||'Frankfurt am Main')}"></label></div><button class="drawer-action" id="toPayment" type="button">Weiter zur Zahlung</button><button class="drawer-action secondary" id="backCart" type="button">Zurück</button>`;
  $('#backCart').addEventListener('click',()=>{state.step=1;renderDrawer()});$('#toPayment').addEventListener('click',saveCustomer);
}
function saveCustomer(){const c={firstName:$('#firstName').value.trim(),lastName:$('#lastName').value.trim(),email:$('#email').value.trim().toLowerCase(),phone:$('#phone').value.trim(),street:$('#street').value.trim(),zip:$('#zip').value.trim(),city:$('#city').value.trim()};if(c.firstName.length<2||c.lastName.length<2){showToast('Name prüfen','Vor- und Nachname werden benötigt.');return}if(!validEmail(c.email)){showToast('E-Mail prüfen','Bitte gib eine gültige E-Mail-Adresse ein.');return}state.customer=c;write('cpCustomer',c);state.step=3;renderDrawer()}
function renderPayment(){
  $('#drawerTitle').textContent='Zahlung';
  $('#drawerBody').innerHTML=`<div class="summary"><div class="summary-row"><span>${state.cart.length} Class Pack${state.cart.length===1?'':'s'}</span><b>${money(total())}</b></div><div class="summary-row total"><span>Zu zahlen</span><b>${money(total())}</b></div></div><p style="font-size:12px;color:#6f6a61;line-height:1.6">Wähle deine bevorzugte Zahlungsart. Verfügbare Wallets und lokale Methoden werden zusätzlich vom Gerät und Zahlungsanbieter geprüft.</p><div class="payment-list">${PAYMENT_METHODS.map(m=>`<label class="payment-option ${state.payment===m.id?'active':''}"><input type="radio" name="payment" value="${m.id}" ${state.payment===m.id?'checked':''}><div><b>${esc(m.name)}</b><small>${esc(m.hint)}</small></div><span class="pay-pill">${esc(m.badge)}</span></label>`).join('')}</div><label class="terms"><input id="terms" type="checkbox"><span>Ich akzeptiere die AGB, Widerrufs- und Datenschutzbestimmungen und stimme der sofortigen Bereitstellung digitaler Credits nach erfolgreicher Zahlung zu.</span></label><button class="drawer-action" id="payNow" type="button">Sicher bezahlen · ${money(total())}</button><button class="drawer-action secondary" id="backCustomer" type="button">Zurück</button>`;
  $$('input[name="payment"]').forEach(r=>r.addEventListener('change',()=>{state.payment=r.value;$$('.payment-option').forEach(x=>x.classList.toggle('active',x.querySelector('input').checked))}));$('#backCustomer').addEventListener('click',()=>{state.step=2;renderDrawer()});$('#payNow').addEventListener('click',submitPayment);
}
async function submitPayment(){
  if(!$('#terms').checked){showToast('Zustimmung fehlt','Bitte akzeptiere die Bedingungen.');return}
  const button=$('#payNow');button.disabled=true;button.textContent='Zahlung wird vorbereitet…';
  const order={reference:'CP-ORDER-'+token(8),currency:'eur',items:state.cart.map(id=>({id,quantity:1})),customer:state.customer,paymentMethod:state.payment,amount:total(),returnUrl:location.origin+location.pathname+'?payment=success'};
  const endpoint=state.payment==='paypal'?'/api/checkout/paypal':'/api/checkout/create';
  try{
    const response=await fetch(endpoint,{method:'POST',headers:{'content-type':'application/json','x-idempotency-key':order.reference},body:JSON.stringify(order)});
    const data=await response.json().catch(()=>({}));
    if(response.ok&&data.url){write('cpPendingOrder',order);location.href=data.url;return}
    if(response.status!==503&&response.status!==404&&response.status!==501)throw new Error(data.error||'checkout_failed');
    savePreparedOrder(order,data.code||'provider_not_connected');
  }catch(_){savePreparedOrder(order,'provider_not_connected')}
}
function savePreparedOrder(order){
  const orders=read('cpOrders',[]);orders.unshift({...order,status:'payment_provider_pending',createdAt:new Date().toISOString()});write('cpOrders',orders.slice(0,25));
  $('#drawerTitle').textContent='Checkout vorbereitet';$('#checkoutProgress').innerHTML='<span></span><span></span><span class="active">Zahlung</span>';
  $('#drawerBody').innerHTML=`<div class="confirmation"><div class="check">✓</div><h3>Der Checkout ist vollständig vorbereitet.</h3><p>Bestellung <b>${esc(order.reference)}</b> wurde gespeichert. Sobald Stripe/Wallets bzw. PayPal mit den Live-Zugangsdaten verbunden sind, führt derselbe Flow direkt zur echten Zahlung. Bis dahin wird keine Belastung ausgelöst.</p><span class="order-ref">${esc(order.reference)}</span><button class="drawer-action" id="donePrepared" type="button">Fertig</button></div>`;
  $('#donePrepared').addEventListener('click',()=>{state.cart=[];write('cpCart',[]);updateCartCount();closeCart()});
}
function handleReturn(){const q=new URLSearchParams(location.search);if(q.get('payment')==='success'){const pending=read('cpPendingOrder',null);state.cart=[];write('cpCart',[]);updateCartCount();openCart();$('#drawerTitle').textContent='Zahlung bestätigt';$('#checkoutProgress').innerHTML='<span></span><span></span><span class="active">Fertig</span>';$('#drawerBody').innerHTML=`<div class="confirmation"><div class="check">✓</div><h3>Vielen Dank.</h3><p>Deine Zahlung wurde zum Abschluss zurückgeleitet. Die serverseitige Zahlungsbestätigung aktiviert anschließend die Credits.</p>${pending?.reference?`<span class="order-ref">${esc(pending.reference)}</span>`:''}<button class="drawer-action" id="doneReturn" type="button">Zum Schedule</button></div>`;$('#doneReturn').addEventListener('click',()=>location.href='./index.html#schedule');history.replaceState({},'',location.pathname)}}

$('#cartTrigger').addEventListener('click',openCart);$('#closeDrawer').addEventListener('click',closeCart);$('#drawerBackdrop').addEventListener('click',closeCart);document.addEventListener('keydown',e=>{if(e.key==='Escape')closeCart()});
renderProducts();updateCartCount();
const incoming=new URLSearchParams(location.search).get('product');if(incoming&&PRODUCTS[incoming]){if(!state.cart.includes(incoming))state.cart.push(incoming);write('cpCart',state.cart);updateCartCount();openCart()}else handleReturn();