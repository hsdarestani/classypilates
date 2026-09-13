from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)


root = Path(__file__).resolve().parents[1]

# Backend: register a real SumUp webhook callback and expose a server-verified status endpoint.
path = root / "server/feedback_app.py"
text = path.read_text()
text = replace_once(
    text,
    '            "description": ("Classy Pilates · " + ", ".join(names))[:255],\n            "redirect_url": f"{origin}/api/checkout/sumup-return?reference={reference}",',
    '            "description": ("Classy Pilates · " + ", ".join(names))[:255],\n            "return_url": f"{origin}/api/checkout/sumup-return",\n            "redirect_url": f"{origin}/api/checkout/sumup-return?reference={reference}",',
    "SumUp return_url",
)
text = replace_once(
    text,
    '    except HTTPException:\n        payment = "pending"\n\n    if order.booking_reference:',
    '    except HTTPException as exc:\n        payment = "pending" if exc.status_code in {502, 503} else "failed"\n\n    if order.booking_reference:',
    "verified return error mapping",
)
marker = '\n\ndef _drop_route(path: str, method: str):\n'
status_endpoint = '''\n\n@app.get("/api/checkout/status")\ndef checkout_status(reference: str, background_tasks: BackgroundTasks, db: Session = Depends(core.db_session)):\n    normalized = reference.strip()[:80]\n    if not normalized:\n        raise HTTPException(400, "invalid_reference")\n    order = db.scalar(select(core.PaymentOrder).where(core.PaymentOrder.reference == normalized))\n    if not order:\n        raise HTTPException(404, "payment_order_not_found")\n    if order.provider_payment_id:\n        checkout = _sumup_request(f"/v0.1/checkouts/{order.provider_payment_id}")\n        synced = _sync_sumup_order(checkout, db, background_tasks)\n        if synced:\n            order = synced\n    return {\n        "ok": True,\n        "provider": "sumup",\n        "reference": order.reference,\n        "bookingReference": order.booking_reference,\n        "status": order.status,\n        "paid": order.status == "paid",\n    }\n'''
if marker not in text:
    raise SystemExit("status endpoint marker missing")
text = text.replace(marker, status_endpoint + marker, 1)
path.write_text(text)

# Shop: query string identifies the returned order only; paid state comes from the server/API verification.
path = root / "public/shop.js"
text = path.read_text()
old = "function handleReturn(){const q=new URLSearchParams(location.search);const payment=q.get('payment');if(payment==='success'){const pending=read('cpPendingOrder',null);state.cart=[];write('cpCart',[]);updateCartCount();openCart();$('#drawerTitle').textContent='Payment confirmed';$('#checkoutProgress').innerHTML='<span></span><span></span><span class=\"active\">Done</span>';$('#drawerBody').innerHTML=`<div class=\"confirmation\"><div class=\"check\">✓</div><h3>Thank you.</h3><p>Your SumUp payment is confirmed and your class credits are ready.</p>${(q.get('reference')||pending?.reference)?`<span class=\"order-ref\">${esc(q.get('reference')||pending.reference)}</span>`:''}<button class=\"drawer-action\" id=\"doneReturn\" type=\"button\">Go to schedule</button></div>`;$('#doneReturn').addEventListener('click',()=>location.href='/#schedule');history.replaceState({},'',location.pathname)}else if(payment==='failed'||payment==='pending'){openCart();state.step=3;renderPayment();showToast(payment==='failed'?'Payment not completed':'Payment is processing',payment==='failed'?'No payment was confirmed. Please try again.':'Please wait a moment and check your account before retrying.');history.replaceState({},'',location.pathname)}}"
new = "async function handleReturn(){const q=new URLSearchParams(location.search),pending=read('cpPendingOrder',null),reference=q.get('reference')||pending?.reference||'';if(!reference)return;let verified='pending';try{const response=await fetch('/api/checkout/status?reference='+encodeURIComponent(reference),{credentials:'same-origin',cache:'no-store'});const data=await response.json().catch(()=>({}));if(response.ok)verified=data.status||'pending';else if(response.status===404)verified='failed'}catch(_){}if(verified==='paid'){state.cart=[];write('cpCart',[]);try{localStorage.removeItem('cpPendingOrder')}catch(_){}updateCartCount();openCart();$('#drawerTitle').textContent='Payment confirmed';$('#checkoutProgress').innerHTML='<span></span><span></span><span class=\"active\">Done</span>';$('#drawerBody').innerHTML=`<div class=\"confirmation\"><div class=\"check\">✓</div><h3>Thank you.</h3><p>Your SumUp payment is confirmed and your class credits are ready.</p><span class=\"order-ref\">${esc(reference)}</span><button class=\"drawer-action\" id=\"doneReturn\" type=\"button\">Go to schedule</button></div>`;$('#doneReturn').addEventListener('click',()=>location.href='/#schedule')}else{openCart();state.step=3;renderPayment();const failed=['failed','cancelled'].includes(verified);showToast(failed?'Payment not completed':'Payment is processing',failed?'SumUp did not confirm the payment. Please try again.':'No successful payment has been confirmed yet. Please check again before retrying.')}history.replaceState({},'',location.pathname)}"
text = replace_once(text, old, new, "shop verified return")
path.write_text(text)

