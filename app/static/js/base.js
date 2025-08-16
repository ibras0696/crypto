// Base layout shared scripts: auth demo, nav toggle, sound bar
async function demoLogin(){
  const email='demo@example.com';
  const password='demopass';
  let r = await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});
  if(r.status!==200){
    await fetch('/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});
    r = await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});
  }
  const js = await r.json();
  localStorage.setItem('token', js.access_token);
  document.getElementById('loginBtn')?.classList.add('hidden');
  document.getElementById('logoutBtn')?.classList.remove('hidden');
}
function demoLogout(){localStorage.removeItem('token');location.reload();}

function initAuthButtons(){
  document.getElementById('loginBtn')?.addEventListener('click', demoLogin);
  document.getElementById('logoutBtn')?.addEventListener('click', demoLogout);
}

function initNavToggle(){
  const navToggle=document.getElementById('navToggle');
  if(!navToggle) return;
  navToggle.addEventListener('click',()=>{
    const nav=document.getElementById('mainNav');
    const hidden=nav.classList.toggle('hidden');
    navToggle.setAttribute('aria-expanded', String(!hidden));
  });
}

// Sound bar
let soundEnabled = localStorage.getItem('soundEnabled') !== 'false';
let soundVolume = parseFloat(localStorage.getItem('soundVolume')||'0.5');

function updateBell(){
  const soundToggle=document.getElementById('soundToggle');
  if(!soundToggle) return;
  soundToggle.textContent = soundEnabled ? '🔔' : '🔕';
  soundToggle.setAttribute('aria-pressed', soundEnabled?'true':'false');
}

function playBeep(freq=660, duration=120){
  if(!soundEnabled||!window.AudioContext) return;
  const ctx = playBeep.ctx || (playBeep.ctx=new AudioContext());
  const o=ctx.createOscillator(); const g=ctx.createGain();
  o.type='sine'; o.frequency.value=freq; g.gain.value=soundVolume*0.2; o.connect(g); g.connect(ctx.destination); o.start();
  setTimeout(()=>{o.stop();}, duration);
}

function initSoundBar(){
  const volumeEl=document.getElementById('soundVolume');
  const toggleEl=document.getElementById('soundToggle');
  if(!volumeEl||!toggleEl) return;
  volumeEl.value=soundVolume;
  updateBell();
  toggleEl.addEventListener('click',()=>{soundEnabled=!soundEnabled; localStorage.setItem('soundEnabled', soundEnabled); updateBell(); playBeep(440,80);});
  volumeEl.addEventListener('input',e=>{soundVolume=parseFloat(e.target.value); localStorage.setItem('soundVolume', soundVolume);});
  window._notifySound = (type)=>{ if(type==='success') playBeep(880,120); else if(type==='error') playBeep(180,250); else playBeep(660,100); };
}

function initBase(){
  initAuthButtons();
  initNavToggle();
  initSoundBar();
}

document.addEventListener('DOMContentLoaded', initBase);
