/* demo.js: animar-reels · estilo DEMO. Helpers SEEK-SAFE: todo es función pura de
   tl.time() o un tween de GSAP. Cero Math.random / Date.now / rAF (el azar es mulberry32).
   Uso: <script src="gsap.min.js"></script><script src="demo.js"></script> y luego el clip. */
(function(){
var TAU = Math.PI*2;

function rng(seed){ var a = seed>>>0; return function(){ a |= 0; a = a + 0x6D2B79F5 | 0;
  var t = Math.imul(a ^ a>>>15, 1 | a); t = t + Math.imul(t ^ t>>>7, 61 | t) ^ t;
  return ((t ^ t>>>14)>>>0) / 4294967296; }; }
function clamp(x,a,b){ return x<a?a:(x>b?b:x); }
function lerp(a,b,u){ return a+(b-a)*u; }
function eo(u){ u=clamp(u,0,1); return u===1?1:1-Math.pow(2,-10*u); }          // expo.out
function ss(u){ u=clamp(u,0,1); return u*u*(3-2*u); }                            // smoothstep

/* ---------- CÁMARA v2: centro (cx,cy) del lienzo a (FX,FY) con escala s, giro r y motion blur mb */
function Cam(el, FX, FY, init, mirror, mFY){
  /* mirror: otra capa (la rejilla de puntos a pantalla completa) que viaja con la MISMA cámara
     pero con su propio FY (el contenido va dentro de una ventana #vp desplazada) */
  var v = {cx:540, cy:960, s:1, r:0, mb:0};
  for (var k in init) v[k] = init[k];
  function tf(fy){ return 'translate('+FX+'px,'+fy+'px) rotate('+v.r+'deg) scale('+v.s+') translate('+(-v.cx)+'px,'+(-v.cy)+'px)'; }
  v.paint = function(){
    el.style.transform = tf(FY);
    el.style.filter = v.mb > 0.05 ? 'blur('+v.mb.toFixed(2)+'px)' : 'none';
    if (mirror) mirror.style.transform = tf(mFY);
  };
  /* vuelo: mueve la cámara y sube/baja el motion blur en la misma ventana */
  v.fly = function(tl, to, t, dur, ease, blur){
    tl.to(v, Object.assign({duration:dur, ease:ease||'power3.inOut'}, to), t);
    if (blur){ tl.to(v, {mb:blur, duration:dur*0.45, ease:'power2.in'}, t);
               tl.to(v, {mb:0, duration:dur*0.5, ease:'power2.out'}, t+dur*0.5); }
  };
  /* punch: sacudida de cámara seek-safe (micro-shake) */
  v.shake = {x:0, y:0};
  return v;
}

/* ---------- MASCOTA (OPCIONAL): cualquier imagen/SVG que aportes, dentro de un contenedor
   <div class="mascota-box" id="mbox"><!--MASCOT--></div>  (o un <img>/<svg> tuyo directamente).
   Es un "actor" de una pieza: respira, salta, se encoge, se inclina, mira a un lado, "habla"
   (pulsa) en las ventanas que le des y puede aparecer/desaparecer con k (escala 0-1).
   Si no usas mascota, simplemente no llames a D.Mascot ni pongas el contenedor.
   Proxies animables con GSAP: k, hop, sq, lean, look, boost. Posición (x,y) = CENTRO, en
   coordenadas de PANTALLA del espacio 1080x1920 (vive FUERA de #cam). */
function Mascot(box, o){
  o = o || {};
  var S = {x:o.x||540, y:o.y||960, w:o.w||150, k:1, lean:0, hop:0, sq:0, look:0, boost:0};
  S.talk = o.talk || [];            // [[t0,t1],...] ventanas en que "habla"
  var inner = box.firstElementChild || box;
  function talking(t){ for (var i=0;i<S.talk.length;i++) if (t>=S.talk[i][0] && t<=S.talk[i][1]) return true; return false; }
  S.render = function(t){
    var w = S.w*S.k;
    box.style.transform = 'translate('+(S.x - w/2)+'px,'+(S.y - 0.5*w)+'px) scale('+(w/150)+')';
    var br = Math.sin(TAU*t/1.3);                                   // respiración
    var sy = 1 + 0.022*br - 0.18*S.sq + (talking(t) ? 0.03*Math.abs(Math.sin(t*17)) : 0);
    var sx = 1/Math.sqrt(Math.max(sy,0.4));
    gsap.set(inner, {scaleY:sy, scaleX:sx, x:6*S.look, y:-6*br - 60*S.hop - 10*S.boost, rotation:12*S.lean, transformOrigin:'50% 90%'});
  };
  return S;
}

/* ---------- ODÓMETRO: columnas 0-9 que ruedan. value -> render(value). fmt: '000' o '0.000' */
function Odometer(el, fmt){
  el.classList.add('odo'); el.innerHTML='';
  var cols = [];
  for (var i=0;i<fmt.length;i++){
    if (fmt[i] !== '0'){ var s=document.createElement('span'); s.className='sep'; s.textContent=fmt[i]; el.appendChild(s); continue; }
    var c=document.createElement('span'); c.className='col';
    var st=document.createElement('span'); st.className='strip';
    for (var d=0; d<=10; d++){ var sp=document.createElement('span'); sp.textContent=(d%10); st.appendChild(sp); }
    c.appendChild(st); el.appendChild(c); cols.push(st);
  }
  var n = cols.length;
  return { render:function(v){
    v = Math.max(0, v);
    for (var k=0;k<n;k++){
      var p = Math.pow(10, n-1-k);
      var base = Math.floor(v/p) % 10;
      var r = (v % p)/p; var roll = (p===1) ? (v%1) : (r>0.92 ? (r-0.92)/0.08 : 0);
      if (k>0 && v < p) { cols[k].parentNode.style.opacity = (v>=p*0.92? (v/p-0.92)/0.08 : 0); } else cols[k].parentNode.style.opacity = 1;
      cols[k].style.transform = 'translateY('+(-(base+roll))+'em)';
    }
  }};
}

/* ---------- PARTÍCULAS deterministas: estallido desde (x,y) en t0. shape: 'coin'|'spark'|'bill'|'dot' */
function Burst(parent, o){
  var R = rng(o.seed||7), n = (o.n===undefined ? 18 : o.n), P=[];
  for (var i=0;i<n;i++){
    var e = document.createElement('div'); e.className='pt';
    var col = o.colors[i % o.colors.length], sz = (o.size||14)*(0.7+0.6*R());
    if (o.shape==='coin'){ e.style.width=e.style.height=sz+'px'; e.style.borderRadius='50%'; e.style.background=col; e.style.boxShadow='0 0 0 2px #1C1A17, inset -3px -3px 0 rgba(0,0,0,.18)'; }
    else if (o.shape==='bill'){ e.style.width=(sz*1.9)+'px'; e.style.height=sz+'px'; e.style.borderRadius='3px'; e.style.background=col; e.style.boxShadow='0 0 0 2px #1C1A17'; }
    else if (o.shape==='spark'){ e.style.width=(sz*0.35)+'px'; e.style.height=sz*1.6+'px'; e.style.borderRadius='4px'; e.style.background=col; }
    else { e.style.width=e.style.height=sz+'px'; e.style.borderRadius='50%'; e.style.background=col; }
    e.style.opacity=0; parent.appendChild(e);
    var ang = (o.dir!==undefined? o.dir : -Math.PI/2) + (R()-0.5)*(o.spread||TAU);
    var sp = (o.speed||600)*(0.45+0.75*R());
    P.push({e:e, vx:Math.cos(ang)*sp, vy:Math.sin(ang)*sp, rot:(R()-0.5)*900, life:(o.life||1.1)*(0.7+0.5*R()), ang:ang});
  }
  var g = o.gravity===undefined?1400:o.gravity;
  return { update:function(t){
    for (var i=0;i<P.length;i++){ var p=P[i], u=t-o.t0;
      if (u<0 || u>p.life){ p.e.style.opacity=0; continue; }
      var x=o.x+p.vx*u, y=o.y+p.vy*u+0.5*g*u*u, a=1-Math.pow(u/p.life,3);
      var r = o.shape==='spark' ? (Math.atan2(p.vy+g*u, p.vx)*180/Math.PI+90) : p.rot*u;
      p.e.style.opacity=a; p.e.style.transform='translate('+x+'px,'+y+'px) rotate('+r+'deg)';
    } } };
}

/* ---------- estado inicial SEGURO en el frame 0: un tl.set(...,0) solo NO se pinta con el
   cabezal exactamente en 0 (lint: gsap_timeline_set_initial_hide) → gsap.set inmediato + tl.set
   para que rebobinar también lo restaure. Úsalo para todo lo que entra después. */
function hide(tl, targets, vars){ vars = vars || {autoAlpha:0}; gsap.set(targets, vars); tl.set(targets, vars, 0); }

/* ---------- anillo de pulso: expande y se apaga */
function pulse(tl, el, t, o){ o=o||{};
  tl.fromTo(el, {scale:o.from||0.4, opacity:o.op||0.9}, {scale:o.to||2.2, opacity:0, duration:o.dur||0.7, ease:'power2.out', immediateRender:false}, t); }

/* ---------- brillo que barre */
function sheen(tl, el, t, dur){ tl.fromTo(el, {xPercent:-160, skewX:-18}, {xPercent:360, skewX:-18, duration:dur||0.7, ease:'power2.inOut', immediateRender:false}, t); }

/* ---------- entrada 3D de superficie (desde profundidad, se asienta plana) */
function enter3d(tl, el, t, o){ o=o||{};
  tl.fromTo(el, {transformPerspective:1600, rotationX:o.rx===undefined?34:o.rx, rotationY:o.ry===undefined?-16:o.ry, z:o.z===undefined?-260:o.z, y:o.y===undefined?70:o.y, x:o.x||0, autoAlpha:o.a0===undefined?0:o.a0},
    {rotationX:0, rotationY:0, z:0, y:0, x:0, autoAlpha:1, duration:o.dur||0.7, ease:o.ease||'expo.out', immediateRender:o.ir||false}, t); }

/* ---------- pop de UI (chip, avatar, badge): escala desde 0 sin rebote */
function pop(tl, el, t, o){ o=o||{};
  tl.fromTo(el, {scale:o.from===undefined?0.3:o.from, autoAlpha:0, y:o.y||0, rotation:o.r0||0}, {scale:1, autoAlpha:1, y:0, rotation:o.r||0, duration:o.dur||0.34, ease:o.ease||'expo.out', immediateRender:false}, t); }

/* ---------- sello: entra grande y asienta (sin rebote) */
function stamp(tl, el, t, rot){ tl.fromTo(el, {scale:1.5, autoAlpha:0, rotation:(rot||-6)-8}, {scale:1, autoAlpha:1, rotation:rot||-6, duration:0.26, ease:'power4.out', immediateRender:false}, t); }

/* ---------- trazo SVG que se dibuja */
function draw(tl, path, t, dur, ease){ var L = path.getTotalLength(); path.style.strokeDasharray = L+' '+L;
  tl.fromTo(path, {strokeDashoffset:L}, {strokeDashoffset:0, duration:dur||0.5, ease:ease||'power2.inOut', immediateRender:false}, t); return L; }

/* ---------- cursor SVG */
var CURSOR = '<svg viewBox="0 0 46 56" width="46" height="56"><path d="M6 4 L6 44 L16 34 L23 50 L31 46 L24 31 L38 31 Z" fill="#FFFDF8" stroke="#1C1A17" stroke-width="4" stroke-linejoin="round"/></svg>';

/* ---------- avatar genérico (silueta, color de fondo variable) */
function avatarSVG(bg, skin, hair){
  return '<svg viewBox="0 0 100 100"><rect width="100" height="100" fill="'+bg+'"/>'+
    '<circle cx="50" cy="40" r="19" fill="'+skin+'"/><path d="M31 36 Q33 18 50 18 Q67 18 69 36 Q60 26 50 27 Q40 26 31 36Z" fill="'+hair+'"/>'+
    '<path d="M14 100 Q16 66 50 64 Q84 66 86 100Z" fill="'+hair+'" opacity=".92"/></svg>';
}
var AVS = [['#F3C9A6','#E7B48F','#3A2A22'],['#BFD3F2','#C98E6A','#1C1A17'],['#F6D77A','#F0C29C','#7A4A2A'],
           ['#CDE8D6','#8E5B3E','#241A12'],['#F2B8B0','#EFC7A6','#5B3A28'],['#D9CCF0','#E9B996','#2E2A26'],
           ['#FAD7B5','#D7A07A','#6A3F24'],['#C6E3EE','#F2CFB0','#8A5A34']];
function avatar(i){ var a=AVS[i%AVS.length]; return avatarSVG(a[0],a[1],a[2]); }

window.D = {TAU:TAU, rng:rng, clamp:clamp, lerp:lerp, eo:eo, ss:ss, Cam:Cam, Mascot:Mascot, Odometer:Odometer,
            Burst:Burst, hide:hide, pulse:pulse, sheen:sheen, enter3d:enter3d, pop:pop, stamp:stamp, draw:draw, CURSOR:CURSOR, avatar:avatar};
})();