# Booking: verified status is fetched server-side; a lost localStorage context still shows the verified paid reference.
path = root / "public/booking-flow.js"
text = path.read_text()
old = "  function handleBookingPaymentReturn(){\n    const q=new URLSearchParams(location.search);if(q.get('flow')!=='booking')return false;const payment=q.get('payment')||'pending',ref=q.get('bookingReference')||'',pending=read('cpPendingBookingPayment',null);if(payment==='success'&&pending&&pending.bookingReference===ref){wizard={...pending.wizard,payment:'sumup'};saveLocalBooking(wizard.class,pending.email,ref,'paid','sumup',false);try{localStorage.removeItem('cpPendingBookingPayment')}catch(_){}renderSchedule();setTimeout(()=>renderSuccess(ref),80)}else{if(payment==='failed'){showToast('Payment not completed','SumUp did not confirm the payment. The pending booking has been cancelled.')}else{showToast('Payment is processing','No successful payment has been confirmed yet. Please check your account before trying again.')}}history.replaceState({},'',location.pathname+(location.hash||'#schedule'));return true\n  }"
new = "  async function handleBookingPaymentReturn(){\n    const q=new URLSearchParams(location.search);if(q.get('flow')!=='booking')return false;const pending=read('cpPendingBookingPayment',null),orderRef=q.get('reference')||pending?.orderReference||'';let verified='pending',ref=q.get('bookingReference')||pending?.bookingReference||'';if(orderRef){try{const response=await fetch('/api/checkout/status?reference='+encodeURIComponent(orderRef),{credentials:'same-origin',cache:'no-store'});const data=await response.json().catch(()=>({}));if(response.ok){verified=data.status||'pending';ref=data.bookingReference||ref}else if(response.status===404)verified='failed'}catch(_){}}if(verified==='paid'&&ref){if(pending&&pending.bookingReference===ref){wizard={...pending.wizard,payment:'sumup'};saveLocalBooking(wizard.class,pending.email,ref,'paid','sumup',false);try{localStorage.removeItem('cpPendingBookingPayment')}catch(_){}renderSchedule();setTimeout(()=>renderSuccess(ref),80)}else{setDrawer('Booking confirmed',`<div class=\"booking-success-v2\"><div class=\"success-orbit\"><span>✓</span></div><p class=\"eyebrow\">PAYMENT VERIFIED</p><h3>Your booking is confirmed.</h3><p class=\"success-lead\">SumUp confirmed the payment. Your paid booking reference is shown below.</p><div class=\"success-grid\"><div><span>PAYMENT</span><b>SumUp</b></div><div><span>BOOKING</span><b>${safe(ref)}</b></div></div><div class=\"success-actions\"><a class=\"drawer-action\" href=\"/account\">Open My Classy</a><button class=\"drawer-action secondary\" id=\"doneV2\">Done</button></div></div>`,5);$('#doneV2')?.addEventListener('click',closeDrawer)}}else{const failed=['failed','cancelled'].includes(verified);showToast(failed?'Payment not completed':'Payment is processing',failed?'SumUp did not confirm the payment. The pending booking has been cancelled.':'No successful payment has been confirmed yet. Please check your account before trying again.')}history.replaceState({},'',location.pathname+(location.hash||'#schedule'));return true\n  }"
text = replace_once(text, old, new, "booking verified return")
path.write_text(text)

print("Final SumUp verification hardening applied")
