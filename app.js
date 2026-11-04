// SPDX-License-Identifier: GPL-2.0-only
const $ = id => document.getElementById(id);
const canvas = $('scene');
let gl, program, manifest, positions, centers, fields, faceCells, frame = 0, playing = false;
let yaw = 0.2, pitch = -0.35, zoom = 1, loaded = false, activePreset = 'data';
const buffers = {};
const hardwareBuffers = {};
let hardwarePositions = null;
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
    attribute vec3 position; attribute float concentration; attribute vec3 bary; attribute vec3 center;
    uniform vec4 camera; uniform float aspect; uniform float radius; uniform float cut; uniform vec3 cutAxis;
    varying float value; varying vec3 edge; varying float visible; varying vec3 surfacePosition;
    void main(){
      vec3 p=position/radius;
      float cy=cos(camera.x),sy=sin(camera.x),cx=cos(camera.y),sx=sin(camera.y);
      p=vec3(cy*p.x+sy*p.z,p.y,-sy*p.x+cy*p.z);
      p=vec3(p.x,cx*p.y-sx*p.z,sx*p.y+cx*p.z);
      surfacePosition=p;
      gl_Position=vec4(p.x*camera.z/aspect,p.y*camera.z,-p.z*0.2,1.0);
      value=concentration; edge=bary; visible=step(dot(center,cutAxis),cut);
    }`));
  gl.attachShader(program, shader(gl.FRAGMENT_SHADER, `
    #extension GL_OES_standard_derivatives : enable
    precision highp float;
    varying float value; varying vec3 edge; varying float visible; varying vec3 surfacePosition;
    uniform float maximum; uniform float edges; uniform float logarithmic; uniform float lighting; uniform float hardware;
    vec3 palette(float t){
      vec3 a=vec3(.07,.12,.23),b=vec3(.16,.34,.49),c=vec3(.24,.65,.61),d=vec3(.72,.84,.51),e=vec3(.96,.82,.51);
      if(t<.25)return mix(a,b,t*4.); if(t<.5)return mix(b,c,(t-.25)*4.);
      if(t<.75)return mix(c,d,(t-.5)*4.);return mix(d,e,(t-.75)*4.);
    }
    void main(){if(visible<.5)discard; float t=mix(value/maximum,log(1.+value)/log(1.+maximum),logarithmic);vec3 col=palette(clamp(t,0.,1.));
      col=mix(col,vec3(.38,.46,.48),hardware);
      vec3 w=smoothstep(vec3(0.),fwidth(edge)*1.1,edge);
      float line=min(w.x,min(w.y,w.z)); col=mix(col*.35,col,mix(1.,line,edges));
      vec3 normal=normalize(cross(dFdx(surfacePosition),dFdy(surfacePosition)));
      float shade=.62+.38*abs(dot(normal,normalize(vec3(.3,.6,1.))));col*=mix(1.,shade,lighting);
      gl_FragColor=vec4(col,1.);
    }`));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
  gl.useProgram(program); gl.enable(gl.DEPTH_TEST);
  for (const key of ['position','concentration','bary','center']) {buffers[key] = gl.createBuffer();hardwareBuffers[key]=gl.createBuffer();}
}
function attribute(name, values, size, target=buffers) {
  gl.bindBuffer(gl.ARRAY_BUFFER, target[name]); gl.bufferData(gl.ARRAY_BUFFER, values, gl.DYNAMIC_DRAW);
  const at = gl.getAttribLocation(program, name); gl.enableVertexAttribArray(at); gl.vertexAttribPointer(at,size,gl.FLOAT,false,0,0);
}
function uniform(name, value) {gl.uniform1f(gl.getUniformLocation(program,name),value);}
function bindGeometry(target){for(const [name,size] of [['position',3],['concentration',1],['bary',3],['center',3]]){gl.bindBuffer(gl.ARRAY_BUFFER,target[name]);const at=gl.getAttribLocation(program,name);gl.vertexAttribPointer(at,size,gl.FLOAT,false,0,0);}}
function colorMaximum(){const s=manifest.species[$('species').value];return $('mapping').value==='robust'?s.displayP995:s.max;}
function draw() {
  if (!loaded) return;
  const rect=canvas.getBoundingClientRect(), dpr=Math.min(devicePixelRatio,2);
  canvas.width=Math.round(rect.width*dpr); canvas.height=Math.round(rect.height*dpr);
  gl.viewport(0,0,canvas.width,canvas.height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.uniform4f(gl.getUniformLocation(program,'camera'),yaw,pitch,zoom,0);
  uniform('aspect',canvas.width/canvas.height);uniform('radius',manifest.radius || 7.1);
  uniform('maximum',colorMaximum());
  uniform('logarithmic',$('mapping').value==='linear'?0:1);
  uniform('lighting',$('lighting').checked?1:0);
  uniform('edges',$('edges').checked?1:0);uniform('cut',Number($('cut').value));
  const axis=$('cutAxis').value;gl.uniform3f(gl.getUniformLocation(program,'cutAxis'),axis==='x'?1:0,axis==='y'?1:0,axis==='z'?1:0);
  bindGeometry(buffers);uniform('hardware',0);gl.drawArrays(gl.TRIANGLES,0,positions.length/3);
  if(activePreset==='engine' && $('hardware').checked && hardwarePositions){bindGeometry(hardwareBuffers);uniform('hardware',1);gl.drawArrays(gl.TRIANGLES,0,hardwarePositions.length/3);}
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
  $('scaleTitle').textContent=`${$('species').value} / µM · ${$('mapping').value==='linear'?'linear':'log(1 + c/µM)'}`;
  $('rangeMax').textContent=($('mapping').value==='robust'?'≥ ':'')+colorMaximum().toFixed(1);
  $('rangeMax').title=$('mapping').value==='robust'?'Values above this limit share the top color; choose full range to include every peak.':'Full recorded maximum';
  draw();
}
async function fetchFile(path, json=false) {
  const r=await fetch(path); if(!r.ok)throw Error(`Could not load ${path} (${r.status})`);
  return json?r.json():new Float32Array(await r.arrayBuffer());
}
async function load(preset) {
  loaded=false;playing=false;$('play').disabled=true;$('timeline').disabled=true;$('preset').disabled=true;
  $('status').textContent='Loading recording…';$('play').textContent='Play ▶';
  manifest=await fetchFile(`${preset}/manifest.json`,true);
  [positions,fields]=await Promise.all([fetchFile(`${preset}/positions.f32`),
    Promise.all(['X','Y'].map(s=>fetchFile(`${preset}/${s}.f32`))).then(([X,Y])=>({X,Y}))]);
  if(positions.length!==manifest.faces*9 || Object.values(fields).some(v=>v.length!==(manifest.cells||manifest.faces)*manifest.times.length))throw Error('Recording dimensions do not match the manifest.');
  faceCells=manifest.volume?await fetchFile(`${preset}/face-cells.f32`):null;
  if(faceCells&&(faceCells.length!==manifest.faces||faceCells.some(i=>i<0||i>=manifest.cells||!Number.isInteger(i))))throw Error('Invalid face-cell map.');
  centers=new Float32Array(positions.length);
  if(manifest.volume){
    // Recover each tetrahedron's center from its four stored triangular faces.
    // This lets all recordings support axis cuts without changing their assets.
    const cellCenters=new Float64Array(manifest.cells*3),counts=new Uint32Array(manifest.cells);
    for(let i=0;i<manifest.faces;i++){const cell=faceCells[i];counts[cell]+=3;
      for(let v=0;v<3;v++)for(let d=0;d<3;d++)cellCenters[cell*3+d]+=positions[i*9+v*3+d];}
    const min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];
    for(let i=0;i<manifest.cells;i++)for(let d=0;d<3;d++){cellCenters[i*3+d]/=counts[i];min[d]=Math.min(min[d],cellCenters[i*3+d]);max[d]=Math.max(max[d],cellCenters[i*3+d]);}
    for(let i=0;i<manifest.faces;i++)for(let v=0;v<3;v++)for(let d=0;d<3;d++)centers[i*9+v*3+d]=(cellCenters[faceCells[i]*3+d]-min[d])/(max[d]-min[d]);
    if(preset==='engine')buildHardware(min,max);
  }
  attribute('position',positions,3);attribute('center',centers,3);
  const bary=new Float32Array(positions.length);for(let i=0;i<bary.length;i++)bary[i]=(i%9===0||i%9===4||i%9===8)?1:0;
  attribute('bary',bary,3);
  $('timeline').max=manifest.times.length-1;$('frameCount').textContent=manifest.times.length;
  $('speed').value=manifest.defaultSpeed || '0.25';
  $('robustOption').disabled=!manifest.species.X.displayP995;$('mapping').value=manifest.defaultMapping || 'log';
  $('hardwareRow').hidden=preset!=='engine';
  $('startTime').textContent=`${manifest.times[0]} s`;$('endTime').textContent=`${manifest.times.at(-1).toFixed(2)} s`;
  $('cut').disabled=!manifest.volume;$('cutAxis').disabled=!manifest.volume;$('viewSection').disabled=!manifest.volume;
  $('cut').value=manifest.defaultCut || 1;$('cutValue').textContent=`${Math.round(Number($('cut').value)*100)}%`;$('cutAxis').value=manifest.defaultCutAxis || 'x';
  $('cutHint').textContent=manifest.volume?'Section removes whole tetrahedra along the chosen direction; exposed faces show the remaining cells.':'The slab recording contains surface data only.';
  $('geometryLabel').textContent=manifest.label || '10 × 10 × 0.2 µm / TETRAHEDRAL SLAB';
  $('provenance').textContent=manifest.description || 'Official CNS-OIST/STEPS_Example recording. Surface extraction of a 10 × 10 × 0.2 µm tetrahedral slab. Fixed color scale; no temporal interpolation. Solver and mesh convergence have not been independently verified.';
  $('tracePanel').hidden=!manifest.traces;
  $('traceTitle').textContent=manifest.traceTitle || 'Two chambers. One reaction network.';
  $('traceLeft').textContent=`● ${manifest.traceLabels?.left || 'Left chamber'}`;$('traceRight').textContent=`● ${manifest.traceLabels?.right || 'Right chamber'}`;
  $('regionNote').textContent=manifest.regionNote || 'Regions: cell centers x < −0.5 µm (left) and x > 0.5 µm (right). The left chamber receives an initial stimulus. One stochastic trajectory; no uncertainty estimate.';
  $('modelNote').textContent=manifest.modelNote || 'A chemical oscillator coupled through diffusion. Each mesh element follows the same reaction network; stochastic molecular events create local differences.';
  $('status').textContent=manifest.volume?'VOLUME DATA / TETEXACT':'SURFACE DATA / TETEXACT';
  frame=manifest.defaultFrame || 0;yaw=preset==='engine'?.65:.2;pitch=-0.35;zoom=1;loaded=true;activePreset=preset;
  $('play').disabled=false;$('timeline').disabled=false;$('preset').disabled=false;updateFrame();
}
function togglePlay(){if(!loaded)return;playing=!playing;if(playing&&frame===manifest.times.length-1)frame=0;$('play').textContent=playing?'Pause Ⅱ':'Play ▶';$('play').setAttribute('aria-label',playing?'Pause simulation':'Play simulation');}
$('play').onclick=togglePlay;
$('timeline').oninput=()=>{playing=false;$('play').textContent='Play ▶';$('play').setAttribute('aria-label','Play simulation');frame=Number($('timeline').value);updateFrame();};
$('species').onchange=updateFrame;$('edges').onchange=draw;
$('mapping').onchange=updateFrame;
$('lighting').onchange=draw;
$('hardware').onchange=draw;
$('cut').oninput=()=>{$('cutValue').textContent=`${Math.round(Number($('cut').value)*100)}%`;draw();};
$('cutAxis').onchange=draw;
$('reset').onclick=$('viewThree').onclick=()=>{yaw=activePreset==='engine'?.65:.2;pitch=-.35;zoom=1;draw();};
$('viewInlet').onclick=()=>{yaw=Math.PI/2;pitch=0;zoom=1.3;draw();};
$('viewSection').onclick=()=>{yaw=.45;pitch=.65;zoom=1.1;$('cutAxis').value='z';$('cut').value=.55;$('cutValue').textContent='55%';draw();};
$('preset').onchange=()=>load($('preset').value).catch(fail);
function buildHardware(min,max){
  // Solid exclusions from the same original CAD construction, scaled to µm.
  // Gray context is never colored as chemistry and never contributes to traces.
  const p=[];
  function tri(a,b,c){p.push(...a,...b,...c);}
  function cone(x0,x1,r0,r1,startCap=false,endCap=false){for(let i=0;i<48;i++){const a=i*2*Math.PI/48,b=(i+1)*2*Math.PI/48;
    const u=[x0,r0*Math.cos(a),r0*Math.sin(a)],v=[x0,r0*Math.cos(b),r0*Math.sin(b)],w=[x1,r1*Math.cos(a),r1*Math.sin(a)],z=[x1,r1*Math.cos(b),r1*Math.sin(b)];tri(u,v,w);tri(v,z,w);if(startCap)tri([x0,0,0],v,u);if(endCap)tri([x1,0,0],w,z);}}
  cone(-1.5,-.75,.2,.425,true,false);cone(-.75,.5,.425,.425);cone(.5,1.5,.425,.2,false,true);
  for(let i=0;i<12;i++){
    const a=i*Math.PI/6,c=Math.cos(a),s=Math.sin(a);
    const v=[];for(const x of [-.375,-.025])for(const y of [.35,.9])for(const z of [-.0325,.0325])v.push([x,y*c-z*s,y*s+z*c]);
    for(const [a,b,c,d] of [[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]]){tri(v[a],v[b],v[c]);tri(v[a],v[c],v[d]);}
  }
  hardwarePositions=new Float32Array(p);const center=new Float32Array(p.length),bary=new Float32Array(p.length);
  for(let i=0;i<p.length;i++){center[i]=(p[i]-min[i%3])/(max[i%3]-min[i%3]);bary[i]=(i%9===0||i%9===4||i%9===8)?1:0;}
  attribute('position',hardwarePositions,3,hardwareBuffers);attribute('center',center,3,hardwareBuffers);
  attribute('bary',bary,3,hardwareBuffers);attribute('concentration',new Float32Array(p.length/3),1,hardwareBuffers);
}
let drag=null;
canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);};
canvas.onpointermove=e=>{if(!drag)return;yaw+=(e.clientX-drag[0])*.008;pitch+=(e.clientY-drag[1])*.008;drag=[e.clientX,e.clientY];draw();};
canvas.onpointerup=canvas.onpointercancel=()=>{drag=null;};
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.3,Math.min(4,zoom*Math.exp(-e.deltaY*.001)));draw();},{passive:false});
canvas.onkeydown=e=>{if(e.key===' '){e.preventDefault();togglePlay();}else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();yaw+=e.key==='ArrowLeft'?-.1:e.key==='ArrowRight'?.1:0;pitch+=e.key==='ArrowUp'?-.1:e.key==='ArrowDown'?.1:0;draw();}};
new ResizeObserver(draw).observe(canvas);
let previous=0, remainder=0;
function tick(t){if(playing&&loaded){remainder+=Math.min((t-previous)/1000,.1)*Number($('speed').value);while(frame<manifest.times.length-1&&remainder>=manifest.times[frame+1]-manifest.times[frame]){remainder-=manifest.times[frame+1]-manifest.times[frame];frame++;updateFrame();}if(frame===manifest.times.length-1){playing=false;$('play').textContent='Replay ↻';$('play').setAttribute('aria-label','Replay simulation');remainder=0;}}else remainder=0;previous=t;requestAnimationFrame(tick);}
function fail(error){loaded=false;playing=false;$('preset').disabled=false;$('status').textContent=error.message;$('status').style.color='#ffb5a0';console.error(error);}
try {initialize();
  // An optional validated custom-volume recording can be bundled alongside the baseline.
  for(const [preset,label] of [['volume','Twin chambers · volume'],['engine','Engine interior · volume']]){
    const r=await fetch(`${preset}/manifest.json`);
    if(r.ok){const o=document.createElement('option');o.value=preset;o.textContent=label;$('preset').prepend(o);$('preset').value=preset;}
  }
  await load($('preset').value);requestAnimationFrame(tick);
}catch(error){fail(error);}
