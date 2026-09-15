(()=>{
  const $=selector=>document.querySelector(selector);
  const params=new URLSearchParams(location.search);
  const token=params.get('token')||'';
  const requestForm=$('#requestForm');
  const confirmForm=$('#confirmForm');

  async function post(path,body){
    let response;
    try{
      response=await fetch(path,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'content-type':'application/json'},body:JSON.stringify(body)});
    }catch(_){
      throw new Error('server_unreachable');
    }
    let data={};
    try{data=await response.json()}catch(_){}
    if(!response.ok) throw new Error(data.detail||'request_failed');
    return data;
  }

  const messages={
    password_too_short:'Please use at least 10 characters.',
    reset_token_expired:'This reset link has expired. Request a new one.',
    reset_token_invalid:'This reset link is invalid. Request a new one.',
    reset_token_used:'This reset link has already been used. Request a new one.',
    request_failed:'Something went wrong. Please try again.',
    server_unreachable:'The server is unavailable. Please try again.'
  };

  if(token){
    requestForm.hidden=true;
    confirmForm.hidden=false;
    history.replaceState(null,'',location.pathname);
  }

  requestForm.onsubmit=async event=>{
    event.preventDefault();
    const button=$('#requestSubmit');
    const message=$('#requestMessage');
    message.textContent='';
    try{
      button.disabled=true;
      button.textContent='Sending…';
      await post('/api/auth/password-reset/request',{email:$('#resetEmail').value.trim()});
      message.style.color='#416347';
      message.textContent='If this email belongs to a Classy account, a reset link has been sent. Please also check your spam folder.';
    }catch(error){
      message.style.color='';
      message.textContent=messages[error.message]||error.message;
    }finally{
      button.disabled=false;
      button.textContent='Send reset link';
    }
  };

  $('#showNewPassword').onchange=()=>{
    const type=$('#showNewPassword').checked?'text':'password';
    $('#newPassword').type=type;
    $('#confirmPassword').type=type;
  };

  confirmForm.onsubmit=async event=>{
    event.preventDefault();
    const button=$('#confirmSubmit');
    const message=$('#confirmMessage');
    const password=$('#newPassword').value;
    message.textContent='';
    if(password!==$('#confirmPassword').value){
      message.textContent='The passwords do not match.';
      return;
    }
    try{
      button.disabled=true;
      button.textContent='Resetting…';
      const data=await post('/api/auth/password-reset/confirm',{token,password});
      message.style.color='#416347';
      message.textContent='Password changed. Opening your portal…';
      const portal=new Set(['/account','/coach','/admin']).has(data?.user?.portal)?data.user.portal:'/account';
      location.replace(portal);
    }catch(error){
      message.style.color='';
      message.textContent=messages[error.message]||error.message;
    }finally{
      button.disabled=false;
      button.textContent='Reset password';
    }
  };
})();
