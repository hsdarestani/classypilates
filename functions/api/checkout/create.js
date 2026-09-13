const CATALOG={single:{name:'1 Class',price:2800,credits:1},five:{name:'5 Classes',price:11900,credits:5},ten:{name:'10 Classes',price:21900,credits:10},twenty:{name:'20 Classes',price:39900,credits:20}};
const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const validEmail=v=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v||''));

export async function onRequestPost({request,env}){
  if(!env.SUMUPAPIKEY||!env.SUMUPMERCHANT)return json({ok:false,code:'sumup_not_configured',message:'SumUp live credentials are not connected yet.'},503);
  if(!env.DB)return json({ok:false,code:'db_not_configured',message:'The order database is not connected.'},503);
  let body;try{body=await request.json()}catch(_){return json({ok:false,error:'invalid_json'},400)}
  const email=String(body?.customer?.email||'').trim().toLowerCase();if(!validEmail(email))return json({ok:false,error:'invalid_email'},400);
  const rawItems=Array.isArray(body.items)?body.items:[];if(!rawItems.length)return json({ok:false,error:'empty_cart'},400);
  const items=[];let total=0;
  for(const row of rawItems){const product=CATALOG[row.id];const qty=Math.max(1,Math.min(10,Number(row.quantity)||1));if(!product)return json({ok:false,error:'unknown_product'},400);items.push({id:row.id,qty,...product});total+=product.price*qty}
  const reference=String(body.reference||'').trim().slice(0,80);if(!reference)return json({ok:false,error:'missing_reference'},400);
  const origin=new URL(request.url).origin;
  const checkoutResponse=await fetch('https://api.sumup.com/v0.1/checkouts',{method:'POST',headers:{authorization:`Bearer ${env.SUMUPAPIKEY}`,'content-type':'application/json'},body:JSON.stringify({
    checkout_reference:reference,
    amount:Number((total/100).toFixed(2)),
    currency:'EUR',
    merchant_code:env.SUMUPMERCHANT,
    description:`Classy Pilates · ${items.map(item=>`${item.qty}× ${item.name}`).join(', ')}`.slice(0,255),
    return_url:`${origin}/api/checkout/sumup-return`,
    redirect_url:`${origin}/api/checkout/sumup-return?reference=${encodeURIComponent(reference)}`,
    hosted_checkout:{enabled:true}
  })});
  const result=await checkoutResponse.json().catch(()=>({}));
  if(!checkoutResponse.ok)return json({ok:false,error:'sumup_checkout_failed',details:result?.message||result?.error_message||'SumUp rejected the checkout.'},502);
  if(!result.id||!result.hosted_checkout_url)return json({ok:false,error:'sumup_checkout_incomplete'},502);
  if(env.DB){
    try{
      const existing=await env.DB.prepare(`SELECT id,amount_cents,email FROM orders WHERE reference=? LIMIT 1`).bind(reference).first();
      if(existing){
        if(Number(existing.amount_cents)!==total||String(existing.email).toLowerCase()!==email)return json({ok:false,error:'reference_conflict'},409);
        await env.DB.prepare(`UPDATE orders SET provider='sumup',provider_payment_id=?,payment_method='hosted_checkout',updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'`).bind(result.id,existing.id).run();
      }else{
        const orderId=crypto.randomUUID();
        const statements=[env.DB.prepare(`INSERT INTO orders(id,reference,email,first_name,last_name,amount_cents,currency,provider,provider_payment_id,payment_method,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)`).bind(orderId,reference,email,String(body?.customer?.firstName||''),String(body?.customer?.lastName||''),total,'eur','sumup',result.id,'hosted_checkout','pending')];
        items.forEach(item=>statements.push(env.DB.prepare(`INSERT INTO order_items(id,order_id,product_id,product_name,quantity,unit_price_cents,credits) VALUES(?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),orderId,item.id,item.name,item.qty,item.price,item.credits)));
        await env.DB.batch(statements);
      }
    }catch(error){return json({ok:false,error:'order_persistence_failed',details:String(error?.message||error)},500)}
  }
  return json({ok:true,url:result.hosted_checkout_url,checkoutId:result.id,reference});
}

export function onRequestGet(){return json({ok:true,provider:'sumup',flow:'hosted_checkout'})}
