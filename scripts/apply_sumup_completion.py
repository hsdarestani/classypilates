from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    try:
        start_at = text.index(start)
        end_at = text.index(end, start_at)
    except ValueError as exc:
        raise SystemExit(f"{label}: marker not found: {exc}") from exc
    return text[:start_at] + replacement + text[end_at:]


root = Path(__file__).resolve().parents[1]

# --- server/main.py: durable booking linkage + safe lightweight migration ---
path = root / "server/main.py"
text = path.read_text()
text = replace_once(
    text,
    '    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True, index=True)\n    status: Mapped[str] = mapped_column(String(30), default="pending")',
    '    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True, index=True)\n    booking_reference: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)\n    status: Mapped[str] = mapped_column(String(30), default="pending")',
    "PaymentOrder booking_reference",
)
text = replace_once(
    text,
    '    if "description" not in columns:\n        with engine.begin() as connection:\n            connection.execute(text("ALTER TABLE classes ADD COLUMN description TEXT NOT NULL DEFAULT \'\'"))\n\n\nmigrate_schema()',
    '    if "description" not in columns:\n        with engine.begin() as connection:\n            connection.execute(text("ALTER TABLE classes ADD COLUMN description TEXT NOT NULL DEFAULT \'\'"))\n\n    inspector = inspect(engine)\n    if inspector.has_table("payment_orders"):\n        payment_columns = {column["name"] for column in inspector.get_columns("payment_orders")}\n        if "booking_reference" not in payment_columns:\n            with engine.begin() as connection:\n                connection.execute(text("ALTER TABLE payment_orders ADD COLUMN booking_reference VARCHAR(40)"))\n                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_payment_orders_booking_reference ON payment_orders (booking_reference)"))\n\n\nmigrate_schema()',
    "payment_orders migration",
)
path.write_text(text)

# --- server/feedback_app.py: one verified SumUp flow for shop + bookings ---
path = root / "server/feedback_app.py"
text = path.read_text()
text = replace_once(
    text,
    'import json\nfrom urllib.error import HTTPError',
    'import json\nfrom decimal import Decimal, InvalidOperation\nfrom urllib.error import HTTPError',
    "Decimal import",
)
text = replace_once(
    text,
    'class CheckoutIn(BaseModel):\n    reference: str\n    customer: CheckoutCustomer\n    items: list[CheckoutItem]\n',
    'class CheckoutIn(BaseModel):\n    reference: str\n    customer: CheckoutCustomer\n    items: list[CheckoutItem] = []\n    bookingReference: Optional[str] = None\n',
    "CheckoutIn bookingReference",
)

