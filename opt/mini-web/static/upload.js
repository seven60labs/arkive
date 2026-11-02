/* ARKive: resumable per-file chunked uploads with progress, plus live USB import progress */
(function(){
var CS=(document.querySelector('input[name=csrf]')||{}).value||'', CH=4<<20, busy=false;
window.addEventListener('beforeunload',function(e){if(busy){e.preventDefault();e.returnValue='Upload in progress';return e.returnValue}});
function mb(n){return n>=1e9?(n/1e9).toFixed(2)+' GB':(n/1e6).toFixed(1)+' MB'}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function sleep(ms){return new Promise(function(r){setTimeout(r,ms)})}
function send(kind,dest,f,off,prog){return new Promise(function(res,rej){
  var x=new XMLHttpRequest();
  x.open('POST','/admin/upload?kind='+kind+'&dest='+encodeURIComponent(dest)+'&name='+encodeURIComponent(f.name)+'&off='+off+'&total='+f.size);
  x.setRequestHeader('X-CSRF',CS);x.setRequestHeader('Content-Type','application/octet-stream');x.timeout=180000;
  x.upload.onprogress=function(e){if(e.lengthComputable)prog(e.loaded,e.total)};
  x.onload=function(){var j={};try{j=JSON.parse(x.responseText)}catch(_){}res({s:x.status,j:j})};
  x.onerror=x.ontimeout=function(){rej(new Error('net'))};
  x.send(f.slice(off,Math.min(f.size,off+CH)));})}
async function one(kind,dest,f,ui){
  var off=0,tries=0;
  if(!f.size)throw new Error('empty file');
  for(;;){
    try{
      var r=await send(kind,dest,f,off,function(l,t){ui.bytes(off+l);ui.saving(l>=t)});
      ui.saving(false);
      if(r.s==409&&r.j.have!=null){off=r.j.have;continue}
      if(r.s==403)throw new Error('fatal:'+(r.j.err||'session expired: reload the page'));
      if(r.s>=500||r.s==0)throw new Error('net');
      if(r.s!=200)throw new Error('fatal:'+(r.j.err||('HTTP '+r.s)));
      if(r.j.done)return r.j;
      off=r.j.have;tries=0;ui.bytes(off);
    }catch(e){
      if(/^fatal:/.test(e.message))throw new Error(e.message.slice(6));
      if(++tries>8)throw new Error('connection lost');
      ui.retry(tries);await sleep(Math.min(15000,1500*tries));
      off=Math.max(0,off);  /* server answers 409 with the real offset if it got more */
    }}}
function box(form){
  var d=document.createElement('div');d.className='upbox';
  d.innerHTML='<div class="row"><b class="uph">Uploading</b><span class="upp">0%</span></div><div class="bar"><i style="width:0"></i></div>'+
    '<div class="mut upf"></div><div class="mut upst"></div><div class="warn upw">Keep this page open until the upload finishes. Leaving or locking the phone pauses it; reopen and upload the same files again to resume where it stopped.</div><div class="upsum"></div>';
  form.after(d);return d}
document.querySelectorAll('form[data-up]').forEach(function(form){
  form.addEventListener('submit',async function(ev){
    ev.preventDefault(); if(busy)return;
    var kind=form.dataset.up, inp=form.querySelector('input[type=file]'), files=Array.from(inp.files||[]);
    var dest=((form.querySelector('[name=album],[name=folder]')||{}).value||'').trim()||(new URLSearchParams(location.search).get('a')||'Uploads');
    if(!files.length)return;
    var total=files.reduce(function(a,f){return a+f.size},0), doneB=0, ok=0, skip=0, bad=[], d=box(form), btn=form.querySelector('button');
    btn.disabled=true;busy=true;
    var bar=d.querySelector('.bar i'),pp=d.querySelector('.upp'),pf=d.querySelector('.upf'),st=d.querySelector('.upst');
    for(var i=0;i<files.length;i++){
      var f=files[i];pf.innerHTML='File '+(i+1)+' of '+files.length+': <code>'+esc(f.name)+'</code> ('+mb(f.size)+')';
      var ui={bytes:function(b){var p=(doneB+b)*100/total;bar.style.width=p.toFixed(1)+'%';pp.textContent=p.toFixed(0)+'% · '+mb(doneB+b)+' / '+mb(total)},
              saving:function(on){var s=on?'Server is saving…':'';if(st.textContent!==s)st.textContent=s},
              retry:function(n){st.textContent='Connection hiccup, retrying ('+n+'/8)…'}};
      try{var r=await one(kind,dest,f,ui); if(r.skipped)skip++; else ok++; dest=r.dest||dest}
      catch(e){bad.push(f.name+': '+e.message)}
      doneB+=f.size;ui.bytes(0);st.textContent='';
    }
    busy=false;btn.disabled=false;d.querySelector('.upw').hidden=true;
    d.querySelector('.uph').textContent=bad.length?'Finished with problems':'Upload complete';
    pf.innerHTML='';
    var href=kind=='photos'?'/admin/photos?a='+encodeURIComponent(dest):'/admin/music?v=folders&f='+encodeURIComponent(dest);
    d.querySelector('.upsum').innerHTML='<p><b>'+ok+' uploaded</b>'+(skip?', '+skip+' skipped (already there)':'')+', <b'+(bad.length?' class="err"':'')+'>'+bad.length+' failed</b> · into <code>'+esc(dest)+'</code></p>'+
      (bad.length?'<ul class="err">'+bad.map(function(b){return '<li>'+esc(b)+'</li>'}).join('')+'</ul><p class="mut">Upload the same selection again: finished files are skipped and only the failed ones are sent.</p>':'')+
      (kind=='photos'?'<p class="mut">Thumbnails are generated in the background over the next minute or so.</p>':'')+
      '<a class="btn pri" href="'+href+'">Open '+(kind=='photos'?'album':'folder')+'</a>';
  });
});
/* USB import progress */
var im=document.getElementById('imports');
document.querySelectorAll('form[action$="/import"]').forEach(function(f){f.addEventListener('submit',function(){var b=f.querySelector('button');b.textContent='Starting import…';setTimeout(function(){b.disabled=true},0)})});
if(im){(async function poll(){
  for(;;){var j=[];try{j=await (await fetch('/admin/import/status',{cache:'no-store'})).json()}catch(_){}
    im.innerHTML=j.map(function(s){var p=s.done*100/Math.max(1,s.total);return '<div class="job"><div class="row"><b>Import '+esc(s.src)+'</b><span class="mut">'+s.done+'/'+s.total+' · '+
      (s.state=='running'?'copying…':s.state)+'</span></div><div class="bar"><i style="width:'+p.toFixed(0)+'%"></i></div></div>'}).join('');
    var run=j.some(function(s){return s.state=='running'});busy=busy||false;
    await sleep(run?1500:10000)}})()}
})();
