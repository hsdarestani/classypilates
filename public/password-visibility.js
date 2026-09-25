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

  function apply(toggle){
    const visible=Boolean(toggle.checked);
    for(const input of targetsFor(toggle)){
      if(!(input instanceof HTMLInputElement)) continue;
      input.dataset.passwordVisibility='1';
      const start=input.selectionStart,end=input.selectionEnd;
      try{input.type=visible?'text':'password'}catch(_){input.setAttribute('type',visible?'text':'password')}
      input.setAttribute('type',visible?'text':'password');
      if(input.style && 'webkitTextSecurity' in input.style) input.style.webkitTextSecurity=visible?'none':'';
      try{if(document.activeElement===input&&start!==null&&end!==null)input.setSelectionRange(start,end)}catch(_){}
    }
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
    upgradeLegacy();
    document.querySelectorAll('[data-password-toggle]').forEach(toggle=>{if(toggle.checked)apply(toggle)});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);
  else boot();
})();