sync_block = '''def _checkout_origin(request: Request) -> str:\n    proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",", 1)[0].strip()\n    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc)).split(",", 1)[0].strip()\n    hostname = host.split(":", 1)[0].lower()\n    allowed_hosts = {"classy.smarbiz.sbs", "new.classypilates.de", "classypilates.de", "www.classypilates.de"}\n    if hostname not in allowed_hosts:\n        return os.getenv("PUBLIC_BASE_URL", "https://classy.smarbiz.sbs").strip().rstrip("/")\n    return f"{proto}://{host}".rstrip("/")\n\n\ndef _sumup_amount_cents(checkout: dict) -> int:\n    try:\n        amount = Decimal(str(checkout.get("amount", ""))).quantize(Decimal("0.01"))\n    except (InvalidOperation, ValueError, TypeError):\n        raise HTTPException(409, "sumup_checkout_mismatch")\n    return int(amount * 100)\n\n\ndef _sync_sumup_order(checkout: dict, db: Session, background_tasks: Optional[BackgroundTasks] = None) -> Optional[core.PaymentOrder]:\n    checkout_id = str(checkout.get("id", "")).strip()\n    if not checkout_id:\n        raise HTTPException(409, "sumup_checkout_mismatch")\n    order = db.scalar(select(core.PaymentOrder).where(core.PaymentOrder.provider_payment_id == checkout_id).with_for_update())\n    if not order:\n        return None\n    merchant = os.getenv("SUMUPMERCHANT", "").strip()\n    if not merchant:\n        raise HTTPException(503, "sumup_not_configured")\n    trusted = (\n        str(checkout.get("merchant_code", "")).strip() == merchant\n        and str(checkout.get("currency", "")).upper() == "EUR"\n        and _sumup_amount_cents(checkout) == order.amount_cents\n    )\n    if not trusted:\n        raise HTTPException(409, "sumup_checkout_mismatch")\n\n    status = str(checkout.get("status", "")).upper()\n    email_job = None\n    if status == "PAID":\n        order.status = "paid"\n        if order.booking_reference:\n            booking = db.scalar(select(core.Booking).where(core.Booking.reference == order.booking_reference).with_for_update())\n            if not booking:\n                raise HTTPException(409, "booking_not_found")\n            if booking.email.lower() != order.email.lower() or booking.amount_cents != order.amount_cents:\n                raise HTTPException(409, "booking_payment_mismatch")\n            first_paid_transition = booking.payment_status != "paid"\n            booking.payment_status = "paid"\n            booking.payment_method = "sumup"\n            booking.status = "reserved"\n            order.credited = True\n            if first_paid_transition:\n                email_job = core.booking_email_data(booking)\n        elif not order.credited:\n            user = db.scalar(select(core.User).where(func.lower(core.User.email) == order.email.lower()))\n            if user:\n                profile = db.scalar(select(core.CustomerProfile).where(core.CustomerProfile.user_id == user.id).with_for_update())\n                if not profile:\n                    profile = core.CustomerProfile(user_id=user.id)\n                    db.add(profile)\n                    db.flush()\n                profile.credits += order.credits\n                order.credited = True\n    elif status in {"FAILED", "EXPIRED", "CANCELLED", "CANCELED"} and order.status != "paid":\n        order.status = "failed" if status == "FAILED" else "cancelled"\n        if order.booking_reference:\n            booking = db.scalar(select(core.Booking).where(core.Booking.reference == order.booking_reference).with_for_update())\n            if booking and booking.payment_status != "paid":\n                booking.payment_status = "failed" if status == "FAILED" else "cancelled"\n                booking.payment_method = "sumup"\n                booking.status = "cancelled"\n    db.commit()\n    if email_job:\n        if background_tasks is not None:\n            background_tasks.add_task(core.send_transactional_email, *email_job)\n        else:\n            core.send_transactional_email(*email_job)\n    return order\n\n\n'''
text = replace_between(text, 'def _sync_sumup_order(', '@app.get("/api/checkout/create")', sync_block, "SumUp sync block")

create_block = '''@app.post("/api/checkout/create")\ndef create_sumup_checkout(data: CheckoutIn, request: Request, db: Session = Depends(core.db_session)):\n    merchant = os.getenv("SUMUPMERCHANT", "").strip()\n    if not os.getenv("SUMUPAPIKEY", "").strip() or not merchant:\n        raise HTTPException(503, "sumup_not_configured")\n    reference = data.reference.strip()[:80]\n    if not reference:\n        raise HTTPException(400, "invalid_checkout")\n\n    email = str(data.customer.email).strip().lower()\n    booking = None\n    booking_reference = (data.bookingReference or "").strip()[:40] or None\n    total = 0\n    credits = 0\n    names = []\n\n    if booking_reference:\n        booking = db.scalar(select(core.Booking).where(core.Booking.reference == booking_reference).with_for_update())\n        if not booking or booking.status != "reserved" or booking.payment_status != "pending":\n            raise HTTPException(409, "booking_not_payable")\n        if booking.email.lower() != email:\n            raise HTTPException(409, "booking_customer_mismatch")\n        if booking.amount_cents <= 0:\n            raise HTTPException(409, "booking_amount_invalid")\n        total = booking.amount_cents\n        names = [f"Class booking {booking.reference}"]\n    else:\n        if not data.items:\n            raise HTTPException(400, "invalid_checkout")\n        for item in data.items:\n            product = SHOP_PRODUCTS.get(item.id)\n            quantity = min(10, max(1, item.quantity))\n            if not product:\n                raise HTTPException(400, "unknown_product")\n            total += product["price"] * quantity\n            credits += product["credits"] * quantity\n            names.append(f"{quantity}× {product['name']}")\n\n    existing = db.scalar(select(core.PaymentOrder).where(core.PaymentOrder.reference == reference))\n    if existing:\n        if existing.email != email or existing.amount_cents != total or existing.booking_reference != booking_reference:\n            raise HTTPException(409, "reference_conflict")\n        raise HTTPException(409, "checkout_already_created")\n\n    order = core.PaymentOrder(\n        reference=reference,\n        email=email,\n        first_name=data.customer.firstName.strip(),\n        last_name=data.customer.lastName.strip(),\n        amount_cents=total,\n        credits=credits,\n        booking_reference=booking_reference,\n    )\n    db.add(order)\n    db.commit()\n\n    origin = _checkout_origin(request)\n    try:\n        checkout = _sumup_request("/v0.1/checkouts", method="POST", payload={\n            "checkout_reference": reference,\n            "amount": float(Decimal(total) / Decimal(100)),\n            "currency": "EUR",\n            "merchant_code": merchant,\n            "description": ("Classy Pilates · " + ", ".join(names))[:255],\n            "redirect_url": f"{origin}/api/checkout/sumup-return?reference={reference}",\n            "hosted_checkout": {"enabled": True},\n        })\n        if not checkout.get("id") or not checkout.get("hosted_checkout_url"):\n            raise HTTPException(502, "sumup_checkout_incomplete")\n        order.provider_payment_id = str(checkout["id"])\n        db.commit()\n        return {\n            "ok": True,\n            "provider": "sumup",\n            "hosted_checkout_url": checkout["hosted_checkout_url"],\n            "url": checkout["hosted_checkout_url"],\n            "checkoutId": checkout["id"],\n            "reference": reference,\n            "bookingReference": booking_reference,\n        }\n    except HTTPException:\n        order.status = "failed"\n        if booking_reference:\n            booking = db.scalar(select(core.Booking).where(core.Booking.reference == booking_reference).with_for_update())\n            if booking and booking.payment_status == "pending":\n                booking.payment_status = "failed"\n                booking.payment_method = "sumup"\n                booking.status = "cancelled"\n        db.commit()\n        raise\n\n\n'''
text = replace_between(text, '@app.post("/api/checkout/create")', '@app.post("/api/checkout/sumup-return"', create_block, "checkout create block")

