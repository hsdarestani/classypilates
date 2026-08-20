const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
export async function onRequestGet({request,env}){
  if(!env.DB)return json({ok:false,code:'db_not_configured',classes:[]},503);
  const url=new URL(request.url);const from=url.searchParams.get('from')||new Date().toISOString().slice(0,10);const to=url.searchParams.get('to')||new Date(Date.now()+14*86400000).toISOString().slice(0,10);const location=url.searchParams.get('location');
  let sql=`SELECT c.id,c.location_id AS studio,c.class_type AS type,c.name,c.coach,c.starts_at,c.duration_minutes AS duration,c.capacity,(c.capacity-c.reserved_count) AS spots,l.name AS studio_name,l.short_name AS studio_short,l.address FROM classes c JOIN locations l ON l.id=c.location_id WHERE c.status='active' AND substr(c.starts_at,1,10) BETWEEN ? AND ?`;
  const args=[from,to];if(location&&location!=='all'){sql+=' AND c.location_id=?';args.push(location)}sql+=' ORDER BY c.starts_at ASC';
  try{const result=await env.DB.prepare(sql).bind(...args).all();return json({ok:true,classes:result.results||[]})}catch(error){return json({ok:false,error:'schedule_query_failed',details:String(error?.message||error)},500)}
}