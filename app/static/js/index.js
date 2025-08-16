// Index page specific logic
const fmt = (v, d=8) => Number(v).toFixed(d).replace(/\.0+$/,'').replace(/(\.\d*?)0+$/,'$1');
const toast = (msg, ok=true) => {
  const t=document.getElementById('toast');
  if(!t) return;
  t.textContent=msg; t.className='text-xs px-3 py-2 rounded shadow '+(ok?'bg-emerald-600':'bg-rose-600')+' text-white';
  t.classList.remove('hidden');
  setTimeout(()=>t.classList.add('hidden'),3500);
  if(window._notifySound) window._notifySound(ok?'success':'error');
};

let currencies=[];
let currentUserData=null;
let currentRate=null;
let rateTimer=null;

async function api(path, opts={}){
  const token=localStorage.getItem('token');
  opts.headers=Object.assign({'Content-Type':'application/json'}, opts.headers||{});
  if(token) opts.headers.Authorization='Bearer '+token;
  const r=await fetch(path, opts);
  return {ok:r.ok, status:r.status, json: async()=>{try{return await r.json();}catch{return null;}}};
}

async function loadCurrencies(){
  const {ok,json}=await api('/currencies');
  if(!ok) return;
  currencies=await json();
  const fromSel=document.getElementById('fromCurrency');
  const toSel=document.getElementById('toCurrency');
  if(!fromSel||!toSel) return;
  [fromSel,toSel].forEach(sel=>{sel.innerHTML=''; currencies.forEach(c=>{const o=document.createElement('option'); o.value=c.id; o.textContent=c.code; sel.appendChild(o);});});
  if(currencies.length>=2){fromSel.selectedIndex=0; toSel.selectedIndex=1;}
  updateLimitsAndReserve();
  await updateRate();
}

function updateLimitsAndReserve(){
  const toSel=document.getElementById('toCurrency');
  if(!toSel) return;
  const toId=Number(toSel.value);
  const curTo=currencies.find(c=>c.id===toId);
  const reserveInfo=document.getElementById('reserveInfo');
  if(reserveInfo) reserveInfo.textContent=curTo?`Резерв: ${fmt(curTo.reserve,4)} ${curTo.code}`:'';
  const limitsInfo=document.getElementById('limitsInfo');
  if(!limitsInfo) return;
  if(currentUserData && currentUserData.kyc_status!=='verified'){
    limitsInfo.textContent=`Лимит без KYC: до ${window.UNVERIFIED_ORDER_MAX || 1000} за заявку / ${window.UNVERIFIED_DAILY_VOLUME_MAX || 5000} в сутки`;
  } else { limitsInfo.textContent=''; }
}

async function updateRate(){
  const fromSel=document.getElementById('fromCurrency');
  const toSel=document.getElementById('toCurrency');
  if(!fromSel||!toSel || !fromSel.value || !toSel.value) return;
  const fromCur=currencies.find(c=>c.id==fromSel.value); const toCur=currencies.find(c=>c.id==toSel.value);
  if(!fromCur||!toCur){return;}
  const symbol=(fromCur.code+toCur.code).toUpperCase();
  const {ok,json}=await api('/public/rates?symbols='+symbol, {headers:{}});
  if(ok){
    const data=await json();
    currentRate=data[symbol];
    if(currentRate){
      const rateInfo=document.getElementById('rateInfo');
      if(rateInfo) rateInfo.textContent=`Курс: 1 ${fromCur.code} = ${fmt(currentRate,6)} ${toCur.code}`;
      recalcTo();
    }
  }
}

function recalcTo(){
  const amountFrom=document.getElementById('amountFrom');
  const amountTo=document.getElementById('amountTo');
  if(!amountFrom||!amountTo){return;}
  const amt=parseFloat(amountFrom.value||'0');
  if(!currentRate || !amt){amountTo.value=''; return;}
  amountTo.value=fmt(amt*currentRate,8);
}

function swap(){
  const fromSel=document.getElementById('fromCurrency');
  const toSel=document.getElementById('toCurrency');
  if(!fromSel||!toSel) return;
  const i=fromSel.selectedIndex; fromSel.selectedIndex=toSel.selectedIndex; toSel.selectedIndex=i;
  updateLimitsAndReserve(); updateRate(); recalcTo();
}

async function loadUser(){
  const token=localStorage.getItem('token');
  if(!token){return;}
  const {ok,json}=await api('/auth/me');
  if(!ok) return;
  currentUserData=await json();
  const box=document.getElementById('userBox');
  if(box){
    box.innerHTML=`<span class='font-semibold'>${currentUserData.email}</span><span class='px-2 py-0.5 bg-slate-200 rounded text-xs'>role:${currentUserData.role}</span><span class='px-2 py-0.5 bg-slate-200 rounded text-xs'>kyc:${currentUserData.kyc_status}</span>`;
    box.classList.remove('hidden');
  }
  const kycForm=document.getElementById('kycForm');
  const kycStatusBadge=document.getElementById('kycStatusBadge');
  const kycWarning=document.getElementById('kycWarning');
  if(kycStatusBadge) kycStatusBadge.textContent=currentUserData.kyc_status;
  if(['unverified','rejected'].includes(currentUserData.kyc_status)){
    kycForm?.classList.remove('hidden');
    if(kycWarning){kycWarning.classList.remove('hidden'); kycWarning.textContent='Вы не верифицированы. Лимиты снижены.';}
  } else {
    kycForm?.classList.add('hidden');
    kycWarning?.classList.add('hidden');
  }
  updateLimitsAndReserve();
}

