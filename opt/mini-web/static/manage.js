/* ARKive media management: selection, bulk delete/move/zip, per-item rename/delete/cover, delete folder */
(function(){
var bar=document.getElementById('mg');if(!bar)return;
var kind=bar.dataset.kind,CS=(document.querySelector('input[name=csrf]')||{}).value||'',on=false,sel=new Set();
var items=function(){return [].slice.call(document.querySelectorAll(kind=='photos'?'a.ph[data-p]':'.trk[data-p]'))};
function post(body){body.csrf=CS;body.kind=kind;return fetch('/admin/media',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(body)})
  .then(function(r){return r.json()}).then(function(j){if(!j.ok){alert('Not done: '+j.msg);return j}sessionStorage.setItem('mgmsg',j.msg);location.reload();return j})}
var m=sessionStorage.getItem('mgmsg');if(m){sessionStorage.removeItem('mgmsg');var d=document.createElement('div');d.className='card';d.innerHTML=m;bar.before(d)}
function upd(){document.getElementById('mgn').textContent=sel.size+' selected';items().forEach(function(e){e.classList.toggle('sel',sel.has(e.dataset.p));var c=e.querySelector('.mcb');if(c)c.checked=sel.has(e.dataset.p)})}
if(kind=='music')items().forEach(function(e){var c=document.createElement('input');c.type='checkbox';c.className='mcb';e.prepend(c);c.onchange=function(){c.checked?sel.add(e.dataset.p):sel.delete(e.dataset.p);upd()}});
document.getElementById('mgsel').onclick=function(){on=!on;document.body.classList.toggle('selmode',on);document.getElementById('mgtools').hidden=!on;this.textContent=on?'✕ Done':'☑ Select';if(!on){sel.clear()}upd()};
document.addEventListener('click',function(e){if(!on||kind!='photos')return;var a=e.target.closest('a.ph[data-p]');if(!a)return;e.preventDefault();e.stopImmediatePropagation();
  sel.has(a.dataset.p)?sel.delete(a.dataset.p):sel.add(a.dataset.p);upd()},true);
document.getElementById('mgall').onclick=function(){var all=items();if(sel.size==all.length)sel.clear();else all.forEach(function(e){sel.add(e.dataset.p)});upd()};
var need=function(){if(!sel.size){alert('Select something first.');return false}return true};
document.getElementById('mgdel').onclick=function(){if(need()&&confirm('Move '+sel.size+' item(s) to the Trash? (Restorable for 30 days.)'))post({op:'delete',paths:JSON.stringify([...sel])})};
document.getElementById('mgmv').onclick=function(){var d=document.getElementById('mgdest').value.trim();if(!need())return;if(!d){alert('Type or pick a destination name first.');return}post({op:'move',dest:d,paths:JSON.stringify([...sel])})};
document.getElementById('mgzip').onclick=function(){if(!need())return;location.href='/admin/media/zip?kind='+kind+[...sel].map(function(p){return '&p='+encodeURIComponent(p)}).join('')};
var rd=document.querySelector('[data-rmdir]');if(rd)rd.onclick=function(){if(confirm('Move "'+rd.dataset.rmdir+'" and everything in it ('+rd.dataset.n+' file(s)) to the Trash?'))post({op:'rmdir',paths:JSON.stringify([rd.dataset.rmdir])})
  .then(function(j){if(j.ok){sessionStorage.setItem('mgmsg',j.msg);var up=rd.dataset.rmdir.split('/').slice(0,-1).join('/');location.href=kind=='photos'?'/admin/photos'+(up?'?a='+encodeURIComponent(up):''):'/admin/music?v=folders&f='+encodeURIComponent(up)}})};
function ren(p){var nm=p.split('/').pop(),n=prompt('New name for '+nm,nm.replace(/\.[^.]+$/,''));if(n&&n!=nm)post({op:'rename',paths:JSON.stringify([p]),new:n})}
function del(p){if(confirm('Move '+p.split('/').pop()+' to the Trash?'))post({op:'delete',paths:JSON.stringify([p])})}
document.querySelectorAll('.mren').forEach(function(b){b.onclick=function(){ren(b.closest('[data-p]').dataset.p)}});
document.querySelectorAll('.mdel').forEach(function(b){b.onclick=function(){del(b.closest('[data-p]').dataset.p)}});
var cur=function(){return window.LBcur&&window.LBcur()};
[['lbren',function(p){ren(p.p)}],['lbdel',function(p){del(p.p)}],['lbcov',function(p){post({op:'cover',paths:JSON.stringify([p.p])})}]].forEach(function(x){var b=document.getElementById(x[0]);if(b)b.onclick=function(e){e.stopPropagation();var p=cur();if(p)x[1](p)}});
})();
