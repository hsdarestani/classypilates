(()=>{
  const capacities={bhf1:8,ladies:10,sachsen:12,bornheim:8,mid:10,oval:10};
  const layouts={
    sachsen:{title:'Studio Sachsenhausen',spots:[[15,20,90],[23,20,90],[31,20,90],[39,20,90],[47,20,90],[55,20,90],[35,59,90],[69,20,90],[77,20,90],[85,20,90],[93,20,90],[78,58,0]],features:[['mirror',29,4,43,3,0,'SPIEGEL'],['mirror',76,90,26,3,0,'SPIEGEL'],['entrance',4,73,4,16,0,'EINGANG'],['bench',4,26,5,28,0,'SITZPLÄTZE'],['desk',51,71,15,12,0,'THEKE']]},
    ladies:{title:'Bahnhofsviertel · 2. OG',spots:[[14,20,0],[14,34,0],[14,48,0],[35,34,90],[56,20,0],[56,34,0],[56,48,0],[82,20,0],[82,34,0],[82,48,0]],features:[['mirror',4,34,3,42,90,'SPIEGEL'],['mirror',95,34,3,42,90,'SPIEGEL'],['mirror',56,64,22,3,0,'SPIEGEL'],['entrance',12,83,11,4,0,'EINGANG'],['desk',23,65,14,10,0,'EMPFANG'],['column',35,62,5,5,0,''],['column',78,66,5,5,0,'']]},
    bornheim:{title:'Studio Bornheim',spots:[[20,24,0],[16,66,90],[27,66,90],[38,66,90],[49,66,90],[60,66,90],[71,66,90],[82,66,90]],features:[['mirror',4,45,3,42,90,'SPIEGEL'],['mirror',48,91,72,3,0,'SPIEGEL'],['entrance',94,67,4,17,0,'EINGANG'],['bench',91,53,5,20,0,'SITZBANK'],['desk',79,25,14,10,0,'THEKE']]},
    bhf1:{title:'Bahnhofsviertel · 1. OG',spots:[[14,27,90],[29,27,90],[44,27,90],[59,27,90],[74,27,90],[89,27,90],[72,70,90],[88,70,90]],features:[['mirror',4,35,3,47,90,'SPIEGEL'],['mirror',77,4,30,3,0,'SPIEGEL'],['mirror',82,91,26,3,0,'SPIEGEL'],['entrance',5,82,4,14,0,'EINGANG']]},
    mid:{title:'Studio Mid',spots:[[8,42,90],[18,42,90],[28,42,90],[39,42,90],[49,42,90],[59,42,90],[70,42,90],[80,42,90],[90,42,90],[97,42,90]],features:[['mirror',17,79,23,3,0,'SPIEGEL'],['mirror',50,79,24,3,0,'SPIEGEL'],['mirror',82,79,23,3,0,'SPIEGEL']]},
    oval:{title:'Studio Oval',spots:[[33,27,58],[42,29,58],[51,31,58],[60,33,58],[69,35,58],[78,37,58],[87,39,58],[94,42,58],[76,68,0],[90,69,18]],features:[['mirror',56,4,54,3,0,'SPIEGEL'],['mirror',79,91,26,3,0,'SPIEGEL'],['mirror',68,58,3,22,90,'SPIEGEL'],['desk',10,55,13,9,0,'THEKE'],['changing',36,74,39,23,0,'UMKLEIDE'],['column',18,33,5,5,0,''],['column',26,33,5,5,0,''],['column',96,48,5,5,0,'']]}
  };

  function studioIdFromText(){
    const text=(document.querySelector('.wizard-class-card p')?.textContent||'').toLowerCase();
    if(text.includes('sachsen'))return'sachsen';
    if(text.includes('bornheim'))return'bornheim';
    if(text.includes('ladies')||text.includes('2. og'))return'ladies';
    if(text.includes('1. og')||text.includes('bahnhofsviertel 1f'))return'bhf1';
    if(text.includes('mid'))return'mid';
    if(text.includes('oval'))return'oval';
    return null;
  }

  function classType(){return(document.querySelector('.wizard-class-card>div>span')?.textContent||'').toLowerCase()}
  function featureNode(item){
    const [type,x,y,w,h,rot,label]=item;
    const el=document.createElement('div');
    el.className=`layout-feature ${type}`;
    el.style.cssText=`--fx:${x}%;--fy:${y}%;--fw:${w}%;--fh:${h}%;--fr:${rot}deg`;
    if(label)el.innerHTML=`<span>${label}</span>`;
    return el;
  }

  function applyRealLayout(){
    const map=document.querySelector('.studio-map');
    if(!map)return;
    const id=studioIdFromText(),layout=layouts[id];
    if(!layout)return;
    const floor=map.querySelector('.studio-floor'),grid=map.querySelector('.spot-grid');
    if(!floor||!grid)return;
    if(map.dataset.realLayout===id)return;
    map.dataset.realLayout=id;
    map.classList.add('real-studio-map');
    grid.classList.add('real-spot-layout');
    grid.dataset.layout=id;
    const topLabel=map.querySelector('.studio-map-top>span');
    if(topLabel)topLabel.textContent=`${layout.title} · ${capacities[id]} PLÄTZE`;
    floor.querySelectorAll('.layout-feature,.real-layout-caption').forEach(n=>n.remove());
    layout.features.forEach(f=>floor.appendChild(featureNode(f)));
    const caption=document.createElement('div');
    caption.className='real-layout-caption';
    caption.innerHTML='<span>STUDIO MAP</span><b>Wähle deinen Platz</b>';
    floor.appendChild(caption);
    const spots=[...grid.querySelectorAll('.studio-spot')];
    spots.forEach((spot,i)=>{
      const pos=layout.spots[i]||layout.spots[layout.spots.length-1];
      spot.style.setProperty('--sx',`${pos[0]}%`);
      spot.style.setProperty('--sy',`${pos[1]}%`);
      spot.style.setProperty('--sr',`${pos[2]}deg`);
      const ct=classType();
      const noun=ct.includes('powerformer')?'Powerformer':ct.includes('mat')?'Matte':ct.includes('barre')?'Position':'Reformer';
      spot.setAttribute('aria-label',`${noun} ${String(i+1).padStart(2,'0')} auswählen`);
    });
    const oldEntry=floor.querySelector('.floor-entry');if(oldEntry)oldEntry.style.display='none';
    normalizeSpotText();
  }

  function normalizeSpotText(){
    const ct=classType();
    const noun=ct.includes('powerformer')?'Powerformer':ct.includes('mat')?'Matte':ct.includes('barre')?'Position':'Reformer';
    document.querySelectorAll('.spot-summary b,.success-grid b,.checkout-mini-summary b').forEach(el=>{
      const current=el.textContent.trim();
      if(!/^(Reformer|Powerformer|Matte|Position)\s+\d+/i.test(current))return;
      const next=current.replace(/^(Reformer|Powerformer|Matte|Position)/i,noun);
      if(next!==current)el.textContent=next;
    });
  }

  try{
    if(typeof studios!=='undefined'){
      const s=studios.find(x=>x.id==='sachsen');if(s)s.address='Zum Gipfelhof 5 · 60594 Frankfurt';
    }
    if(typeof generateSchedule==='function'){
      const originalGenerateSchedule=generateSchedule;
      generateSchedule=function(){
        return originalGenerateSchedule().map(r=>{
          const cap=capacities[r.studio]||r.capacity;
          return {...r,capacity:cap,spots:Math.min(Number(r.spots)||0,cap)};
        });
      };
      if(typeof renderStudios==='function')renderStudios();
      if(typeof renderSchedule==='function')renderSchedule();
    }
  }catch(err){console.warn('Studio layout capacity sync skipped',err)}

  const root=document.querySelector('#drawerBody')||document.body;
  let scheduled=false;
  const refreshLayout=()=>{
    if(scheduled)return;
    scheduled=true;
    requestAnimationFrame(()=>{
      scheduled=false;
      applyRealLayout();
      normalizeSpotText();
    });
  };
  const observer=new MutationObserver(refreshLayout);
  observer.observe(root,{childList:true,subtree:true});
  refreshLayout();
})();
