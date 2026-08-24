(()=>{
  const syncedKey='cpServerSyncedRefs';
  const read=(k,f)=>{try{return JSON.parse(localStorage.getItem(k)||JSON.stringify(f))}catch(_){return f}};
  const write=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(_){}};
  let busy=false;
  async function syncLatest(){
    if(busy)return;busy=true;
    try{
      const bookings=read('cpBookings',[]), synced=new Set(read(syncedKey,[]));
      const customer=read('cpWizardCustomer',{});
      for(const b of bookings.slice(0,12)){
        if(!b?.ref||synced.has(b.ref)||b.status==='cancelled')continue;
        if(!Number.isInteger(Number(b.classId)))continue;
        try{
          const r=await fetch('/api/bookings',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({
            classId:Number(b.classId),email:b.email,firstName:customer.firstName||'',lastName:customer.lastName||'',phone:customer.phone||'',spot:b.spotNumber||null,paymentMethod:b.paymentMethod||''
          })});
          if(r.ok||r.status===409){synced.add(b.ref);write(syncedKey,[...synced].slice(-100));}
        }catch(_){break}
      }
    }finally{busy=false}
  }
  const drawer=document.querySelector('#drawerBody');
  if(drawer)new MutationObserver(()=>{if(drawer.querySelector('.booking-success-v2'))setTimeout(syncLatest,100)}).observe(drawer,{childList:true,subtree:true});
  window.addEventListener('online',syncLatest);setTimeout(syncLatest,1200);
})();
