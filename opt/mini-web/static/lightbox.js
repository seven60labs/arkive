// first-party lightbox for the admin photo grid: prev/next, keys, swipe
(function(){var lb=document.getElementById('lb');if(!lb)return;var I=document.getElementById('lbi'),N=document.getElementById('lbn'),O=document.getElementById('lbo'),c=0;
function show(i){c=(i+P.length)%P.length;var p=P[c];I.src=p.v;N.textContent=p.n+(p.d?' · '+p.d:'');O.href=p.o;lb.hidden=false;document.body.style.overflow='hidden'}
function hide(){lb.hidden=true;document.body.style.overflow=''}
document.querySelectorAll('a.ph[data-i]').forEach(function(a){a.onclick=function(e){e.preventDefault();show(+a.dataset.i)}});
document.getElementById('lbp').onclick=function(){show(c-1)};document.getElementById('lbnx').onclick=function(){show(c+1)};document.getElementById('lbx').onclick=hide;
document.addEventListener('keydown',function(e){if(lb.hidden)return;if(e.key=='ArrowLeft')show(c-1);if(e.key=='ArrowRight')show(c+1);if(e.key=='Escape')hide()});
var x0=null;lb.addEventListener('touchstart',function(e){x0=e.touches[0].clientX},{passive:true});
lb.addEventListener('touchend',function(e){if(x0===null)return;var dx=e.changedTouches[0].clientX-x0;if(Math.abs(dx)>40)show(c+(dx<0?1:-1));x0=null});
lb.addEventListener('click',function(e){if(e.target===lb)hide()});window.LBcur=function(){return lb.hidden?null:P[c]}})();
