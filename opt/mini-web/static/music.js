// first-party music UI: browser queue (shuffle/repeat, saved locally) + Pi player controls
(function(){var au=document.getElementById('au'),Q=JSON.parse(localStorage.getItem('mq')||'[]'),i=+localStorage.getItem('mi')||0,shuf=localStorage.getItem('ms')=='1',rep=localStorage.getItem('mr')=='1';
var CS=(document.querySelector('input[name=csrf]')||{}).value||'';
function save(){localStorage.setItem('mq',JSON.stringify(Q));localStorage.setItem('mi',i);localStorage.setItem('ms',shuf?'1':'0');localStorage.setItem('mr',rep?'1':'0')}
function ui(){var t=Q[i];document.getElementById('now').textContent=t?('▶ '+t.t+' · '+t.a):'Browser player: nothing playing';document.getElementById('bshuf').className=shuf?'on':'';document.getElementById('brep').className=rep?'on':'';
 document.getElementById('bq').textContent=Q.length?('Queue: '+Q.map(function(x,k){return (k==i?'▶':'')+x.t}).join(' · ')):''}
function play(k){if(!Q.length)return;i=(k+Q.length)%Q.length;au.src=Q[i].u;au.play();save();ui()}
function nxt(){if(shuf&&Q.length>1){var k;do{k=Math.floor(Math.random()*Q.length)}while(k==i);play(k)}else if(i+1<Q.length||rep)play(i+1)}
au.addEventListener('ended',nxt);
document.getElementById('bnext').onclick=nxt;document.getElementById('bprev').onclick=function(){play(i-1)};
document.getElementById('bshuf').onclick=function(){shuf=!shuf;save();ui()};document.getElementById('brep').onclick=function(){rep=!rep;save();ui()};
document.getElementById('bclr').onclick=function(){Q=[];i=0;au.pause();au.removeAttribute('src');save();ui()};
function tr(b){return JSON.parse(b.dataset.t)}
document.querySelectorAll('.pb').forEach(function(b){b.onclick=function(){Q.splice(i+1,0,tr(b));play(Q.length>1?i+1:0)}});
document.querySelectorAll('.qb').forEach(function(b){b.onclick=function(){Q.push(tr(b));save();ui();if(au.paused&&Q.length==1)play(0)}});
document.querySelectorAll('.playall').forEach(function(b){b.onclick=function(){Q=[].map.call(document.querySelectorAll('.pb'),tr);play(0)}});
function pi(body){body.csrf=CS;return fetch('/admin/music/pi',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(body)}).then(function(r){return r.json()}).then(piui)}
function fmt(s){s=Math.floor(s||0);return Math.floor(s/60)+':'+('0'+s%60).slice(-2)}
function piui(s){var n=document.getElementById('pinow');if(!n)return;if(!s.ok){n.textContent=s.err;return}
 n.innerHTML=(s.bt.length?'🔊 '+s.bt.join(', '):'<span class=err>No Bluetooth speaker connected</span>')+' · '+(s.title?((s.pause?'⏸ ':'▶ ')+s.title+' '+fmt(s.pos)+' / '+fmt(s.dur)):'idle');
 document.getElementById('pibar').style.width=(s.dur?100*s.pos/s.dur:0)+'%';var v=document.getElementById('pivol');if(document.activeElement!==v)v.value=s.vol||0;
 document.getElementById('piq').innerHTML=s.queue.map(function(q,k){return '<li'+(k==s.cur?' style="color:var(--acc)"':'')+'>'+q.replace(/</g,'&lt;')+' <button class="pirm" data-i="'+k+'" title="Remove from Pi queue" style="padding:0 6px;font-size:.8em">✕</button></li>'}).join('');
 document.querySelectorAll('.pirm').forEach(function(b){b.onclick=function(){pi({c:'rm',i:b.dataset.i})}})}
document.querySelectorAll('.pi').forEach(function(b){b.onclick=function(){pi({c:'add',paths:JSON.stringify([b.dataset.p])})}});
document.querySelectorAll('.piall').forEach(function(b){b.onclick=function(){pi({c:'add',replace:'1',paths:JSON.stringify([].map.call(document.querySelectorAll('.pi'),function(x){return x.dataset.p}))})}});
document.querySelectorAll('#pi button[data-c]').forEach(function(b){b.onclick=function(){pi({c:b.dataset.c})}});
var v=document.getElementById('pivol');if(v)v.onchange=function(){pi({c:'vol',v:v.value})};
function poll(){fetch('/admin/music/pi').then(function(r){return r.json()}).then(piui).catch(function(){})}if(document.getElementById('pi')){poll();setInterval(poll,3000)}
ui();if(Q[i])au.src=Q[i].u})();