return_block = '''@app.post("/api/checkout/sumup-return", status_code=204)\ndef sumup_webhook(event: dict, background_tasks: BackgroundTasks, db: Session = Depends(core.db_session)):\n    checkout_id = str(event.get("id") or event.get("checkout_id") or "").strip()\n    if not checkout_id:\n        reference = str(event.get("checkout_reference") or "").strip()[:80]\n        if reference:\n            order = db.scalar(select(core.PaymentOrder).where(core.PaymentOrder.reference == reference))\n            checkout_id = order.provider_payment_id if order and order.provider_payment_id else ""\n    if not checkout_id:\n        return Response(status_code=204)\n    checkout = _sumup_request(f"/v0.1/checkouts/{checkout_id}")\n    _sync_sumup_order(checkout, db, background_tasks)\n    return Response(status_code=204)\n\n\n@app.get("/api/checkout/sumup-return")\ndef sumup_return(reference: str, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(core.db_session)):\n    origin = _checkout_origin(request)\n    order = db.scalar(select(core.PaymentOrder).where(core.PaymentOrder.reference == reference[:80]))\n    if not order or not order.provider_payment_id:\n        return RedirectResponse(f"{origin}/shop?payment=failed&provider=sumup")\n    try:\n        checkout = _sumup_request(f"/v0.1/checkouts/{order.provider_payment_id}")\n        synced = _sync_sumup_order(checkout, db, background_tasks)\n        state = synced.status if synced else "failed"\n        payment = "success" if state == "paid" else ("failed" if state in {"failed", "cancelled"} else "pending")\n    except HTTPException:\n        payment = "pending"\n\n    if order.booking_reference:\n        return RedirectResponse(\n            f"{origin}/?payment={payment}&provider=sumup&flow=booking&bookingReference={order.booking_reference}&reference={order.reference}#schedule"\n        )\n    return RedirectResponse(f"{origin}/shop?payment={payment}&provider=sumup&reference={order.reference}")\n\n\n'''
text = replace_between(text, '@app.post("/api/checkout/sumup-return"', 'def _drop_route(', return_block, "SumUp callback/return block")

text = replace_once(
    text,
    '        payment_method="class_credit" if use_credit else data.paymentMethod,\n        payment_status="paid" if use_credit else "pending", amount_cents=0 if use_credit else (2800 if data.paymentMethod else 0),',
    '        payment_method="class_credit" if use_credit else "sumup",\n        payment_status="paid" if use_credit else "pending", amount_cents=0 if use_credit else 2800,',
    "booking payment method",
)
path.write_text(text)

