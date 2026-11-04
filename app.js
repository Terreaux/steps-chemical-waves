// SPDX-License-Identifier: GPL-2.0-only
const $ = id => document.getElementById(id);
const canvas = $('scene');
let gl, program, manifest, positions, centers, fields, faceCells, frame = 0, playing = false;
let yaw = 0.2, pitch = -0.35, zoom = 1, loaded = false, activePreset = 'data';
const buffers = {};
function shader(type, source) {
  const s = gl.createShader(type); gl.shaderSource(s, source); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s));
  return s;
}
function initialize() {
  gl = canvas.getContext('webgl', {antialias: true, preserveDrawingBuffer: true});
  if (!gl) throw Error('WebGL is unavailable. Enable hardware acceleration and reload.');
  if (!gl.getExtension('OES_standard_derivatives')) throw Error('This viewer requires WebGL standard derivatives.');
  program = gl.createProgram();
  gl.attachShader(program, shader(gl.VERTEX_SHADER, `
    attribute vec3 position; attribute float concentration; attribute vec3 bary; attribute float center;
    uniform vec4 camera; uniform float aspect; uniform float radius; uniform float cut;
    varying float value; varying vec3 edge; varying float visible;
    void main(){
      vec3 p=position/radius;
      float cy=cos(camera.x),sy=sin(camera.x),cx=cos(camera.y),sx=sin(camera.y);
      p=vec3(cy*p.x+sy*p.z,p.y,-sy*p.x+cy*p.z);
      p=vec3(p.x,cx*p.y-sx*p.z,sx*p.y+cx*p.z);
      gl_Position=vec4(p.x*camera.z/aspect,p.y*camera.z,-p.z*0.2,1.0);
      value=concentration; edge=bary; visible=step(center,cut);
    }`));
  gl.attachShader(program, shader(gl.FRAGMENT_SHADER, `
    #extension GL_OES_standard_derivatives : enable
    precision highp float;
    varying float value; varying vec3 edge; varying float visible;
    uniform float maximum; uniform float edges; uniform float logarithmic;
    vec3 palette(float t){
      vec3 a=vec3(.07,.12,.23),b=vec3(.16,.34,.49),c=vec3(.24,.65,.61),d=vec3(.72,.84,.51),e=vec3(.96,.82,.51);
      if(t<.25)return mix(a,b,t*4.); if(t<.5)return mix(b,c,(t-.25)*4.);
      if(t<.75)return mix(c,d,(t-.5)*4.);return mix(d,e,(t-.75)*4.);
    }
    void main(){if(visible<.5)discard; float t=mix(value/maximum,log(1.+value)/log(1.+maximum),logarithmic);vec3 col=palette(clamp(t,0.,1.));
      vec3 w=smoothstep(vec3(0.),fwidth(edge)*1.1,edge);
      float line=min(w.x,min(w.y,w.z)); col=mix(col*.35,col,mix(1.,line,edges));
      gl_FragColor=vec4(col,1.);
    }`));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
  gl.useProgram(program); gl.enable(gl.DEPTH_TEST);
  for (const key of ['position','concentration','bary','center']) buffers[key] = gl.createBuffer();
}
function attribute(name, values, size) {
  gl.bindBuffer(gl.ARRAY_BUFFER, buffers[name]); gl.bufferData(gl.ARRAY_BUFFER, values, gl.DYNAMIC_DRAW);
  const at = gl.getAttribLocation(program, name); gl.enableVertexAttribArray(at); gl.vertexAttribPointer(at,size,gl.FLOAT,false,0,0);
}
function uniform(name, value) {gl.uniform1f(gl.getUniformLocation(program,name),value);}
function draw() {
  if (!loaded) return;
  const rect=canvas.getBoundingClientRect(), dpr=Math.min(devicePixelRatio,2);
  canvas.width=Math.round(rect.width*dpr); canvas.height=Math.round(rect.height*dpr);
  gl.viewport(0,0,canvas.width,canvas.height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.uniform4f(gl.getUniformLocation(program,'camera'),yaw,pitch,zoom,0);
  uniform('aspect',canvas.width/canvas.height);uniform('radius',manifest.radius || 7.1);
  uniform('maximum',manifest.species[$('species').value].max);
  uniform('logarithmic',$('mapping').value==='log'?1:0);
  uniform('edges',$('edges').checked?1:0);uniform('cut',Number($('cut').value));
  gl.drawArrays(gl.TRIANGLES,0,positions.length/3);
  drawTrace();
}
function drawTrace(){
  if(!manifest.traces)return;
  const c=$('trace'),ctx=c.getContext('2d'),w=c.clientWidth,h=180,dpr=Math.min(devicePixelRatio,2);
  c.width=w*dpr;c.height=h*dpr;ctx.scale(dpr,dpr);
  const traces=manifest.traces[$('species').value], max=Math.max(...traces.left,...traces.right)*1.08;
  const left=42,right=w-12,top=10,bottom=h-25,x=t=>left+t/manifest.times.at(-1)*(right-left),y=v=>bottom-v/max*(bottom-top);
  ctx.font='10px Arial';ctx.lineWidth=1;
  for(let i=0;i<=4;i++){const value=max*i/4,py=y(value);ctx.strokeStyle='#304044';ctx.beginPath();ctx.moveTo(left,py);ctx.lineTo(right,py);ctx.stroke();ctx.fillStyle='#849b9e';ctx.fillText(value.toFixed(0),3,py+3);}
  for(const [name,color] of [['left','#c7dfa7'],['right','#6bb8cf']]){ctx.strokeStyle=color;ctx.lineWidth=1.8;ctx.beginPath();traces[name].forEach((v,i)=>{i?ctx.lineTo(x(manifest.times[i]),y(v)):ctx.moveTo(x(manifest.times[i]),y(v));});ctx.stroke();}
  ctx.strokeStyle='#e5ecec';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x(manifest.times[frame]),top);ctx.lineTo(x(manifest.times[frame]),bottom);ctx.stroke();ctx.fillStyle='#849b9e';ctx.fillText('0 s',left,h-5);ctx.fillText(`${manifest.times.at(-1)} s`,right-18,h-5);
  $('traceSpecies').textContent=$('species').value;
}
function updateFrame() {
  if (!loaded) return;
  const values=fields[$('species').value], n=manifest.faces, count=manifest.cells || n, expanded=new Float32Array(n*3);
  for(let i=0;i<n;i++) expanded.fill(values[frame*count+(faceCells?faceCells[i]:i)],i*3,i*3+3);
  attribute('concentration',expanded,1);
  $('timeline').value=frame; $('time').value=`${manifest.times[frame].toFixed(2)} s`;
  $('scaleTitle').textContent=`${$('species').value} / µM · ${$('mapping').value==='log'?'log(1 + c/µM)':'linear'}`;
  $('rangeMax').textContent=manifest.species[$('species').value].max.toFixed(1);
  draw();
}
async function fetchFile(path, json=false) {
  const r=await fetch(path); if(!r.ok)throw Error(`Could not load ${path} (${r.status})`);
  return json?r.json():new Float32Array(await r.arrayBuffer());
}
async function load(preset) {
  loaded=false;playing=false;$('play').disabled=true;$('timeline').disabled=true;
  $('status').textContent='Loading recording…';$('play').textContent='Play ▶';
  manifest=await fetchFile(`${preset}/manifest.json`,true);
  [positions,fields]=await Promise.all([fetchFile(`${preset}/positions.f32`),
    Promise.all(['X','Y'].map(s=>fetchFile(`${preset}/${s}.f32`))).then(([X,Y])=>({X,Y}))]);
  if(positions.length!==manifest.faces*9 || Object.values(fields).some(v=>v.length!==(manifest.cells||manifest.faces)*manifest.times.length))throw Error('Recording dimensions do not match the manifest.');
  faceCells=manifest.volume?await fetchFile(`${preset}/face-cells.f32`):null;
  if(faceCells&&(faceCells.length!==manifest.faces||faceCells.some(i=>i<0||i>=manifest.cells||!Number.isInteger(i))))throw Error('Invalid face-cell map.');
  centers=manifest.volume?await fetchFile(`${preset}/centers.f32`):new Float32Array(manifest.faces*3);
  if(centers.length!==manifest.faces*3)throw Error('Invalid volume centers.');
  attribute('position',positions,3);attribute('center',centers,1);
  const bary=new Float32Array(positions.length);for(let i=0;i<bary.length;i++)bary[i]=(i%9===0||i%9===4||i%9===8)?1:0;
  attribute('bary',bary,3);
  $('timeline').max=manifest.times.length-1;$('frameCount').textContent=manifest.times.length;
  $('startTime').textContent=`${manifest.times[0]} s`;$('endTime').textContent=`${manifest.times.at(-1).toFixed(2)} s`;
  $('cut').disabled=!manifest.volume;$('cut').value=1;$('cutValue').textContent='100%';
  $('cutHint').textContent=manifest.volume?'Cut removes tetrahedra by center position along x; the exposed faces show the remaining cells.':'The slab recording contains surface data only.';
  $('geometryLabel').textContent=manifest.label || '10 × 10 × 0.2 µm / TETRAHEDRAL SLAB';
  $('provenance').textContent=manifest.description || 'Official CNS-OIST/STEPS_Example recording. Surface extraction of a 10 × 10 × 0.2 µm tetrahedral slab. Fixed color scale; no temporal interpolation. Solver and mesh convergence have not been independently verified.';
  $('tracePanel').hidden=!manifest.traces;
  $('status').textContent=manifest.volume?'VOLUME DATA / TETEXACT':'SURFACE DATA / TETEXACT';
  frame=0;yaw=0.2;pitch=-0.35;zoom=1;loaded=true;activePreset=preset;
  $('play').disabled=false;$('timeline').disabled=false;updateFrame();
}
function togglePlay(){if(!loaded)return;playing=!playing;if(playing&&frame===manifest.times.length-1)frame=0;$('play').textContent=playing?'Pause Ⅱ':'Play ▶';$('play').setAttribute('aria-label',playing?'Pause simulation':'Play simulation');}
$('play').onclick=togglePlay;
$('timeline').oninput=()=>{playing=false;$('play').textContent='Play ▶';$('play').setAttribute('aria-label','Play simulation');frame=Number($('timeline').value);updateFrame();};
$('species').onchange=updateFrame;$('edges').onchange=draw;
$('mapping').onchange=updateFrame;
$('cut').oninput=()=>{$('cutValue').textContent=`${Math.round(Number($('cut').value)*100)}%`;draw();};
$('reset').onclick=()=>{yaw=.2;pitch=-.35;zoom=1;draw();};
$('preset').onchange=()=>load($('preset').value).catch(fail);
let drag=null;
canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);};
canvas.onpointermove=e=>{if(!drag)return;yaw+=(e.clientX-drag[0])*.008;pitch+=(e.clientY-drag[1])*.008;drag=[e.clientX,e.clientY];draw();};
canvas.onpointerup=canvas.onpointercancel=()=>{drag=null;};
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.3,Math.min(4,zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});
canvas.onkeydown=e=>{if(e.key===' '){e.preventDefault();togglePlay();}else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();yaw+=e.key==='ArrowLeft'?-.1:e.key==='ArrowRight'?.1:0;pitch+=e.key==='ArrowUp'?-.1:e.key==='ArrowDown'?.1:0;draw();}};
new ResizeObserver(draw).observe(canvas);
let previous=0, remainder=0;
function tick(t){if(playing&&loaded){remainder+=Math.min((t-previous)/1000,.1)*Number($('speed').value);while(frame<manifest.times.length-1&&remainder>=manifest.times[frame+1]-manifest.times[frame]){remainder-=manifest.times[frame+1]-manifest.times[frame];frame++;updateFrame();}if(frame===manifest.times.length-1){playing=false;$('play').textContent='Replay ↻';$('play').setAttribute('aria-label','Replay simulation');remainder=0;}}else remainder=0;previous=t;requestAnimationFrame(tick);}
function fail(error){loaded=false;playing=false;$('status').textContent=error.message;$('status').style.color='#ffb5a0';console.error(error);}
try {initialize();
  // An optional validated custom-volume recording can be bundled alongside the baseline.
  const r=await fetch('volume/manifest.json');
  if(r.ok){const o=document.createElement('option');o.value='volume';o.textContent='Twin chambers · volume';$('preset').prepend(o);$('preset').value='volume';}
  await load($('preset').value);requestAnimationFrame(tick);
}catch(error){fail(error);}