document.getElementById('kycForm')?.addEventListener('submit', async e=>{
  e.preventDefault();
  const fd=new FormData(e.target);
  const body={full_name:fd.get('full_name'), document_id:fd.get('document_id')};
  const {ok}=await api('/auth/kyc/submit',{method:'POST', body:JSON.stringify(body)});
  if(ok){toast('KYC отправлен'); loadUser();} else toast('Ошибка KYC', false);
});

async function loadMyOrders(){
  const {ok,json}=await api('/orders/my/list');
  if(!ok) return;
  const data=await json();
  const tb=document.querySelector('#myOrdersTbl tbody');
  if(!tb) return;
  tb.innerHTML='';
  const tpl=document.getElementById('orderRowTpl');
  data.forEach(o=>{
    const r=tpl.content.firstElementChild.cloneNode(true);
    const tds=r.querySelectorAll('td');
    const fromC=currencies.find(c=>c.id===o.from_currency)?.code||o.from_currency;
    const toC=currencies.find(c=>c.id===o.to_currency)?.code||o.to_currency;
    tds[0].textContent=o.id;
    tds[1].textContent=fromC+'→'+toC;
    tds[2].textContent=fmt(o.amount_from)+'/'+fmt(o.amount_to);
    tds[3].innerHTML=`<span class='inline-block px-2 py-0.5 rounded bg-slate-200 text-[10px] font-medium'>${o.status}</span>`;
    r.querySelector('[data-view]').onclick=()=>showOrder(o.id);
    tb.appendChild(r);
  });
}

async function showOrder(id){
  const {ok,json}=await api('/orders/'+id);
  if(!ok) return;
  const order=await json();
  const {ok:okTx,json:jsonTx}=await api(`/orders/${id}/transactions`);
  const txs= okTx? await jsonTx():[];
  const box=document.getElementById('orderDetail');
  if(!box) return;
  const fromC=currencies.find(c=>c.id===order.from_currency)?.code||order.from_currency;
  const toC=currencies.find(c=>c.id===order.to_currency)?.code||order.to_currency;
  box.classList.remove('hidden');
  box.innerHTML=`<div class='flex items-center justify-between'><h3 class='font-semibold'>Заявка #${order.id}</h3><span class='px-2 py-0.5 rounded bg-slate-200 text-[10px]'>${order.status}</span></div>
  <div class='grid grid-cols-2 gap-2 text-[11px]'>
    <div>Пара: ${fromC}→${toC}</div>
    <div>Сумма: ${fmt(order.amount_from)} → ${fmt(order.amount_to)}</div>
    <div>Адрес оплаты:<br><code>${order.wallet_address||''}</code></div>
    <div>Вывод:<br><code>${order.payout_details||''}</code></div>
  </div>
  <form id='txForm' class='mt-4 flex gap-2'>
    <input name='tx_hash' placeholder='tx hash' class='border rounded px-2 py-1 flex-1 text-xs'/>
    <input name='amount' type='number' step='0.00000001' placeholder='amount' class='border rounded px-2 py-1 w-28 text-xs'/>
    <button class='bg-pink-600 text-white text-xs px-3 rounded'>Добавить Tx</button>
  </form>
  <div class='mt-4 text-[11px] font-semibold'>Транзакции</div>
  <ul class='mt-1 space-y-1'>${txs.map(t=>`<li class='border rounded px-2 py-1'>#${t.id} ${fmt(t.amount)} (${t.status}) <code>${t.tx_hash||''}</code></li>`).join('')||'<li class="text-slate-500">Нет</li>'}</ul>`;
  document.getElementById('txForm').addEventListener('submit', e=>submitTx(e, order.id));
}

async function submitTx(e, id){
  e.preventDefault();
  const fd=new FormData(e.target);
  const body={tx_hash:fd.get('tx_hash')||null, amount:parseFloat(fd.get('amount')||'0')};
  const {ok}=await api(`/orders/${id}/transactions`, {method:'POST', body:JSON.stringify(body)});
  if(ok){toast('Tx добавлен'); showOrder(id); loadMyOrders();} else toast('Ошибка Tx', false);
}

document.getElementById('exchangeForm')?.addEventListener('submit', async e=>{
  e.preventDefault();
  if(!currentUserData){toast('Нужен вход', false); return;}
  const fromId=Number(document.getElementById('fromCurrency').value);
  const toId=Number(document.getElementById('toCurrency').value);
  const amount=parseFloat(document.getElementById('amountFrom').value||'0');
  const payout=document.getElementById('payoutDetails').value||null;
  const body={from_currency:fromId,to_currency:toId,amount_from:amount,payout_details:payout};
  const {ok,json}=await api('/orders',{method:'POST', body:JSON.stringify(body)});
  const data=await json();
  if(ok){toast('Заявка создана'); loadMyOrders(); showOrder(data.id);} else {toast(data?.detail||'Ошибка создания', false);}
});

document.getElementById('fromCurrency')?.addEventListener('change', ()=>{updateLimitsAndReserve(); updateRate(); recalcTo();});
document.getElementById('toCurrency')?.addEventListener('change', ()=>{updateLimitsAndReserve(); updateRate(); recalcTo();});
document.getElementById('amountFrom')?.addEventListener('input', recalcTo);
document.getElementById('swapBtn')?.addEventListener('click', swap);
document.getElementById('refreshOrders')?.addEventListener('click', loadMyOrders);

function scheduleRate(){ if(rateTimer) clearInterval(rateTimer); rateTimer=setInterval(updateRate,15000); }

async function initIndex(){
  await loadCurrencies();
  await loadUser();
  await loadMyOrders();
  scheduleRate();
}

document.addEventListener('DOMContentLoaded', initIndex);