# --- public/booking-flow.js: remove demo flow and redirect unpaid bookings to real SumUp ---
path = root / "public/booking-flow.js"
text = path.read_text()
text = replace_once(text, '  const PRESENTATION_PAYMENT=true;\n', '', "presentation flag")
booking_payment_block = r'''  function renderPaymentStep(){
    setDrawer('Choose payment',`${classSummary(wizard.class)}<div class="checkout-mini-summary"><div><span>SPOT</span><b>${safe(spotLabel(wizard.spot,wizard.class))}</b></div><div><span>PAYMENT</span><b>1 Class Credit or 28,00 €</b></div></div><div class="wizard-panel"><div class="wizard-kicker">SECURE PAYMENT</div><h4>Confirm your booking.</h4><p>If your Classy account has an available credit, it will be used automatically. Otherwise you will continue to the secure SumUp checkout.</p><div class="wizard-payment-grid">${payMethods.map(m=>`<button type="button" class="wizard-pay ${wizard.payment===m.id?'active':''}" data-wpay="${m.id}"><span class="pay-mark">${safe(m.mark)}</span><span><b>${safe(m.name)}</b><small>${safe(m.detail)}</small></span><i>${wizard.payment===m.id?'✓':''}</i></button>`).join('')}</div><div class="wizard-sticky-actions"><button class="drawer-action secondary" id="backDetails">Back</button><button class="drawer-action" id="finishPayment">Confirm & continue</button></div></div>`,4);
    $$('[data-wpay]').forEach(b=>b.addEventListener('click',()=>{wizard.payment=b.dataset.wpay;renderPaymentStep()}));$('#backDetails')?.addEventListener('click',renderDetailsStep);$('#finishPayment')?.addEventListener('click',processPayment)
  }

  function processPayment(){const btn=$('#finishPayment');if(btn){btn.disabled=true;btn.innerHTML='<span class="button-spinner"></span> Preparing secure payment…'}completeBookingPayment()}
  function bookingRefV2(){return 'CP-'+(cryptoSafeToken?cryptoSafeToken(8):Math.random().toString(36).slice(2,10).toUpperCase())}
  function checkoutRefV2(){return 'CP-BOOKPAY-'+(cryptoSafeToken?cryptoSafeToken(10):Math.random().toString(36).slice(2,12).toUpperCase())}
  async function accountRequest(path,body){const response=await fetch(path,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'content-type':'application/json'},body:JSON.stringify(body)});let data={};try{data=await response.json()}catch(_){}if(!response.ok)throw new Error(data.detail||'request_failed');return data}
  async function authenticateCustomer(){const details=wizard.details;let result;if(wizard.mode==='register'){try{result=await accountRequest('/api/auth/register',{email:details.email,password:details.password,first_name:details.firstName,last_name:details.lastName,phone:details.phone,birth_date:details.birth,emergency_contact:details.emergency,marketing_opt_in:details.news})}catch(error){if(error.message!=='email_exists')throw error;result=await accountRequest('/api/auth/login',{email:details.email,password:details.password})}}else{result=await accountRequest('/api/auth/login',{email:details.email,password:details.password})}if(result.user?.portal!=='/account')throw new Error('customer_account_required');return result.user}
  async function createServerBooking(r,user){const startsAt=new Date(`${r.date}T${r.time}:00`).toISOString();const classId=Number.isInteger(Number(r.id))?Number(r.id):String(r.id);const response=await fetch('/api/bookings',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'content-type':'application/json'},body:JSON.stringify({classId,email:user.email,firstName:user.first_name||wizard.details.firstName||'',lastName:user.last_name||wizard.details.lastName||'',phone:wizard.details.phone||'',spot:wizard.spot,paymentMethod:'sumup',studioId:r.studio,title:r.name,classType:r.type,startsAt,duration:r.duration,capacity:r.capacity,coachName:r.coach})});let data={};try{data=await response.json()}catch(_){}if(!response.ok)throw new Error(data.detail||'booking_failed');return data}
  function saveLocalBooking(r,email,ref,paymentState,paymentMethod,adjust=true){const existing=read('cpBookings',[]);if(!existing.some(b=>b.ref===ref)){existing.unshift({ref,email,classId:r.id,name:r.name,time:r.time,date:r.date,studio:studioName(r),studioId:r.studio,coach:r.coach,spot:spotLabel(wizard.spot,r),spotNumber:wizard.spot,paymentMethod,status:'reserved',paymentState,createdAt:new Date().toISOString()});write('cpBookings',existing.slice(0,50));if(adjust){try{adjustSeats(r.id,-1)}catch(_){}}}try{localStorage.setItem('cpLastEmail',email)}catch(_){}}
  async function createBookingCheckout(bookingReference,user){const reference=checkoutRefV2();const response=await fetch('/api/checkout/create',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'content-type':'application/json','x-idempotency-key':reference},body:JSON.stringify({reference,bookingReference,customer:{email:user.email,firstName:user.first_name||wizard.details.firstName||'',lastName:user.last_name||wizard.details.lastName||''},items:[]})});let data={};try{data=await response.json()}catch(_){}const url=data.hosted_checkout_url||data.url;if(!response.ok||!url)throw new Error(data.detail||'checkout_failed');return {reference,url}}
  async function completeBookingPayment(){
    const r=wizard.class,email=wizard.details.email;try{const user=await authenticateCustomer();const result=await createServerBooking(r,user);const ref=result.booking?.reference||bookingRefV2();if(result.credit_used||result.payment_status==='paid'){wizard.payment='class_credit';saveLocalBooking(r,email,ref,'paid','class_credit');renderSchedule();renderSuccess(ref);return}if(!result.booking?.reference)throw new Error('booking_failed');const checkout=await createBookingCheckout(result.booking.reference,user);write('cpPendingBookingPayment',{bookingReference:result.booking.reference,orderReference:checkout.reference,email,wizard:{class:r,spot:wizard.spot,payment:'sumup',details:{email,firstName:user.first_name||wizard.details.firstName||'',lastName:user.last_name||wizard.details.lastName||'',phone:wizard.details.phone||''}}});location.href=checkout.url}catch(error){const map={invalid_credentials:'Email or password is incorrect.',duplicate_booking:'You have already booked this class.',class_full:'This class is now sold out.',spot_taken:'This spot was just taken.',customer_account_required:'Please use a customer account.',password_too_short:'The password must be at least 8 characters.',sumup_not_configured:'Secure payment is currently unavailable.',sumup_unavailable:'SumUp is currently unavailable. Please try again.',checkout_failed:'Secure payment could not be started.'};showToast('Booking not completed',map[error.message]||'Check your details and try again. No payment was confirmed.');renderPaymentStep()}
  }
'''
text = replace_between(text, '  function renderPaymentStep(){', '  function calendarHref(){', booking_payment_block, "booking frontend payment block")
text = replace_once(
    text,
    "  function renderSuccess(ref){const method=payMethods.find(x=>x.id===wizard.payment)?.name||wizard.payment;",
    "  function renderSuccess(ref){const method=wizard.payment==='class_credit'?'Class Credit':(payMethods.find(x=>x.id===wizard.payment)?.name||wizard.payment);",
    "success payment label",
)
return_handler = r'''  function handleBookingPaymentReturn(){
    const q=new URLSearchParams(location.search);if(q.get('flow')!=='booking')return false;const payment=q.get('payment')||'pending',ref=q.get('bookingReference')||'',pending=read('cpPendingBookingPayment',null);if(payment==='success'&&pending&&pending.bookingReference===ref){wizard={...pending.wizard,payment:'sumup'};saveLocalBooking(wizard.class,pending.email,ref,'paid','sumup',false);try{localStorage.removeItem('cpPendingBookingPayment')}catch(_){}renderSchedule();setTimeout(()=>renderSuccess(ref),80)}else{if(payment==='failed'){showToast('Payment not completed','SumUp did not confirm the payment. The pending booking has been cancelled.')}else{showToast('Payment is processing','No successful payment has been confirmed yet. Please check your account before trying again.')}}history.replaceState({},'',location.pathname+(location.hash||'#schedule'));return true
  }

'''
text = replace_once(text, '  const originalOpenClass=', return_handler + '  const originalOpenClass=', "booking return handler")
text = replace_once(
    text,
    '  moveStudiosBeforeSchedule();addQuickDock();observeDynamicUi();loadCoachPhotos();\n',
    '  moveStudiosBeforeSchedule();addQuickDock();observeDynamicUi();loadCoachPhotos();handleBookingPaymentReturn();\n',
    "booking return bootstrap",
)
path.write_text(text)

