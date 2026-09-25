(()=>{
  const selector='input[data-password-visibility]';

  function targetsFor(toggle){
    const raw=(toggle.getAttribute('data-password-targets')||toggle.getAttribute('data-password-toggle')||'').trim();
    if(raw){
      return raw.split(',').map(value=>value.trim()).filter(Boolean).flatMap(value=>[...document.querySelectorAll(value)]);
    }
    const scope=toggle.closest('form,.security-box,.profile-security,.modal,.form-stack')||document;
    return [...scope.querySelectorAll('input[type="password"],input[data-password-visibility]')].filter(input=>input!==toggle);
  }

  function setFieldVisibility(input,visible){
    if(!(input instanceof HTMLInputElement)) return;
    input.dataset.passwordVisibility='1';
    const start=input.selectionStart,end=input.selectionEnd;
    const type=visible?'text':'password';
    try{input.type=type}catch(_){}
    input.setAttribute('type',type);
    input.classList.toggle('password-visible',visible);
    input.classList.toggle('password-hidden',!visible);
    try{input.style.webkitTextSecurity=visible?'none':''}catch(_){}
    // Safari/iOS can keep the previous secure rendering for one frame after
    // changing input.type. Reapply on the next paint without replacing the
    // element, so autofill, listeners and the current value stay intact.
    requestAnimationFrame(()=>{
      try{
        input.type=type;
        input.setAttribute('type',type);
        input.style.webkitTextSecurity=visible?'none':'';
        void input.offsetWidth;
        if(document.activeElement===input&&start!==null&&end!==null)input.setSelectionRange(start,end);
      }catch(_){}
    });
  }

  function apply(toggle){
    const visible=Boolean(toggle.checked);
    for(const input of targetsFor(toggle)) setFieldVisibility(input,visible);
  }

  function handleToggleEvent(event){
    const toggle=event.target.closest?.('[data-password-toggle]');
    if(toggle) apply(toggle);
  }
  document.addEventListener('change',handleToggleEvent);
  document.addEventListener('input',handleToggleEvent);

  function upgradeLegacy(){
    const mappings=[
      ['#showPassword','#loginPassword'],
      ['#showNewPassword','#newPassword,#confirmPassword']
    ];
    for(const [toggleSelector,targetSelector] of mappings){
      const toggle=document.querySelector(toggleSelector);
      if(toggle&&!toggle.hasAttribute('data-password-toggle')){
        toggle.setAttribute('data-password-toggle','');
        toggle.setAttribute('data-password-targets',targetSelector);
      }
    }
  }

  function boot(){
    if(!document.getElementById('classy-password-visibility-style')){
      const style=document.createElement('style');
      style.id='classy-password-visibility-style';
      style.textContent='input.password-visible{-webkit-text-security:none!important}';
      document.head.appendChild(style);
    }
    upgradeLegacy();
    document.querySelectorAll('[data-password-toggle]').forEach(toggle=>apply(toggle));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);
  else boot();
})();