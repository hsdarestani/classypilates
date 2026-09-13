const redirect=(url,status=302)=>new Response(null,{status,headers:{location:url,'cache-control':'no-store'}});
const empty=status=>new Response(null,{status,headers:{'cache-control':'no-store'}});

async function retrieveCheckout(env,id){
  if(!env.SUMUPAPIKEY||!id)return null;
  const response=await fetch(`https://api.sumup.com/v0.1/checkouts/${encodeURIComponent(id)}`,{headers:{authorization:`Bearer ${env.SUMUPAPIKEY}`}});
  if(!response.ok)throw new Error(`sumup_retrieve_${response.status}`);
  return response.json();
}

async function syncOrder(env,checkout){
  if(!env.DB||!checkout?.id)return;
  const order=await env.DB.prepare(`SELECT id,email,status,amount_cents,currency FROM orders WHERE provider='sumup' AND provider_payment_id=? LIMIT 1`).bind(checkout.id).first();
  if(!order)return;
  const trusted=String(checkout.merchant_code||'')===String(env.SUMUPMERCHANT||'')&&String(checkout.currency||'').toUpperCase()===String(order.currency||'').toUpperCase()&&Math.round(Number(checkout.amount)*100)===Number(order.amount_cents);
  if(!trusted)throw new Error('sumup_checkout_mismatch');
  if(checkout.status==='PAID'&&order.status!=='paid'){
    const credits=await env.DB.prepare(`SELECT COALESCE(SUM(quantity*COALESCE(credits,0)),0) AS total FROM order_items WHERE order_id=?`).bind(order.id).first();
    const statements=[env.DB.prepare(`UPDATE orders SET status='paid',updated_at=CURRENT_TIMESTAMP WHERE id=? AND status<>'paid'`).bind(order.id)];
    if(Number(credits?.total||0)>0)statements.push(env.DB.prepare(`INSERT INTO credit_ledger(id,email,order_id,delta,reason) SELECT ?,?,?,?,'purchase' WHERE NOT EXISTS (SELECT 1 FROM credit_ledger WHERE order_id=? AND reason='purchase')`).bind(crypto.randomUUID(),order.email,order.id,Number(credits.total),order.id));
    await env.DB.batch(statements);
  }else if(['FAILED','EXPIRED'].includes(checkout.status)&&order.status==='pending'){
    await env.DB.prepare(`UPDATE orders SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'`).bind(checkout.status==='FAILED'?'failed':'cancelled',order.id).run();
  }
}

export async function onRequestPost({request,env,waitUntil}){
  let event;try{event=await request.json()}catch(_){return empty(400)}
  if(event?.event_type!=='CHECKOUT_STATUS_CHANGED'||!event?.id)return empty(204);
  const work=retrieveCheckout(env,event.id).then(checkout=>syncOrder(env,checkout)).catch(()=>{});
  if(waitUntil)waitUntil(work);else await work;
  return empty(204);
}

export async function onRequestGet({request,env}){
  const url=new URL(request.url);const reference=String(url.searchParams.get('reference')||'').slice(0,80);const origin=url.origin;
  if(!reference||!env.DB||!env.SUMUPAPIKEY)return redirect(`${origin}/shop.html?payment=failed&provider=sumup`);
  try{
    const order=await env.DB.prepare(`SELECT provider_payment_id FROM orders WHERE reference=? AND provider='sumup' LIMIT 1`).bind(reference).first();
    if(!order?.provider_payment_id)throw new Error('order_not_found');
    const checkout=await retrieveCheckout(env,order.provider_payment_id);await syncOrder(env,checkout);
    const payment=checkout.status==='PAID'?'success':(['FAILED','EXPIRED'].includes(checkout.status)?'failed':'pending');
    return redirect(`${origin}/shop.html?payment=${payment}&provider=sumup&reference=${encodeURIComponent(reference)}`);
  }catch(_){return redirect(`${origin}/shop.html?payment=failed&provider=sumup`)}
}
