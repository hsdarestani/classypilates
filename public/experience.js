(()=>{
  const $=(s,c=document)=>c.querySelector(s);const $$=(s,c=document)=>[...c.querySelectorAll(s)];
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;document.documentElement.classList.add('js-ready');

  // Scroll progress + sticky header state.
  const progress=document.createElement('div');progress.className='scroll-progress';document.body.appendChild(progress);
  let ticking=false;function onScroll(){if(ticking)return;ticking=true;requestAnimationFrame(()=>{const max=Math.max(1,document.documentElement.scrollHeight-innerHeight);progress.style.transform=`scaleX(${Math.min(1,scrollY/max)})`;$('.shop-header')?.classList.toggle('is-scrolled',scrollY>12);ticking=false})}addEventListener('scroll',onScroll,{passive:true});onScroll();

  // Editorial reveal choreography. Nothing is hidden for reduced-motion users.
  const revealTargets=['.manifesto .eyebrow','.manifesto h2','.manifesto-copy','.schedule-title>div','.trust-box','.booking-shell','.section-head>div','.section-head>p','.studio-card','.class-copy>*','.passes .section-head','.pass-grid article','.shop-hero>div','.shop-hero>p','.benefits>div','.section-title','.product-card','.payment-strip>div','.trust-section article'];
  const targets=[...new Set(revealTargets.flatMap(s=>$$(s)))];targets.forEach((el,i)=>{el.classList.add('reveal');if(i%3===1)el.classList.add('reveal-delay-1');if(i%3===2)el.classList.add('reveal-delay-2')});
  if(reduced){targets.forEach(el=>el.classList.add('is-visible'))}else{const io=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-visible');io.unobserve(e.target)}}),{threshold:.1,rootMargin:'0px 0px -5%'});targets.forEach(el=>io.observe(el))}

  // Hero parallax kept subtle so text remains stable and premium rather than game-like.
  const hero=$('.hero'),heroImage=$('.hero-image');if(hero&&heroImage&&!reduced&&matchMedia('(pointer:fine)').matches){let tx=0,ty=0,cx=0,cy=0,raf=0;const draw=()=>{cx+=(tx-cx)*.055;cy+=(ty-cy)*.055;heroImage.style.transform=`scale(1.045) translate3d(${cx}px,${cy}px,0)`;if(Math.abs(tx-cx)>.05||Math.abs(ty-cy)>.05)raf=requestAnimationFrame(draw);else raf=0};hero.addEventListener('pointermove',e=>{const r=hero.getBoundingClientRect();tx=((e.clientX-r.left)/r.width-.5)*-10;ty=((e.clientY-r.top)/r.height-.5)*-7;if(!raf)raf=requestAnimationFrame(draw)});hero.addEventListener('pointerleave',()=>{tx=0;ty=0;if(!raf)raf=requestAnimationFrame(draw)})}

  // Lightweight 3D response for studio/product cards; automatically disabled on touch.
  function tilt(el,max=3.2){if(reduced||!matchMedia('(pointer:fine)').matches)return;el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;el.style.setProperty('--rx',`${(-y*max).toFixed(2)}deg`);el.style.setProperty('--ry',`${(x*max).toFixed(2)}deg`)});el.addEventListener('pointerleave',()=>{el.style.setProperty('--rx','0deg');el.style.setProperty('--ry','0deg')})}
  $$('.studio-card').forEach(x=>tilt(x,2.8));$$('.product-card').forEach(x=>tilt(x,3.5));

  // Animate numeric brand proof once.
  const nums=$$('.numbers b');if(nums.length&&!reduced){const nio=new IntersectionObserver(entries=>entries.forEach(e=>{if(!e.isIntersecting)return;const el=e.target,target=parseInt(el.textContent,10);if(!Number.isFinite(target))return;const start=performance.now(),duration=650;const step=now=>{const p=Math.min(1,(now-start)/duration),ease=1-Math.pow(1-p,3);el.textContent=Math.round(target*ease);if(p<1)requestAnimationFrame(step)};requestAnimationFrame(step);nio.unobserve(el)}),{threshold:.7});nums.forEach(n=>nio.observe(n))}

  // Schedule rows can be re-rendered by filters/API; animate and add a visual capacity cue each time.
  const list=$('#classList');function enhanceRows(){if(!list)return;$$('.class-row',list).forEach((row,i)=>{if(!row.dataset.fx){row.dataset.fx='1';row.classList.add('row-enter');row.style.animationDelay=`${Math.min(i,8)*35}ms`}const spot=$('.spots',row);if(spot){const text=spot.textContent||'';const m=text.match(/(\d+)/);let v=m?Math.max(.18,Math.min(1,Number(m[1])/10)):.35;if(spot.classList.contains('full'))v=.12;spot.style.setProperty('--seat',v)}})}if(list){enhanceRows();new MutationObserver(enhanceRows).observe(list,{childList:true,subtree:true})}

  // Ripple only on meaningful primary actions.
  document.addEventListener('pointerdown',e=>{const btn=e.target.closest('.reserve-btn,.drawer-action,.primary-btn,.pass-grid button,.product-card button');if(!btn||reduced)return;const r=btn.getBoundingClientRect(),size=Math.max(r.width,r.height),dot=document.createElement('span');dot.className='ripple';dot.style.width=dot.style.height=size+'px';dot.style.left=(e.clientX-r.left-size/2)+'px';dot.style.top=(e.clientY-r.top-size/2)+'px';btn.appendChild(dot);setTimeout(()=>dot.remove(),620)});

  // Current section in nav.
  const navLinks=$$('.desktop-nav a[href^="#"]');const sections=navLinks.map(a=>$(a.getAttribute('href'))).filter(Boolean);if(sections.length){const sio=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){navLinks.forEach(a=>a.classList.toggle('is-active',a.getAttribute('href')==='#'+entry.target.id))}}),{rootMargin:'-28% 0px -58%',threshold:0});sections.forEach(s=>sio.observe(s))}

  // Floating schedule action appears only after the hero, keeping first screen clean.
  if(hero){const floating=document.createElement('a');floating.className='floating-book';floating.href='#schedule';floating.innerHTML='<i></i><span>Kurs buchen</span><b>↗</b>';document.body.appendChild(floating);const fio=new IntersectionObserver(([entry])=>floating.classList.toggle('show',!entry.isIntersecting),{threshold:.15});fio.observe(hero)}

  // Shop cart feedback when cart count changes.
  const count=$('#cartCount'),cart=$('#cartTrigger');if(count&&cart){let old=count.textContent;new MutationObserver(()=>{if(count.textContent===old)return;old=count.textContent;cart.classList.remove('cart-bump');void cart.offsetWidth;cart.classList.add('cart-bump')}).observe(count,{childList:true,characterData:true,subtree:true})}
})();
