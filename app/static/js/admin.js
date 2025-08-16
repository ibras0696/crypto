// Admin page specific logic
const statuses=["pending_payment","paid","processing","completed","canceled"];

async function fetchOrders(){
  const token=localStorage.getItem('token');
  if(!token){return;}
  const st = document.getElementById('filterStatus').value.trim();
  const qs = st?`?status=${encodeURIComponent(st)}`:'';
  const r = await fetch('/orders'+qs,{headers:{Authorization:'Bearer '+token}});
  if(!r.ok) return;
  const data = await r.json();
  const tb = document.querySelector('#ordersTbl tbody');
  if(!tb) return;
  tb.innerHTML='';
  data.forEach(o=>{
    const tr=document.createElement('tr');
    tr.className='border-b';
    tr.innerHTML=`<td class=p-2>${o.id}</td><td class=p-2>${o.user_id}</td><td class=p-2>${o.from_currency}->${o.to_currency}</td><td class=p-2>${o.amount_from}</td><td class=p-2>${o.status}</td><td class=p-2></td>`;
    const actTd=tr.lastChild;
    statuses.forEach(s=>{
      if(s!==o.status){
        const btn=document.createElement('button');
        btn.textContent=s;btn.className='text-xs mr-1 mb-1 px-2 py-1 rounded bg-pink-600 text-white';
        btn.onclick=()=>updateStatus(o.id,s);
        actTd.appendChild(btn);
      }
    });
    tb.appendChild(tr);
  });
}

async function loadAnalytics(){
  const token=localStorage.getItem('token');
  if(!token) return;
  const r=await fetch('/orders/analytics/summary?days=7',{headers:{Authorization:'Bearer '+token}});
  if(!r.ok) return;
  const data=await r.json();
  const ctx=document.getElementById('volChart');
  const labels=data.daily.map(d=>d.date);
  const volumes=data.daily.map(d=>d.volume);
  if(window._chart) window._chart.destroy();
  window._chart=new Chart(ctx,{type:'bar',data:{labels,datasets:[{label:'Volume',data:volumes,backgroundColor:'#db2777'}]},options:{scales:{y:{beginAtZero:true}}}});
}

async function updateStatus(id,s){
  const token=localStorage.getItem('token');
  const r=await fetch(`/orders/${id}/status`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({status:s})});
  if(r.ok){fetchOrders();} 
}

function initAdmin(){
  document.getElementById('reloadBtn')?.addEventListener('click', fetchOrders);
  fetchOrders();
  loadAnalytics();
}

document.addEventListener('DOMContentLoaded', initAdmin);
