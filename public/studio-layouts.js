(()=>{
  const capacities={bhf1:8,ladies:10,sachsen:12,bornheim:8,mid:10,oval:10};
  const layouts={
    sachsen:{title:'Studio Sachsenhausen',spots:[[18,24,90],[26,24,90],[34,24,90],[42,24,90],[50,24,90],[58,24,90],[52,66,90],[72,24,90],[79,24,90],[86,24,90],[93,24,90],[84,67,0]],features:[['mirror',34,4,44,3,0,'MIRROR'],['mirror',84,91,24,3,0,'MIRROR'],['entrance',4,76,4,16,0,'ENTRANCE'],['stairs',5,31,6,29,0,'STAIRS'],['desk',58,73,15,11,0,'RECEPTION'],['wall',65,47,2,84,0,'']]},
    ladies:{title:'Studio Bahnhofsviertel · 2nd Floor',spots:[[16,20,0],[16,36,0],[16,52,0],[35,35,90],[56,20,0],[56,36,0],[56,52,0],[80,20,0],[80,36,0],[80,52,0]],features:[['mirror',4,37,3,45,90,'MIRROR'],['mirror',96,37,3,45,90,'MIRROR'],['mirror',42,65,17,3,0,'MIRROR'],['entrance',13,88,12,4,0,'ENTRANCE'],['desk',20,70,14,10,0,'RECEPTION'],['column',34,69,5,5,0,''],['bench',76,78,24,7,0,'SEATING']]},
    bhf1:{title:'Studio Bahnhofsviertel · 1st Floor',spots:[[17,28,90],[33,28,90],[48,28,90],[66,28,90],[78,28,90],[90,28,90],[72,70,90],[88,70,90]],features:[['mirror',4,36,3,48,90,'MIRROR'],['mirror',76,4,38,3,0,'MIRROR'],['mirror',82,92,27,3,0,'MIRROR'],['entrance',5,84,4,14,0,'ENTRANCE']]},
    bornheim:{title:'Studio Bornheim',spots:[[20,22,0],[16,66,90],[27,66,90],[38,66,90],[49,66,90],[60,66,90],[71,66,90],[83,66,90]],features:[['mirror',4,27,3,23,90,'MIRROR'],['mirror',49,92,73,3,0,'MIRROR'],['entrance',95,69,4,17,0,'ENTRANCE'],['stairs',93,34,6,22,0,'STAIRS'],['desk',79,24,14,10,0,'RECEPTION']]},
    oval:{title:'Studio Oval',spots:[[34,24,62],[43,27,62],[52,30,62],[61,33,62],[70,36,62],[79,39,62],[88,42,62],[95,45,62],[77,69,0],[91,69,20]],features:[['mirror',56,4,55,3,0,'MIRROR'],['mirror',84,92,21,3,0,'MIRROR'],['mirror',68,62,3,23,90,'MIRROR'],['desk',10,56,14,9,0,'RECEPTION'],['changing',37,75,40,24,0,'CHANGING ROOM'],['column',18,32,5,5,0,''],['column',26,32,5,5,0,''],['column',97,51,5,5,0,'']]},
    mid:{title:'Studio Mid',spots:[[11,43,90],[20,43,90],[29,43,90],[43,43,90],[52,43,90],[61,43,90],[75,43,90],[83,43,90],[91,43,90],[98,43,90]],features:[['mirror',18,82,25,3,0,'MIRROR'],['mirror',51,82,24,3,0,'MIRROR'],['mirror',84,82,25,3,0,'MIRROR']]}
  };

  function studioIdFromText(){
    const text=(document.querySelector('.wizard-class-card p')?.textContent||'').toLowerCase();
    if(text.includes('sachsen'))return'sachsen';
    if(text.includes('bornheim'))return'bornheim';
    if(text.includes('ladies')||text.includes('2. og')||text.includes('2nd floor')||text.includes('2f'))return'ladies';
    if(text.includes('1. og')||text.includes('1st floor')||text.includes('bahnhofsviertel 1f')||text.includes('bf - 1'))return'bhf1';
    if(text.includes('mid'))return'mid';
    if(text.includes('oval'))return'oval';
    return null;
  }

  function classType(){return(document.querySelector('.wizard-class-card>div>span')?.textContent||'').toLowerCase()}
  function featureNode(item){
    const [type,x,y,w,h,rot,label]=item;
    const el=document.createElement('div');
    el.className=`layout-feature ${type}`;
    el.setAttribute('aria-hidden','true');
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
    const ct=classType();
    const isPowerformer=ct.includes('powerformer');
    const isMat=ct.includes('mat')||ct.includes('barre');
    map.classList.toggle('powerformer-room',isPowerformer);
    map.classList.toggle('reformer-room',!isPowerformer&&!isMat);
    map.classList.toggle('floor-position-room',isMat);
    if(topLabel)topLabel.textContent=`${layout.title} · ${capacities[id]} PLACES`;
    floor.querySelectorAll('.layout-feature,.real-layout-caption').forEach(n=>n.remove());
    layout.features.forEach(f=>floor.appendChild(featureNode(f)));
    const caption=document.createElement('div');
    caption.className='real-layout-caption';
    caption.innerHTML='<span>STUDIO MAP</span><b>Choose your spot</b>';
    floor.appendChild(caption);
    const spots=[...grid.querySelectorAll('.studio-spot')];
    spots.forEach((spot,i)=>{
      const pos=layout.spots[i]||layout.spots[layout.spots.length-1];
      spot.style.setProperty('--sx',`${pos[0]}%`);
      spot.style.setProperty('--sy',`${pos[1]}%`);
      spot.style.setProperty('--sr',`${pos[2]}deg`);
      const noun=ct.includes('powerformer')?'Powerformer':ct.includes('mat')?'Mat':ct.includes('barre')?'Position':'Reformer';
      spot.classList.toggle('powerformer-machine',isPowerformer);
      spot.classList.toggle('reformer-machine',!isPowerformer&&!isMat);
      const bed=spot.querySelector('.spot-bed');
      if(bed&&!bed.querySelector('em'))bed.append(document.createElement('em'));
      if(bed&&!bed.querySelector('u'))bed.append(document.createElement('u'));
      spot.setAttribute('aria-label',`${noun} ${String(i+1).padStart(2,'0')} select`);
    });
    const oldEntry=floor.querySelector('.floor-entry');if(oldEntry)oldEntry.style.display='none';
    normalizeSpotText();
  }

  function normalizeSpotText(){
    const ct=classType();
    const noun=ct.includes('powerformer')?'Powerformer':ct.includes('mat')?'Mat':ct.includes('barre')?'Position':'Reformer';
    document.querySelectorAll('.spot-summary b,.success-grid b,.checkout-mini-summary b').forEach(el=>{
      const current=el.textContent.trim();
      if(!/^(Reformer|Powerformer|Mat|Position)\s+\d+/i.test(current))return;
      const next=current.replace(/^(Reformer|Powerformer|Mat|Position)/i,noun);
      if(next!==current)el.textContent=next;
    });
  }

  try{
    if(typeof studios!=='undefined'){
      const publicNames={
        bhf1:'Studio Bahnhofsviertel · 1st Floor',
        ladies:'Studio Bahnhofsviertel · 2nd Floor',
        sachsen:'Studio Sachsenhausen',
        bornheim:'Studio Bornheim',
        oval:'Studio Oval',
        mid:'Studio Mid'
      };
      studios.forEach(studio=>{
        if(publicNames[studio.id])studio.name=publicNames[studio.id];
        if(capacities[studio.id])studio.capacity=capacities[studio.id];
      });
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
