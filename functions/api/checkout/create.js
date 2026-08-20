const CATALOG={single:{name:'1 Class',price:2800,credits:1},five:{name:'5 Classes',price:11900,credits:5},ten:{name:'10 Classes',price:21900,credits:10},twenty:{name:'20 Classes',price:39900,credits:20}};
const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const validEmail=v=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v||''));

export async function onRequestPost({request,env}){
  if(!env.STRIPE_SECRET_KEY)return json({ok:false,code:'stripe_not_configured',message:'Stripe live credentials are not connected yet.'},503);
  let body;try{body=await request.json()}catch(_){return json({ok:false,error:'invalid_json'},400)}
  const email=String(body?.customer?.email||'').trim().toLowerCase();if(!validEmail(email))return json({ok:false,error:'invalid_email'},400);
  const rawItems=Array.isArray(body.items)?body.items:[];if(!rawItems.length)return json({ok:false,error:'empty_cart'},400);
  const items=[];let total=0;
  for(const row of rawItems){const product=CATALOG[row.id];const qty=Math.max(1,Math.min(10,Number(row.quantity)||1));if(!product)return json({ok:false,error:'unknown_product'},400);items.push({id:row.id,qty,...product});total+=product.price*qty}
  const reference=String(body.reference||'').slice(0,80);if(!reference)return json({ok:false,error:'missing_reference'},400);
  const origin=new URL(request.url).origin;
  const params=new URLSearchParams();params.set('mode','payment');params.set('customer_email',email);params.set('success_url',`${origin}/shop.html?payment=success&session_id={CHECKOUT_SESSION_ID}`);params.set('cancel_url',`${origin}/shop.html?payment=cancelled`);params.set('automatic_payment_methods[enabled]','true');params.set('metadata[order_reference]',reference);params.set('metadata[source]','classy-webshop');
  items.forEach((item,i)=>{params.set(`line_items[${i}][quantity]`,String(item.qty));params.set(`line_items[${i}][price_data][currency]`,'eur');params.set(`line_items[${i}][price_data][unit_amount]`,String(item.price));params.set(`line_items[${i}][price_data][product_data][name]`,item.name)});
  const stripe=await fetch('https://api.stripe.com/v1/checkout/sessions',{method:'POST',headers:{authorization:`Bearer ${env.STRIPE_SECRET_KEY}`,'content-type':'application/x-www-form-urlencoded','Idempotency-Key':request.headers.get('x-idempotency-key')||reference},body:params});
  const result=await stripe.json().catch(()=>({}));if(!stripe.ok)return json({ok:false,error:'stripe_checkout_failed',details:result?.error?.message||'Unknown Stripe error'},502);
  if(env.DB){try{const orderId=crypto.randomUUID();const statements=[env.DB.prepare(`INSERT OR IGNORE INTO orders(id,reference,email,first_name,last_name,amount_cents,currency,provider,provider_payment_id,payment_method,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)`).bind(orderId,reference,email,String(body?.customer?.firstName||''),String(body?.customer?.lastName||''),total,'eur','stripe',result.id,String(body.paymentMethod||'automatic'),'pending')];items.forEach(item=>statements.push(env.DB.prepare(`INSERT INTO order_items(id,order_id,product_id,product_name,quantity,unit_price_cents,credits) VALUES(?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),orderId,item.id,item.name,item.qty,item.price,item.credits)));await env.DB.batch(statements)}catch(_){}}
  return json({ok:true,url:result.url,sessionId:result.id,reference});
}

export function onRequestGet(){return json({ok:true,provider:'stripe',methods:['card','apple_pay','google_pay','klarna','sepa_debit','link'],note:'Actual availability is determined by Stripe account settings, customer eligibility and browser/device.'})}