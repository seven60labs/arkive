/* ARKive admin: check for updates / update / roll back, with live log */
(function(){
var CS=(document.querySelector('input[name=csrf]')||{}).value||'',$=function(i){return document.getElementById(i)};
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function show(j){
  var c=j.check,r=$('ures'),h='';
  if(c){var when=new Date(c.checked*1000).toLocaleString();
    if(!c.ok)h='<div class="warn">'+esc(c.msg)+'</div>';
    else if(!c.latest)h='<p class="mut">'+esc(c.msg)+'</p>';
    else if(c.newer)h='<p><b class="ok">New version available: v'+esc(c.latest)+'</b> ('+esc(c.name)+')'+(c.url?' · <span class="mut">'+esc(c.url)+'</span>':'')+'</p>'+(c.notes?'<div class="relnotes">'+esc(c.notes)+'</div>':'<p class="mut">No changelog published for this '+esc(c.kind)+'.</p>');
    else h='<p class="ok">You are up to date (latest is v'+esc(c.latest)+').</p>';
    h+='<p class="mut" style="margin:6px 0 0">Last checked '+esc(when)+'</p>'}
  r.innerHTML=h;
  $('uapp').disabled=!(c&&c.ok&&c.newer)||j.running;$('uapp').className=(c&&c.newer)?'pri':'';
  $('uchk').disabled=j.running;
  var a=j.apply;$('ust').innerHTML=j.running?'<b class="dots">'+(a&&a.kind=='rollback'?'Rolling back':'Updating')+'</b>':a?(a.state=='done'?'<b class="ok">'+esc(a.msg)+'</b>':a.state=='failed'?'<b class="err">'+esc(a.msg)+'</b>':esc(a.state)):'Idle.';
  var L=$('ulog');L.textContent=j.log||'';L.scrollTop=L.scrollHeight}
async function st(){try{var j=await (await fetch('/admin/update/status',{cache:'no-store'})).json();show(j);return j}catch(_){$('ust').innerHTML='<b class="dots">Panel restarting</b>';return null}}
async function post(a){var b=new URLSearchParams({a:a,csrf:CS});
  var r=await fetch('/admin/update',{method:'POST',body:b,headers:{'Content-Type':'application/x-www-form-urlencoded'}});var j={};try{j=await r.json()}catch(_){}
  if(j.version)show(j);else $('ures').innerHTML='<div class="warn">'+esc(j.msg||('HTTP '+r.status))+'</div>';return j}
async function follow(){for(;;){await new Promise(function(r){setTimeout(r,2000)});var j=await st();
  if(j&&!j.running){if(j.apply&&j.apply.state=='done')setTimeout(function(){location.reload()},2500);return}}}
$('uchk').onclick=async function(){this.disabled=true;this.textContent='Checking…';await post('check');this.textContent='Check for updates';this.disabled=false};
$('uapp').onclick=async function(){if(!confirm('Install the new version now? The panel restarts during the update.'))return;this.disabled=true;await post('apply');follow()};
$('urb').onclick=async function(){if(!confirm('Restore the previous version?'))return;await post('rollback');follow()};
st().then(function(j){if(j&&j.running)follow()});
})();
