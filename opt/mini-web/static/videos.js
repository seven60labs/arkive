/* ARKive videos: live conversion-queue status */
(function(){
var el=document.getElementById('vq');if(!el)return;
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function t(s){s=Math.max(0,Math.round(s||0));var h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;return (h?h+':'+(m<10?'0':''):'')+m+':'+(x<10?'0':'')+x}
var had=false,F=document.getElementById('vform'),B=document.getElementById('vbusy'),up=false;
function mb(n){return n>=1e9?(n/1e9).toFixed(2)+' GB':(n/1e6).toFixed(1)+' MB'}
function lock(on,why){if(!F)return;F.querySelectorAll('input[type=file],button').forEach(function(x){x.disabled=on});if(B){B.hidden=!on||up;if(why)B.textContent='Upload is disabled until the current video is finished: '+why}}
if(F){var inp=F.querySelector('input[type=file]'),info=document.getElementById('vinfo');
  inp.addEventListener('change',function(){var f=inp.files[0];info.textContent='';if(!f)return;
    info.textContent=f.name+' · '+mb(f.size);var v=document.createElement('video');v.preload='metadata';
    v.onloadedmetadata=function(){var d=v.duration,sp=parseFloat(F.dataset.speed)||1;URL.revokeObjectURL(v.src);
      if(isFinite(d)&&d>0)info.innerHTML=esc(f.name)+' · '+mb(f.size)+' · '+t(d)+' long · conversion about <b>'+t(d/sp)+'</b> after upload'+(d>1200?' <span class="err">(long video: the Pi will be busy for a long time)</span>':'')};
    v.onerror=function(){URL.revokeObjectURL(v.src)};v.src=URL.createObjectURL(f)});
  F.addEventListener('submit',function(){up=true;setTimeout(function(){lock(true)},0)},true)}
(async function poll(){for(;;){var j=null;try{j=await (await fetch('/admin/videos/queue',{cache:'no-store'})).json()}catch(_){}
  if(j){var h='',c=j.current;
    if(c){var p=c.duration?Math.min(100,c.pos*100/c.duration):0;had=true;
      h+='<div class="job"><div class="row"><b>Converting <code>'+esc(c.name)+'</code></b><span class="mut">'+p.toFixed(0)+'% · '+(c.speed?c.speed.toFixed(2)+'× realtime':'starting…')+
         (c.speed&&c.duration?' · about '+t((c.duration-c.pos)/c.speed)+' left':'')+'</span></div><div class="bar"><i style="width:'+p.toFixed(1)+'%"></i></div></div>'}
    if(j.waiting.length&&!c)h+='<div class="job"><b>Starting conversion of <code>'+esc(j.waiting[0])+'</code>…</b></div>';
    if(j.failed.length)h+='<div class="job err"><b>Could not convert ('+j.failed.length+')</b>: '+j.failed.map(esc).join(', ')+' <span class="mut">(kept in videos/.failed with a log)</span></div>';
    if(j.last)h+='<div class="job mut">Last finished: <code>'+esc(j.last.name)+'</code> · '+(j.last.ok?'ok, '+(j.last.speed||0).toFixed(2)+'× realtime':'failed')+'</div>';
    if(!j.alive&&(j.waiting.length||c))h+='<div class="warn">The converter service is not running (mini-videos.service).</div>';
    el.innerHTML=h||'<span class="mut">Nothing is being converted.</span>';
    if(!up)lock(!!(c||j.waiting.length||j.uploading),c?'“'+c.name+'” is being converted.':j.waiting.length?'“'+j.waiting[0]+'” is about to be converted.':j.uploading?'Another video is being uploaded.':'');
    if(had&&!c&&!j.waiting.length){had=false;setTimeout(function(){location.reload()},1500)}}
  await new Promise(function(r){setTimeout(r,(j&&(j.current||j.waiting.length))?2000:10000)})}})();
})();
