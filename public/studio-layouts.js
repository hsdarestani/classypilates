(()=>{
  const capacities={bhf1:8,ladies:10,sachsen:12,bornheim:8,mid:10,oval:10};
  const layouts={
    sachsen:{title:'Studio Sachsenhausen',spots:[[19,21,90],[27,22,90],[35,21,90],[43,23,90],[51,22,90],[59,21,90],[39,62,90],[72,22,90],[80,21,90],[87,23,90],[94,22,90],[84,64,0]],features:[['mirror',38,4,50,3,0,'MIRROR'],['mirror',84,91,25,3,0,'MIRROR'],['entrance',4,72,4,15,0,'ENTRANCE'],['chair',5,17,4,6,90,''],['chair',5,25,4,6,90,''],['chair',5,33,4,6,90,''],['chair',5,41,4,6,90,''],['desk',59,76,13,11,0,'RECEPTION'],['partition',65,48,.7,89,0,'']]},

    /* Bahnhofsviertel 2F: exact supplied sketch.
       01–03 on the left, 04 vertical above the single center mirror,
       05–07 and 08–10 in two right-side columns. Only three mirrors:
       one vertical left, one vertical center, one vertical right. */
    ladies:{title:'Studio Bahnhofsviertel · 2nd Floor',spots:[[18,18,0],[18,35,0],[18,52,0],[43,27,90],[64,18,0],[64,35,0],[64,52,0],[86,18,0],[86,35,0],[86,52,0]],features:[['mirror',4,30,3,50,0,'MIRROR'],['mirror',43,54,3,27,0,'MIRROR'],['mirror',97,31,3,56,0,'MIRROR'],['entrance',15,79,6,14,0,'ENTRANCE']]},

    /* Bahnhofsviertel 1F: exact supplied sketch — entrance bottom-left; mirrors only on the left wall and top wall. */
    bhf1:{title:'Studio Bahnhofsviertel · 1st Floor',spots:[[17,24,90],[32,25,90],[46,24,90],[66,23,90],[79,24,90],[91,23,90],[70,69,90],[86,70,90]],features:[['mirror',4,22,3,44,0,'MIRROR'],['mirror',46,5,14,3,0,'MIRROR'],['mirror',79,6,44,3,0,'MIRROR'],['entrance',6,86,4,14,0,'ENTRANCE']]},

    bornheim:{title:'Studio Bornheim',spots:[[20,18,0],[16,63,90],[28,65,90],[39,62,90],[50,64,90],[61,62,90],[72,65,90],[84,63,90]],features:[['mirror',4,26,3,48,90,'MIRROR'],['mirror',49,88,74,3,0,'MIRROR'],['desk',82,18,12,7,0,'RECEPTION'],['chair',93,12,5,6,90,''],['chair',93,19,5,6,90,''],['chair',93,26,5,6,90,''],['entrance',97,34,4,13,0,'ENTRANCE']]},

    oval:{title:'Studio Oval',spots:[[12,22,90],[24,22,90],[36,22,90],[48,22,90],[60,22,90],[70,22,90],[80,22,90],[90,22,90],[33,78,0],[86,72,20]],features:[['mirror',52,4,90,3,0,'MIRROR'],['entrance',4,57,4,15,0,'ENTRANCE'],['wall',60,79,1,37,0,''],['wall',68,61,17,1,0,''],['wall',76,79,1,37,0,''],['mirror',77,79,2,37,0,'MIRROR'],['mirror',88,96,23,3,0,'MIRROR']]},

    /* Mid: mirrors only under 01–02, 04–06 and 07–08. 03, 09 and 10 have no mirror. */
    mid:{title:'Studio Mid',spots:[[10,43,90],[19,43,90],[28,43,90],[44,43,90],[52,43,90],[60,43,90],[72,43,90],[80,43,90],[88,43,90],[96,43,90]],features:[['mirror',14,82,16,3,0,'MIRROR'],['mirror',52,82,24,3,0,'MIRROR'],['mirror',76,82,16,3,0,'MIRROR'],['entrance',35,92,5,13,0,'ENTRANCE']]}
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
    map.dataset.layoutId=id;
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
    if(topLabel)topLabel.textContent=`${layout.title} · ${layout.visiblePlaces||capacities[id]} PLACES`;
    floor.querySelectorAll('.layout-feature,.real-layout-caption').forEach(n=>n.remove());
    layout.features.forEach(f=>floor.appendChild(featureNode(f)));
    const caption=document.createElement('div');
    caption.className='real-layout-caption';
    caption.innerHTML='<span>STUDIO MAP</span><b>Choose your spot</b>';
    floor.appendChild(caption);
    const spots=[...grid.querySelectorAll('.studio-spot')];
    spots.forEach((spot,i)=>{
      const pos=layout.spots[i];
      if(!pos){spot.hidden=true;spot.style.display='none';return}
      spot.hidden=false;spot.style.removeProperty('display');
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
