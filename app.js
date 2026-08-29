const state={digest:[],special:[],sources:{groups:[]},digestFilter:'all',specialFilter:'all',digestSearch:'',specialSearch:''};
const $=(s,r=document)=>r.querySelector(s);
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=(v='')=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const dateLong=iso=>new Date(`${iso}T12:00:00`).toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric'});
const updated=iso=>iso?`UPDATED ${new Date(iso).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/Chicago'})} CT`:'UPDATED —';
function switchTab(name){
  $$('.tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
  $$('.panel').forEach(p=>p.classList.toggle('active',p.id===`panel-${name}`));
  history.replaceState(null,'',`#${name}`);
}
$$('.tab').forEach(b=>b.addEventListener('click',()=>switchTab(b.dataset.tab)));
function digestFiltered(){
  const q=state.digestSearch.trim().toLowerCase();
  return state.digest.filter(x=>{
    const f=state.digestFilter==='all'||(x.asset_classes||[]).includes(state.digestFilter);
    const s=!q||`${x.source} ${x.headline} ${x.summary} ${x.investment_takeaway}`.toLowerCase().includes(q);
    return f&&s;
  });
}
function renderDigest(){
  const rows=digestFiltered();
  $('#digest-count').textContent=`${rows.length} ITEM${rows.length===1?'':'S'}`;
  $('#digest-list').innerHTML=rows.length?rows.map((x,i)=>`
  <article class="digest-row">
    <div class="rankcell"><div class="rank">${String(i+1).padStart(2,'0')}</div><div class="time">${esc(x.time||'')}</div></div>
    <div class="digest-main">
      <div class="meta-line"><span class="source">${esc(x.source||'')}</span>${(x.asset_classes||[]).map(a=>`<span class="asset">${esc(a)}</span>`).join('')}</div>
      <h3 class="digest-title">${esc(x.headline||'')}</h3>
      <p class="digest-summary">${esc(x.summary||'')}</p>
      <div class="takeaway"><strong>Investor Takeaway</strong>${esc(x.investment_takeaway||'')}</div>
    </div>
    <div class="sidecell">
      <div class="priority ${esc((x.importance||'medium').toLowerCase())}">${esc((x.importance||'medium').toUpperCase())} PRIORITY</div>
      <a class="open-source" href="${esc(x.url||'#')}" target="_blank" rel="noopener">OPEN SOURCE ↗</a>
    </div>
  </article>`).join(''):'<div class="empty">NO ITEMS MATCH THE CURRENT FILTER.</div>';
}
function specialFiltered(){
  const q=state.specialSearch.trim().toLowerCase();
  return state.special.filter(x=>{
    const f=state.specialFilter==='all'||x.event_type===state.specialFilter;
    const s=!q||`${x.ticker} ${x.company} ${x.event_type} ${x.why_it_matters} ${x.next_step||''}`.toLowerCase().includes(q);
    return f&&s;
  });
}
function renderSpecial(){
  const rows=specialFiltered();
  $('#special-count').textContent=`${rows.length} EVENT${rows.length===1?'':'S'}`;
  $('#special-body').innerHTML=rows.length?rows.map(x=>`
  <tr>
    <td>${esc(x.time||'')}</td>
    <td><span class="badge ${esc((x.signal||'new').toLowerCase())}">${esc(x.signal||'NEW')}</span></td>
    <td class="ticker">${esc(x.ticker||'—')}</td>
    <td class="company">${esc(x.company||'')}</td>
    <td class="event">${esc(x.event_type||'Other')}</td>
    <td><span class="badge ${esc((x.status||'live').toLowerCase())}">${esc(x.status||'Live')}</span></td>
    <td class="narrative">${esc(x.why_it_matters||'')}</td>
    <td class="nextstep">${esc(x.next_step||'Verify source; identify next dated catalyst.')}</td>
    <td><a href="${esc(x.url||'#')}" target="_blank" rel="noopener">${esc(x.source||'SOURCE')} ↗</a></td>
  </tr>`).join(''):'<tr><td colspan="9" class="empty">NO EVENTS MATCH THE CURRENT FILTER.</td></tr>';
}
function renderSources(){
  const groups=state.sources.groups||[];
  const total=groups.reduce((n,g)=>n+(g.sources||[]).length,0);
  $('#source-count').textContent=total||'—';
  const edgar=groups.find(g=>g.name==='SEC / Filings');
  const regs=groups.find(g=>g.name==='Regulators / Deal Review');
  $('#edgar-count').textContent=edgar?(edgar.sources||[]).length:'—';
  $('#reg-count').textContent=regs?(regs.sources||[]).length:'—';
  $('#coverage-list').innerHTML=groups.map(g=>`<div class="coverage-group"><h4>${esc(g.name)}</h4><div class="coverage-tags">${(g.sources||[]).map(s=>`<span class="coverage-tag">${esc(s)}</span>`).join('')}</div></div>`).join('');
}
$$('[data-digest-filter]').forEach(b=>b.addEventListener('click',()=>{
  $$('[data-digest-filter]').forEach(x=>x.classList.remove('active'));b.classList.add('active');state.digestFilter=b.dataset.digestFilter;renderDigest();
}));
$$('[data-special-filter]').forEach(b=>b.addEventListener('click',()=>{
  $$('[data-special-filter]').forEach(x=>x.classList.remove('active'));b.classList.add('active');state.specialFilter=b.dataset.specialFilter;renderSpecial();
}));
$('#digest-search').addEventListener('input',e=>{state.digestSearch=e.target.value;renderDigest()});
$('#special-search').addEventListener('input',e=>{state.specialSearch=e.target.value;renderSpecial()});
async function load(){
  try{
    const stamp=Date.now();
    const [d,s,src]=await Promise.all([
      fetch(`data/digest.json?v=${stamp}`).then(r=>{if(!r.ok)throw Error('digest');return r.json()}),
      fetch(`data/special_situations.json?v=${stamp}`).then(r=>{if(!r.ok)throw Error('special');return r.json()}),
      fetch(`data/sources.json?v=${stamp}`).then(r=>{if(!r.ok)throw Error('sources');return r.json()})
    ]);
    state.digest=d.items||[];state.special=s.items||[];state.sources=src||{groups:[]};
    const day=d.date||new Date().toISOString().slice(0,10);
    $('#digest-tab-title').textContent=`${dateLong(day)} Digest`;
    $('#digest-heading').textContent=`${dateLong(day)} Digest`;
    $('#digest-updated').textContent=updated(d.updated_at);
    $('#special-updated').textContent=updated(s.updated_at);
    renderDigest();renderSpecial();renderSources();
  }catch(e){
    $('#digest-list').innerHTML='<div class="empty">DATA FEED UNAVAILABLE. CHECK THE /data FILES.</div>';
    $('#special-body').innerHTML='<tr><td colspan="9" class="empty">DATA FEED UNAVAILABLE.</td></tr>';
  }
}
function clock(){
  const d=new Date();
  $('#clock').textContent=d.toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',second:'2-digit',timeZone:'America/Chicago'})+' CT';
  $('#footer-date').textContent=d.toLocaleDateString('en-US',{month:'short',day:'2-digit',year:'numeric',timeZone:'America/Chicago'}).toUpperCase();
}
setInterval(clock,1000);clock();
const h=location.hash.slice(1);if(['digest','special','about'].includes(h))switchTab(h);
load();