# --- public/shop.js: no fake/provider-not-connected success fallback ---
path = root / "public/shop.js"
text = path.read_text()
shop_submit = r'''async function submitPayment(){
  if(!$('#terms').checked){showToast('Consent required','Please accept the terms.');return}
  const button=$('#payNow');button.disabled=true;button.textContent='Preparing payment…';
  const order={reference:'CP-ORDER-'+token(8),items:state.cart.map(id=>({id,quantity:1})),customer:state.customer};
  try{
    const response=await fetch('/api/checkout/create',{method:'POST',headers:{'content-type':'application/json','x-idempotency-key':order.reference},body:JSON.stringify(order)});
    const data=await response.json().catch(()=>({}));const url=data.hosted_checkout_url||data.url;
    if(response.ok&&url){write('cpPendingOrder',order);location.href=url;return}
    throw new Error(data.detail||'checkout_failed');
  }catch(error){button.disabled=false;button.textContent='Pay securely · '+money(total());const unavailable=['sumup_not_configured','sumup_unavailable','sumup_request_failed'].includes(error.message);showToast(unavailable?'Payment unavailable':'Payment not started',unavailable?'SumUp is currently unavailable. No order has been marked as paid.':'Secure checkout could not be started. Please try again.');}
}
'''
text = replace_between(text, 'async function submitPayment(){', 'function handleReturn(){', shop_submit, "shop real checkout")
path.write_text(text)

