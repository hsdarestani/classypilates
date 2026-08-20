const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const validEmail=v=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v||''));
const ref=()=>`CP-${crypto.randomUUID().replace(/-/g,'').slice(0,8).toUpperCase()}`;

export async function onRequestGet({request,env}){
  if(!env.DB)return json({ok:false,code:'db_not_configured',bookings:[]},503);const email=new URL(request.url).searchParams.get('email')?.trim().toLowerCase();if(!validEmail(email))return json({ok:false,error:'invalid_email'},400);
  try{const result=await env.DB.prepare(`SELECT b.reference,b.class_id,b.status,b.payment_state,b.created_at,c.name,c.starts_at,c.location_id,l.name AS studio_name,c.coach FROM bookings b JOIN classes c ON c.id=b.class_id JOIN locations l ON l.id=c.location_id WHERE lower(b.email)=? ORDER BY c.starts_at DESC`).bind(email).all();return json({ok:true,bookings:result.results||[]})}catch(error){return json({ok:false,error:'booking_query_failed',details:String(error?.message||error)},500)}
}

export async function onRequestPost({request,env}){
  if(!env.DB)return json({ok:false,code:'db_not_configured'},503);let body;try{body=await request.json()}catch(_){return json({ok:false,error:'invalid_json'},400)}
  const classId=String(body.classId||'');const email=String(body.email||'').trim().toLowerCase();const firstName=String(body.firstName||'').trim();if(!classId||!validEmail(email))return json({ok:false,error:'invalid_booking'},400);
  const reference=ref();const id=crypto.randomUUID();
  try{await env.DB.prepare(`INSERT INTO bookings(id,reference,class_id,email,first_name,status,payment_state) VALUES(?,?,?,?,?,'reserved','not_required')`).bind(id,reference,classId,email,firstName).run();const row=await env.DB.prepare(`SELECT b.reference,b.class_id,b.status,c.capacity,c.reserved_count,(c.capacity-c.reserved_count) AS spots,c.name,c.starts_at,l.name AS studio_name,c.coach FROM bookings b JOIN classes c ON c.id=b.class_id JOIN locations l ON l.id=c.location_id WHERE b.id=?`).bind(id).first();return json({ok:true,booking:row},201)}catch(error){const message=String(error?.message||error);if(message.includes('CLASS_FULL'))return json({ok:false,error:'class_full'},409);if(message.includes('DUPLICATE_BOOKING'))return json({ok:false,error:'duplicate_booking'},409);if(message.includes('CLASS_NOT_AVAILABLE'))return json({ok:false,error:'class_not_available'},409);return json({ok:false,error:'booking_failed',details:message},500)}
}

export async function onRequestDelete({request,env}){
  if(!env.DB)return json({ok:false,code:'db_not_configured'},503);let body;try{body=await request.json()}catch(_){return json({ok:false,error:'invalid_json'},400)}const reference=String(body.reference||'');const email=String(body.email||'').trim().toLowerCase();if(!reference||!validEmail(email))return json({ok:false,error:'invalid_request'},400);
  try{const result=await env.DB.prepare(`UPDATE bookings SET status='cancelled',cancelled_at=CURRENT_TIMESTAMP WHERE reference=? AND lower(email)=? AND status='reserved'`).bind(reference,email).run();if(!result.meta?.changes)return json({ok:false,error:'booking_not_found'},404);return json({ok:true,reference})}catch(error){return json({ok:false,error:'cancel_failed',details:String(error?.message||error)},500)}
}