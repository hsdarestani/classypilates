const CATALOG={single:{name:'1 Class',price:2800},five:{name:'5 Classes',price:11900},ten:{name:'10 Classes',price:21900},twenty:{name:'20 Classes',price:39900}};
const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const money=c=>((c/100).toFixed(2));

export async function onRequestPost({request,env}){
  if(!env.PAYPAL_CLIENT_ID||!env.PAYPAL_CLIENT_SECRET)return json({ok:false,code:'paypal_not_configured',message:'PayPal live credentials are not connected yet.'},503);
  let body;try{body=await request.json()}catch(_){return json({ok:false,error:'invalid_json'},400)}
  const items=Array.isArray(body.items)?body.items:[];if(!items.length)return json({ok:false,error:'empty_cart'},400);
  let total=0;for(const row of items){const p=CATALOG[row.id];if(!p)return json({ok:false,error:'unknown_product'},400);total+=p.price*Math.max(1,Number(row.quantity)||1)}
  const reference=String(body.reference||'').slice(0,80);if(!reference)return json({ok:false,error:'missing_reference'},400);
  const base=String(env.PAYPAL_ENV||'sandbox').toLowerCase()==='live'?'https://api-m.paypal.com':'https://api-m.sandbox.paypal.com';
  const auth=btoa(`${env.PAYPAL_CLIENT_ID}:${env.PAYPAL_CLIENT_SECRET}`);
  const tokenResp=await fetch(`${base}/v1/oauth2/token`,{method:'POST',headers:{authorization:`Basic ${auth}`,'content-type':'application/x-www-form-urlencoded'},body:'grant_type=client_credentials'});const token=await tokenResp.json().catch(()=>({}));if(!tokenResp.ok||!token.access_token)return json({ok:false,error:'paypal_auth_failed'},502);
  const origin=new URL(request.url).origin;
  const orderResp=await fetch(`${base}/v2/checkout/orders`,{method:'POST',headers:{authorization:`Bearer ${token.access_token}`,'content-type':'application/json','PayPal-Request-Id':request.headers.get('x-idempotency-key')||reference},body:JSON.stringify({intent:'CAPTURE',purchase_units:[{reference_id:reference,custom_id:reference,description:'Classy Pilates Class Packs',amount:{currency_code:'EUR',value:money(total)}}],payment_source:{paypal:{experience_context:{brand_name:'Classy Pilates',shipping_preference:'NO_SHIPPING',user_action:'PAY_NOW',return_url:`${origin}/shop.html?payment=success&provider=paypal`,cancel_url:`${origin}/shop.html?payment=cancelled&provider=paypal`}}}})});
  const result=await orderResp.json().catch(()=>({}));if(!orderResp.ok)return json({ok:false,error:'paypal_order_failed',details:result},502);const approval=(result.links||[]).find(x=>x.rel==='payer-action'||x.rel==='approve');if(!approval?.href)return json({ok:false,error:'paypal_approval_url_missing'},502);
  if(env.DB){try{await env.DB.prepare(`INSERT OR IGNORE INTO orders(id,reference,email,first_name,last_name,amount_cents,currency,provider,provider_payment_id,payment_method,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),reference,String(body?.customer?.email||'').toLowerCase(),String(body?.customer?.firstName||''),String(body?.customer?.lastName||''),total,'eur','paypal',result.id,'paypal','pending').run()}catch(_){}}
  return json({ok:true,url:approval.href,orderId:result.id,reference});
}

export function onRequestGet(){return json({ok:true,provider:'paypal'})}