# --- deploy workflow: keep secret propagation, add payment capability smoke tests and mask derived secret values ---
path = root / ".github/workflows/deploy-production.yml"
text = path.read_text()
text = replace_once(
    text,
    '          SUMUPAPIKEY_B64="$(printf \'%s\' "$SUMUPAPIKEY" | base64 -w0)"\n          SUMUPMERCHANT_B64="$(printf \'%s\' "$SUMUPMERCHANT" | base64 -w0)"\n          sshpass -e ssh',
    '          SUMUPAPIKEY_B64="$(printf \'%s\' "$SUMUPAPIKEY" | base64 -w0)"\n          SUMUPMERCHANT_B64="$(printf \'%s\' "$SUMUPMERCHANT" | base64 -w0)"\n          echo "::add-mask::$SUMUPAPIKEY_B64"\n          echo "::add-mask::$SUMUPMERCHANT_B64"\n          sshpass -e ssh',
    "mask encoded SumUp secrets",
)
text = replace_once(
    text,
    '          curl -fsS http://127.0.0.1:8787/api/health\n\n          # The importer uses SQLAlchemy Core only, so it can safely run beside',
    '          curl -fsS http://127.0.0.1:8787/api/health\n          curl -fsS http://127.0.0.1:8787/api/checkout/create | grep -q \'"provider":"sumup"\'\n\n          # The importer uses SQLAlchemy Core only, so it can safely run beside',
    "internal checkout smoke",
)
text = replace_once(
    text,
    '          curl -fsSL --max-time 20 https://classy.smarbiz.sbs/api/health | grep -q \'"ok":true\'\n',
    '          curl -fsSL --max-time 20 https://classy.smarbiz.sbs/api/health | grep -q \'"ok":true\'\n          curl -fsSL --max-time 20 https://classy.smarbiz.sbs/api/checkout/create | grep -q \'"provider":"sumup"\'\n',
    "public checkout smoke",
)
path.write_text(text)

# Guardrails for the requested runtime cleanup.
for runtime in [root / "server", root / "public"]:
    for candidate in runtime.rglob("*"):
        if candidate.is_file() and candidate.suffix in {".py", ".js", ".html", ".css"}:
            body = candidate.read_text(errors="ignore")
            if "stripe" in body.lower():
                raise SystemExit(f"runtime Stripe reference remains in {candidate.relative_to(root)}")

booking_js = (root / "public/booking-flow.js").read_text()
shop_js = (root / "public/shop.js").read_text()
for forbidden in ["PRESENTATION_PAYMENT", "Payment is simulated", "No real charge", "Confirm demo payment", "completeDemoBooking"]:
    if forbidden in booking_js:
        raise SystemExit(f"demo booking text/logic remains: {forbidden}")
for forbidden in ["savePreparedOrder", "provider_not_connected", "Checkout ready", "No charge is made until then"]:
    if forbidden in shop_js:
        raise SystemExit(f"fake shop fallback remains: {forbidden}")

print("SumUp completion patch applied successfully")
